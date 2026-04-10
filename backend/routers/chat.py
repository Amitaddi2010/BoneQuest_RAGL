# ============================================================
# BoneQuest v2 — Chat Router (V2: Thinking Block + Rich Citations)
# ============================================================

import json
import uuid
import asyncio
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models.schemas import (
    ChatSessionCreate, ChatSessionResponse, ChatSessionListResponse,
    ChatMessageRequest, ChatMessageResponse, QueryRequest, QueryResponse,
    TraceStep, UserRole
)
from models.db_models import User, ChatSession, ChatMessage, AuditLog
from auth.permissions import get_current_user, get_optional_user
from chat.session_manager import session_manager
from chat.conversation_manager import conversation_manager
from services.context_chat_engine import ContextChatEngine

router = APIRouter()
engine = ContextChatEngine()


# ── Session Management ─────────────────────────────────────

@router.post("/sessions", response_model=ChatSessionResponse)
async def create_session(
    request: ChatSessionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new chat session."""
    session = session_manager.create_session(
        db=db,
        user_id=user.id,
        title=request.title,
        context=request.context
    )
    return session_manager.get_session_with_message_count(db, session)


@router.get("/sessions", response_model=ChatSessionListResponse)
async def list_sessions(
    skip: int = 0,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all chat sessions for the current user."""
    sessions = session_manager.list_sessions(db, user.id, skip, limit)
    total = session_manager.count_sessions(db, user.id)
    return ChatSessionListResponse(
        sessions=[session_manager.get_session_with_message_count(db, s) for s in sessions],
        total=total
    )


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific chat session."""
    session = session_manager.get_session(db, session_id, user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session_manager.get_session_with_message_count(db, session)


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Soft delete a chat session."""
    success = session_manager.delete_session(db, session_id, user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted"}


@router.patch("/sessions/{session_id}/rename")
async def rename_session(
    session_id: str,
    title: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Rename a chat session."""
    success = session_manager.rename_session(db, session_id, user.id, title)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session renamed"}


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all messages in a session."""
    session = session_manager.get_session(db, session_id, user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = session_manager.get_messages(db, session_id)
    return {
        "session_id": session_id,
        "messages": [
            {
                "id":               m.id,
                "role":             m.role,
                "content":          m.content,
                "citations":        m.citations,
                "confidence_score": m.confidence_score,
                "reasoning_trace":  m.reasoning_trace,
                "tokens_used":      m.tokens_used,
                "model_used":       m.model_used,
                "user_feedback":    m.user_feedback,
                "created_at":       m.created_at.isoformat() + "Z" if m.created_at else "",
            }
            for m in messages
        ]
    }


@router.post("/messages/{message_id}/feedback")
async def give_feedback(
    message_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Provide thumbs up (1) or thumbs down (-1) feedback to a specific AI message."""
    data = await request.json()
    score = data.get("score", 0)
    if score not in (-1, 1):
        raise HTTPException(status_code=400, detail="Score must be 1 or -1")

    msg = (
        db.query(ChatMessage)
        .join(ChatSession, ChatSession.id == ChatMessage.session_id)
        .filter(ChatMessage.id == message_id, ChatSession.user_id == user.id)
        .first()
    )
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    msg.user_feedback = score
    db.commit()

    audit = AuditLog(
        user_id=user.id,
        action="chat_feedback",
        resource_type="message",
        resource_id=message_id,
        details={"score": score},
    )
    db.add(audit)
    db.commit()

    return {"message": "Feedback recorded", "score": score}


# ── Chat Message (streaming with thinking block) ────────────

@router.post("/message")
async def send_message(
    request: ChatMessageRequest,
    req: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message; streams thinking → trace → tokens → citations → confidence → done."""

    session = session_manager.get_session(db, request.session_id, user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Save user message
    session_manager.add_message(
        db=db,
        session_id=request.session_id,
        role="user",
        content=request.message
    )
    session_manager.auto_title(db, request.session_id, request.message)

    role = UserRole(request.role) if request.role else UserRole(user.role)
    user_id = user.id
    client_host = req.client.host if req.client else None

    # Build history array for the intent classifier
    history_records = db.query(ChatMessage).filter(
        ChatMessage.session_id == request.session_id
    ).order_by(ChatMessage.created_at.desc()).limit(10).all()
    history = [{"role": m.role, "content": m.content} for m in reversed(history_records)]

    async def event_generator():
        try:
            # Consume the unified generator
            async for event in engine.generate_response_stream(
                db=db,
                query=request.message,
                role=role,
                document_id=request.document_id,
                history=history,
                max_context_tokens=request.max_context_tokens,
                max_context_chunks=request.max_context_chunks,
            ):
                if event["type"] == "final_payload":
                    data = event["data"]
                    # Save DB record
                    msg = session_manager.add_message(
                        db=db,
                        session_id=request.session_id,
                        role="assistant",
                        content=data.get("answer", ""),
                        citations=data.get("citations", []),
                        confidence_score=data.get("confidence", 0.0),
                        reasoning_trace=data.get("trace", []),
                        model_used=data.get("model", ""),
                        metadata_extra={"retrieval": data.get("retrieval", {})},
                    )
                    
                    # Yield message ID so frontend can tie feedback to it
                    yield f"data: {json.dumps({'type': 'message_id', 'data': str(msg.id)})}\n\n"
                    # Yield retrieval diagnostics so UI can render accurate grounding state.
                    yield f"data: {json.dumps({'type': 'retrieval_meta', 'data': data.get('retrieval', {})})}\n\n"
                    
                    # Log to audit table
                    audit = AuditLog(
                        user_id=user_id,
                        action="chat_query",
                        resource_type="session",
                        resource_id=request.session_id,
                        details={
                            "query_length": len(request.message),
                            "role": role.value,
                            "intent": data.get("intent", "clinical"),
                            "confidence": data.get("confidence", 0.0),
                            "model": data.get("model", ""),
                        },
                        ip_address=client_host,
                    )
                    db.add(audit)
                    db.commit()
                else:
                    # Default: Just stream it downstream
                    yield f"data: {json.dumps(event)}\n\n"
                    if event["type"] in ["trace", "thinking", "token"]:
                        await asyncio.sleep(0.015)

        except Exception as e:
            error_event = {"type": "error", "data": str(e)}
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection":    "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/query", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    user: User = Depends(get_current_user),
):
    """Submit a clinical query (legacy endpoint, auth required)."""
    try:
        final_payload = None
        async for event in engine.generate_response_stream(
            db=None,
            query=request.query,
            role=UserRole.resident,
            document_id=request.document_id,
            history=[],
            max_context_tokens=request.max_context_tokens,
            max_context_chunks=request.max_context_chunks,
        ):
            if event["type"] == "final_payload":
                final_payload = event["data"]
                
        if not final_payload:
            raise HTTPException(status_code=500, detail="No final payload yielded")
            
        return QueryResponse(
            id=f"q-{uuid.uuid4().hex[:8]}",
            answer=final_payload.get("answer", ""),
            confidence=final_payload.get("confidence", 0.0),
            citations=final_payload.get("citations", []),
            reasoning_trace=[TraceStep(**t) for t in final_payload.get("trace", [])],
            role=UserRole.resident,
            model=final_payload.get("model", "")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query/stream")
async def stream_query(
    request: QueryRequest,
    user: User = Depends(get_current_user),
):
    """Stream a clinical query response (legacy endpoint, auth required)."""

    async def event_generator():
        try:
            async for event in engine.generate_response_stream(
                db=None,
                query=request.query,
                role=UserRole.resident,
                document_id=request.document_id,
                history=[],
                max_context_tokens=request.max_context_tokens,
                max_context_chunks=request.max_context_chunks,
            ):
                if event["type"] == "final_payload":
                    continue  # We don't need to yield this for basic streaming
                yield f"data: {json.dumps(event)}\n\n"
                if event["type"] in ["trace", "thinking", "token"]:
                    await asyncio.sleep(0.015)
        except Exception as e:
            error_event = {"type": "error", "data": str(e)}
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection":    "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
