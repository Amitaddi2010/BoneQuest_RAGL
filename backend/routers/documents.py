import os
import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from models.schemas import DocumentInfo, DocumentListResponse, DocumentStatus
from database import get_db
from models.db_models import Document, User
from sqlalchemy.orm import Session
from config import settings
from auth.permissions import require_admin

router = APIRouter()

# Try to import PageIndex client (optional dependency)
pi_client = None
try:
    from pageindex.client import PageIndexClient
    pi_client = PageIndexClient(api_key=settings.PAGEINDEX_API_KEY)
except ImportError:
    print("[documents] PageIndex SDK not installed. Document upload uses local-only mode.")
except Exception as e:
    print(f"[documents] PageIndex init failed: {e}")


@router.get("", response_model=DocumentListResponse)
def list_documents(db: Session = Depends(get_db)):
    """List all indexed documents from DB."""
    db_docs = db.query(Document).all()
    docs = []
    for d in db_docs:
        docs.append(DocumentInfo(
            id=d.doc_id,
            title=d.name,
            filename=d.name + ".pdf",
            pages=0,
            doc_type=d.doc_type,
            status=DocumentStatus(d.status) if d.status in ("processing", "indexed", "error") else DocumentStatus.processing,
            sections=0,
            last_queried="Recently",
            tree=None
        ))
    return DocumentListResponse(documents=docs, total=len(docs))


@router.get("/{doc_id}", response_model=DocumentInfo)
def get_document(doc_id: str, db: Session = Depends(get_db)):
    """Get a specific document."""
    d = db.query(Document).filter(Document.doc_id == doc_id).first()
    if not d:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")

    tree_data = None
    if pi_client:
        try:
            if pi_client.is_retrieval_ready(doc_id):
                tree_data = pi_client.get_tree(doc_id)
                d.status = "indexed"
                db.commit()
        except Exception:
            pass

    return DocumentInfo(
        id=d.doc_id,
        title=d.name,
        filename=d.name + ".pdf",
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
    """Upload a PDF and submit it to PageIndex. Admin only."""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    internal_id = uuid.uuid4().hex[:8]
    upload_path = os.path.join("data", "uploads", f"{internal_id}.pdf")
    os.makedirs(os.path.dirname(upload_path), exist_ok=True)

    content = await file.read()
    with open(upload_path, "wb") as f:
        f.write(content)

    cloud_doc_id = internal_id
    status = "indexed"

    # Submit to PageIndex if available
    if pi_client:
        try:
            response = pi_client.submit_document(upload_path)
            cloud_doc_id = response.get("doc_id", internal_id)
            status = "processing"
        except Exception as e:
            print(f"PageIndex upload failed: {e}, using local mode")

    # Save to Database
    title = file.filename.replace('.pdf', '').replace('_', ' ').title()
    db_doc = Document(
        doc_id=cloud_doc_id,
        name=title,
        status=status,
        doc_type=doc_type,
        uploaded_by=admin.id
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)

    return DocumentInfo(
        id=cloud_doc_id,
        title=title,
        filename=file.filename,
        pages=0,
        doc_type=doc_type,
        status=DocumentStatus(status),
        sections=0,
        last_queried="Never",
        tree=None
    )


@router.delete("/{doc_id}")
def delete_document(doc_id: str, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Delete a document and its index. Admin only."""
    d = db.query(Document).filter(Document.doc_id == doc_id).first()
    if not d:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")

    if pi_client:
        try:
            pi_client.delete_document(doc_id)
        except Exception:
            pass

    db.delete(d)
    db.commit()

    return {"message": f"Document '{d.name}' deleted successfully"}
