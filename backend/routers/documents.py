import os
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from models.schemas import DocumentInfo, DocumentListResponse, DocumentStatus
from database import get_db
from models.db_models import Document, DocumentChunk, User
from sqlalchemy.orm import Session
from config import settings
from auth.permissions import require_admin
from services.document_processing import detect_source_type, parse_document_to_chunks
from services.hybrid_retriever import EmbeddingManager, compute_embeddings_for_chunks
from config import settings as app_settings

router = APIRouter()

# Default to local-only mode unless explicitly enabled.
USE_PAGEINDEX_CLOUD = os.getenv("USE_PAGEINDEX_CLOUD", "false").lower() == "true"

# Anchor upload dir to backend package directory — works regardless of cwd
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_UPLOAD_DIR = _BACKEND_DIR / "data" / "uploads"
_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Try to import PageIndex client (optional dependency)
pi_client = None
try:
    from pageindex.client import PageIndexClient
    if settings.PAGEINDEX_API_KEY and USE_PAGEINDEX_CLOUD:
        pi_client = PageIndexClient(api_key=settings.PAGEINDEX_API_KEY)
except ImportError:
    print("[documents] PageIndex SDK not installed. Document upload uses local-only mode.")
except Exception as e:
    print(f"[documents] PageIndex init failed: {e}")


def _find_doc(db: Session, doc_id: str):
    """Look up a document by internal_id first (stable), then doc_id (cloud, may change)."""
    return (
        db.query(Document).filter(Document.internal_id == doc_id).first()
        or db.query(Document).filter(Document.doc_id == doc_id).first()
    )


VALID_STATUSES = {"processing", "indexed", "error"}

def _safe_status(status: str) -> DocumentStatus:
    return DocumentStatus(status) if status in VALID_STATUSES else DocumentStatus.processing

def _safe_doc_type(doc_type: str) -> str:
    return doc_type if doc_type in ("guideline", "general") else "general"


def _resolve_existing_upload_path(internal_id: str) -> str:
    for ext in [".pdf", ".docx", ".txt", ".md"]:
        p = _UPLOAD_DIR / f"{internal_id}{ext}"
        if p.exists():
            return str(p)
    return str(_UPLOAD_DIR / f"{internal_id}.pdf")


@router.get("", response_model=DocumentListResponse)
def list_documents(db: Session = Depends(get_db)):
    """List all indexed documents from DB."""
    try:
        db_docs = db.query(Document).order_by(Document.created_at.desc()).all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")
    docs = []
    for d in db_docs:
        stable_id = d.internal_id or d.doc_id
        if not stable_id:
            continue
        docs.append(DocumentInfo(
            id=stable_id,
            title=d.name or stable_id,
            filename=d.name or stable_id,
            pages=0,
            doc_type=_safe_doc_type(d.doc_type or "general"),
            status=_safe_status(d.status or "processing"),
            sections=0,
            last_queried="Recently",
            tree=None
        ))
    return DocumentListResponse(documents=docs, total=len(docs))


@router.get("/{doc_id}", response_model=DocumentInfo)
def get_document(doc_id: str, db: Session = Depends(get_db)):
    """Get a specific document."""
    d = _find_doc(db, doc_id)
    if not d:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")

    tree_data = None
    cloud_id = d.doc_id
    if pi_client and cloud_id:
        try:
            if pi_client.is_retrieval_ready(cloud_id):
                tree_data = pi_client.get_tree(cloud_id)
                d.status = "indexed"
                db.commit()
        except Exception:
            pass

    stable_id = d.internal_id or d.doc_id
    return DocumentInfo(
        id=stable_id,
        title=d.name,
        filename=d.name,
        pages=0,
        doc_type=d.doc_type,
        status=DocumentStatus(d.status) if d.status in ("processing", "indexed", "error") else DocumentStatus.processing,
        sections=0,
        last_queried="Recently",
        tree=tree_data
    )


@router.post("/upload", response_model=DocumentInfo)
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form("general"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Upload and index a document for automatic context injection. Admin only."""
    source_type = detect_source_type(file.filename or "")
    if source_type not in {"pdf", "docx", "txt"}:
        raise HTTPException(status_code=400, detail="Supported formats: PDF, DOCX, TXT")

    internal_id = uuid.uuid4().hex[:8]
    ext = Path(file.filename or "").suffix.lower() or ".txt"
    upload_path = str(_UPLOAD_DIR / f"{internal_id}{ext}")

    content = await file.read()
    with open(upload_path, "wb") as f:
        f.write(content)

    cloud_doc_id = internal_id
    status = "processing"

    # Submit to PageIndex if available
    if pi_client:
        try:
            response = pi_client.submit_document(upload_path)
            cloud_doc_id = response.get("doc_id", internal_id)
            status = "processing"
        except Exception as e:
            print(f"PageIndex upload failed: {e}, using local mode")

    # Save to Database
    title = Path(file.filename or "document").stem.replace("_", " ").title()
    db_doc = Document(
        doc_id=cloud_doc_id,
        internal_id=internal_id,
        name=title,
        status=status,
        doc_type=doc_type,
        uploaded_by=admin.id
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)

    try:
        chunks = parse_document_to_chunks(
            upload_path, source_type=source_type,
            overlap_chars=app_settings.CHUNK_OVERLAP_CHARS,
        )
        db.query(DocumentChunk).filter(DocumentChunk.document_id == db_doc.id).delete()

        # Compute dense embeddings for all chunks in a single batch
        chunk_texts = [ch["content"][:1500] for ch in chunks]
        embeddings = EmbeddingManager.encode(chunk_texts)

        for i, ch in enumerate(chunks):
            emb = embeddings[i] if embeddings and i < len(embeddings) else None
            db.add(
                DocumentChunk(
                    document_id=db_doc.id,
                    chunk_index=ch["chunk_index"],
                    source_type=ch["source_type"],
                    section=ch.get("section"),
                    page_label=ch.get("page_label"),
                    content=ch["content"],
                    token_count=ch.get("token_count", 0),
                    embedding=emb,
                    embedding_model=app_settings.EMBEDDING_MODEL if emb else None,
                )
            )
        db_doc.status = "indexed" if chunks else "error"
        db.commit()

        # Backfill any chunks that missed embeddings (e.g., if model wasn't loaded yet)
        if not embeddings and chunks:
            compute_embeddings_for_chunks(db, db_doc.id)

        # Trigger PageIndex tree generation in background (non-blocking)
        if app_settings.ENABLE_PAGEINDEX_TREE and ext in ('.pdf', '.md'):
            import threading
            def _generate_tree_bg(doc_id_val, path_val):
                try:
                    from services.pageindex_service import generate_tree_for_document
                    from database import SessionLocal
                    bg_db = SessionLocal()
                    try:
                        generate_tree_for_document(bg_db, doc_id_val, path_val)
                    finally:
                        bg_db.close()
                except Exception as e:
                    print(f"[documents] Background tree generation failed: {e}")
            threading.Thread(
                target=_generate_tree_bg,
                args=(db_doc.id, upload_path),
                daemon=True,
            ).start()

    except Exception as e:
        db_doc.status = "error"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Document parsing failed: {e}")

    return DocumentInfo(
        id=internal_id,
        title=title,
        filename=file.filename,
        pages=0,
        doc_type=doc_type,
        status=DocumentStatus(db_doc.status if db_doc.status in VALID_STATUSES else "processing"),
        sections=0,
        last_queried="Never",
        tree=None
    )


@router.post("/reindex-all")
async def reindex_all_documents(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Re-submit every local PDF to PageIndex and reset status to processing. Admin only."""
    if not pi_client:
        raise HTTPException(status_code=503, detail="PageIndex SDK not available")

    db_docs = db.query(Document).all()
    results = []
    for doc in db_docs:
        # Use internal_id for the local file path (stable), fall back to doc_id for legacy rows
        file_key = doc.internal_id or doc.doc_id
        local_path = str(_UPLOAD_DIR / f"{file_key}.pdf")
        if not os.path.exists(local_path):
            results.append({"doc_id": file_key, "name": doc.name, "status": "skipped", "reason": "file_not_found"})
            continue
        try:
            response = pi_client.submit_document(local_path)
            new_cloud_id = response.get("doc_id") or doc.doc_id
            doc.doc_id = new_cloud_id
            # Backfill internal_id for legacy rows that predate this column
            if not doc.internal_id:
                doc.internal_id = file_key
            doc.status = "processing"
            db.commit()
            results.append({"doc_id": new_cloud_id, "internal_id": file_key, "name": doc.name, "status": "resubmitted"})
        except Exception as e:
            results.append({"doc_id": file_key, "name": doc.name, "status": "error", "reason": str(e)})

    submitted = sum(1 for r in results if r["status"] == "resubmitted")
    return {"total": len(results), "submitted": submitted, "results": results}



@router.delete("/{doc_id}")
def delete_document(doc_id: str, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Delete a document and its index. Admin only."""
    d = _find_doc(db, doc_id)
    if not d:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")

    if pi_client and d.doc_id:
        try:
            pi_client.delete_document(d.doc_id)
        except Exception:
            pass

    db.query(DocumentChunk).filter(DocumentChunk.document_id == d.id).delete()
    internal_key = d.internal_id or d.doc_id
    if internal_key:
        path = _resolve_existing_upload_path(internal_key)
        try:
            os.remove(path)
        except Exception:
            pass

    db.delete(d)
    db.commit()

    return {"message": f"Document '{d.name}' deleted successfully"}
