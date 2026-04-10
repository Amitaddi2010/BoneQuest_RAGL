# ============================================================
# BoneQuest v2 — Chat Session Manager
# ============================================================

import json
from datetime import datetime
from typing import Optional, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from models.db_models import ChatSession, ChatMessage, User


def _normalize_json_context(raw: Any) -> Optional[dict]:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None
    return None


class SessionManager:
    """Manages chat sessions and message persistence."""

    @staticmethod
    def create_session(db: Session, user_id: str, title: Optional[str] = None, context: Optional[dict] = None) -> ChatSession:
        """Create a new chat session."""
        session = ChatSession(
            user_id=user_id,
            title=title or "New Chat",
            context=context,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def get_session(db: Session, session_id: str, user_id: str) -> Optional[ChatSession]:
        """Get a session (only if owned by user)."""
        return db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id,
            ChatSession.is_deleted == False
        ).first()

    @staticmethod
    def list_sessions(db: Session, user_id: str, skip: int = 0, limit: int = 50) -> List[ChatSession]:
        """List all sessions for a user, most recent first."""
        return db.query(ChatSession).filter(
            ChatSession.user_id == user_id,
            ChatSession.is_deleted == False
        ).order_by(desc(ChatSession.updated_at)).offset(skip).limit(limit).all()

    @staticmethod
    def count_sessions(db: Session, user_id: str) -> int:
        """Count total sessions for a user."""
        return db.query(func.count(ChatSession.id)).filter(
            ChatSession.user_id == user_id,
            ChatSession.is_deleted == False
        ).scalar()

    @staticmethod
    def delete_session(db: Session, session_id: str, user_id: str) -> bool:
        """Soft delete a session."""
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id,
        ).first()
        if not session:
            return False
        session.is_deleted = True
        session.deleted_at = datetime.utcnow()
        db.commit()
        return True

    @staticmethod
    def rename_session(db: Session, session_id: str, user_id: str, new_title: str) -> bool:
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id,
            ChatSession.is_deleted == False
        ).first()
        if not session:
            return False
        session.title = new_title
        session.updated_at = datetime.utcnow()
        db.commit()
        return True

    @staticmethod
    def add_message(
        db: Session,
        session_id: str,
        role: str,
        content: str,
        citations: list = None,
        confidence_score: float = None,
        reasoning_trace: list = None,
        tokens_used: int = None,
        model_used: str = None,
        metadata_extra: dict = None,
    ) -> ChatMessage:
        """Add a message to a session."""
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            citations=citations,
            confidence_score=confidence_score,
            reasoning_trace=reasoning_trace,
            tokens_used=tokens_used,
            model_used=model_used,
            metadata_extra=metadata_extra,
        )
        db.add(message)

        # Update session timestamp
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session:
            session.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(message)
        return message

    @staticmethod
    def get_messages(db: Session, session_id: str, skip: int = 0, limit: int = 200) -> List[ChatMessage]:
        """Get all messages in a session."""
        return db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at).offset(skip).limit(limit).all()

    @staticmethod
    def auto_title(db: Session, session_id: str, first_message: str):
        """Auto-generate session title from first message."""
        title = first_message[:80].strip()
        if len(first_message) > 80:
            title += "..."
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session and (session.title == "New Chat" or session.title is None):
            session.title = title
            db.commit()

    @staticmethod
    def get_session_with_message_count(db: Session, session: ChatSession) -> dict:
        """Get session info with message count and preview."""
        msg_count = db.query(func.count(ChatMessage.id)).filter(
            ChatMessage.session_id == session.id
        ).scalar()

        last_msg = db.query(ChatMessage).filter(
            ChatMessage.session_id == session.id,
            ChatMessage.role == "user"
        ).order_by(desc(ChatMessage.created_at)).first()

        preview = None
        if last_msg:
            preview = last_msg.content[:100] + ("..." if len(last_msg.content) > 100 else "")

        return {
            "id": session.id,
            "title": session.title,
            "context": _normalize_json_context(session.context),
            "created_at": session.created_at.isoformat() + "Z" if session.created_at else "",
            "updated_at": session.updated_at.isoformat() + "Z" if session.updated_at else "",
            "message_count": int(msg_count or 0),
            "last_message_preview": preview,
        }


session_manager = SessionManager()
