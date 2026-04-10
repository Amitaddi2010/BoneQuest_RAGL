# ============================================================
# BoneQuest v2 — Admin Router
# ============================================================

from datetime import datetime, timedelta
import os
import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional, List, Dict, Any

from database import get_db
from models.db_models import User, ChatSession, ChatMessage, AuditLog, ImageAnalysis, Document
from models.schemas import AnalyticsResponse, AuditLogEntry, AuditLogListResponse, UserResponse
from auth.permissions import require_admin
from evals.run_local_rag_eval import run_eval
from services.local_retriever import LocalRetriever

router = APIRouter()


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    days: int = Query(default=7, ge=1, le=90),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get system analytics. Admin only."""
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Total users
    total_users = db.query(func.count(User.id)).scalar()

    # Active users in period
    daily_active = db.query(func.count(func.distinct(ChatMessage.session_id))).filter(
        ChatMessage.created_at >= cutoff
    ).scalar()

    # Total sessions
    total_sessions = db.query(func.count(ChatSession.id)).filter(
        ChatSession.is_deleted == False
    ).scalar()

    # Total queries
    total_queries = db.query(func.count(ChatMessage.id)).filter(
        ChatMessage.role == "user"
    ).scalar()

    # Average confidence
    avg_confidence = db.query(func.avg(ChatMessage.confidence_score)).filter(
        ChatMessage.role == "assistant",
        ChatMessage.confidence_score.isnot(None)
    ).scalar() or 0.0

    # Queries by role - via audit log
    role_counts = db.query(
        func.json_extract(AuditLog.details, '$.role'),
        func.count(AuditLog.id)
    ).filter(
        AuditLog.action == "chat_query"
    ).group_by(
        func.json_extract(AuditLog.details, '$.role')
    ).all()
    queries_by_role = {str(r[0] or "unknown"): r[1] for r in role_counts}

    # QA Feedback stats
    total_validated = db.query(func.count(ChatMessage.id)).filter(ChatMessage.user_feedback == 1).scalar() or 0
    total_flagged = db.query(func.count(ChatMessage.id)).filter(ChatMessage.user_feedback == -1).scalar() or 0

    # Queries per day
    queries_by_day = []
    for i in range(min(days, 30)):
        day = datetime.utcnow() - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = db.query(func.count(ChatMessage.id)).filter(
            ChatMessage.role == "user",
            ChatMessage.created_at >= day_start,
            ChatMessage.created_at < day_end
        ).scalar()
        queries_by_day.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "count": count
        })
    queries_by_day.reverse()

    return {
        "daily_active_users": daily_active or 0,
        "total_users": total_users or 0,
        "total_sessions": total_sessions or 0,
        "total_queries": total_queries or 0,
        "average_confidence": round(float(avg_confidence), 3),
        "queries_by_role": queries_by_role,
        "queries_by_day": queries_by_day,
        "total_validated": total_validated,
        "total_flagged": total_flagged,
    }


@router.get("/audit-log", response_model=AuditLogListResponse)
async def get_audit_log(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=10, le=200),
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get paginated audit log. Admin only."""
    query = db.query(AuditLog)

    if action:
        query = query.filter(AuditLog.action == action)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)

    total = query.count()
    entries = query.order_by(desc(AuditLog.created_at)).offset(
        (page - 1) * per_page
    ).limit(per_page).all()

    # Enrich with user email
    result_entries = []
    for entry in entries:
        u = db.query(User).filter(User.id == entry.user_id).first() if entry.user_id else None
        result_entries.append(AuditLogEntry(
            id=entry.id,
            user_id=entry.user_id,
            user_email=u.email if u else None,
            action=entry.action,
            resource_type=entry.resource_type,
            resource_id=entry.resource_id,
            details=entry.details,
            ip_address=entry.ip_address,
            created_at=entry.created_at.isoformat() if entry.created_at else "",
        ))

    return AuditLogListResponse(
        entries=result_entries,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/users")
async def list_users(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=10, le=200),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List all users. Admin only."""
    total = db.query(func.count(User.id)).scalar()
    users = db.query(User).order_by(desc(User.created_at)).offset(
        (page - 1) * per_page
    ).limit(per_page).all()

    return {
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "hospital_id": u.hospital_id,
                "role": u.role,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "last_login": u.last_login.isoformat() if u.last_login else None,
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.patch("/users/{target_user_id}")
async def update_user(
    target_user_id: str,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update user role or status. Admin only."""
    target = db.query(User).filter(User.id == target_user_id).first()
    if not target:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")

    if role is not None and role in ("patient", "resident", "consultant", "admin"):
        target.role = role
    if is_active is not None:
        target.is_active = is_active

    target.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "User updated", "user_id": target_user_id}
@router.get("/qa-feed")
async def get_qa_feed(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=10, le=200),
    score: Optional[int] = None,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get AI responses that have received clinician feedback. Admin only."""
    query = db.query(ChatMessage).filter(
        ChatMessage.role == "assistant",
        ChatMessage.user_feedback != 0
    )

    if score is not None:
        query = query.filter(ChatMessage.user_feedback == score)

    total = query.count()
    messages = query.order_by(desc(ChatMessage.created_at)).offset(
        (page - 1) * per_page
    ).limit(per_page).all()

    return {
        "messages": [
            {
                "id": m.id,
                "session_id": m.session_id,
                "content": m.content,
                "feedback": m.user_feedback,
                "confidence": m.confidence_score,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
        "total": total,
        "page": page,
        "per_page": per_page
    }


@router.post("/eval/local-rag")
async def run_local_rag_eval(
    eval_set_path: Optional[str] = None,
    user: User = Depends(require_admin),
):
    """Run local hybrid RAG eval set and return metrics. Admin only."""
    base_dir = os.path.dirname(os.path.dirname(__file__))
    default_path = os.path.join(base_dir, "evals", "local_rag_eval_set.json")
    path = eval_set_path or default_path
    if not os.path.exists(path):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Eval set not found: {path}")
    return await run_eval(path)


@router.post("/local-docs/import")
async def import_local_pdfs(
    folder_path: str,
    doc_type: str = "general",
    recursive: bool = True,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Import a local folder of PDFs into backend data/uploads and register them in DB.
    This is how you test local hybrid RAG on real PDFs (no PageIndex cloud).
    Admin only.
    """
    src_dir = Path(folder_path).expanduser()
    if not src_dir.exists() or not src_dir.is_dir():
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Folder not found: {folder_path}")

    backend_dir = Path(__file__).resolve().parent.parent
    upload_dir = backend_dir / "data" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    pattern = "**/*.pdf" if recursive else "*.pdf"
    pdfs = sorted(src_dir.glob(pattern))
    if not pdfs:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"No PDFs found in: {folder_path}")

    results: List[Dict[str, Any]] = []
    for pdf_path in pdfs:
        internal_id = uuid.uuid4().hex[:8]
        dest_path = upload_dir / f"{internal_id}.pdf"
        title = pdf_path.stem.replace("_", " ").replace("-", " ").strip().title()

        try:
            shutil.copyfile(str(pdf_path), str(dest_path))
            row = Document(
                doc_id=internal_id,
                internal_id=internal_id,
                name=title or internal_id,
                status="indexed",
                doc_type=doc_type if doc_type in ("general", "guideline") else "general",
                uploaded_by=user.id,
            )
            db.add(row)
            db.commit()
            results.append(
                {
                    "internal_id": internal_id,
                    "title": title,
                    "filename": pdf_path.name,
                    "status": "imported",
                }
            )
        except Exception as e:
            db.rollback()
            results.append(
                {
                    "filename": pdf_path.name,
                    "status": "error",
                    "error": str(e),
                }
            )

    imported = sum(1 for r in results if r.get("status") == "imported")
    return {"total_found": len(pdfs), "imported": imported, "results": results[:50]}


@router.get("/local-docs/test-retrieval")
async def test_local_retrieval(
    document_id: str,
    query: str,
    top_k: int = Query(default=4, ge=1, le=10),
    clear_cache: bool = False,
    user: User = Depends(require_admin),
):
    """
    Retrieval-only test endpoint: returns the exact top chunks/citations from local PDFs.
    Admin only.
    """
    backend_dir = Path(__file__).resolve().parent.parent
    upload_dir = backend_dir / "data" / "uploads"
    retriever = LocalRetriever(uploads_dir=str(upload_dir))
    if clear_cache:
        retriever.clear_cache(document_id=document_id)
    has_doc = retriever.has_local_doc(document_id)
    citations = retriever.retrieve(query=query, document_id=document_id, top_k=top_k) if has_doc else []
    return {
        "document_id": document_id,
        "has_local_doc": has_doc,
        "top_k": top_k,
        "citations_count": len(citations),
        "citations": citations,
    }
