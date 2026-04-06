# ============================================================
# BoneQuest v2 — Chat Router (replaces query.py)
# ============================================================

import json
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
from services.pageindex_engine import PageIndexEngine

router = APIRouter()
engine = PageIndexEngine()


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
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "citations": m.citations,
                "confidence_score": m.confidence_score,
                "reasoning_trace": m.reasoning_trace,
                "tokens_used": m.tokens_used,
                "model_used": m.model_used,
                "user_feedback": m.user_feedback,
                "created_at": m.created_at.isoformat() + "Z" if m.created_at else "",
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
    
    msg = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
        
    msg.user_feedback = score
    db.commit()
    
    # Audit log the feedback
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

# ── Chat Message (with streaming) ──────────────────────────

@router.post("/message")
async def send_message(
    request: ChatMessageRequest,
    req: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message and get a streaming AI response."""
    # Verify session ownership
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

    # Auto-title on first message
    session_manager.auto_title(db, request.session_id, request.message)

    # Use the role from the user's account or from request
    role = UserRole(request.role) if request.role else UserRole(user.role)

    user_id = user.id
    client_host = req.client.host if req.client else None

    async def event_generator():
        try:
            # Generate response using the engine
            response = await engine.query(
                query=request.message,
                role=role,
                document_id=request.document_id,
            )

            # Send trace steps
            for trace in response.reasoning_trace:
                event = {
                    "type": "trace",
                    "step": trace.step,
                    "data": json.dumps({"action": trace.action, "detail": trace.detail})
                }
                yield f"data: {json.dumps(event)}\n\n"
                await asyncio.sleep(0.15)

            # Send citations
            if response.citations:
                event = {"type": "citation", "data": json.dumps(response.citations)}
                yield f"data: {json.dumps(event)}\n\n"

            # Stream answer token by token
            words = response.answer.split(' ')
            full_text = ""
            for i, word in enumerate(words):
                full_text += (" " if i > 0 else "") + word
                event = {"type": "token", "data": (" " if i > 0 else "") + word}
                yield f"data: {json.dumps(event)}\n\n"
                await asyncio.sleep(0.02)

            # Send confidence
            event = {"type": "confidence", "data": str(response.confidence)}
            yield f"data: {json.dumps(event)}\n\n"

            # Save assistant message to DB first to get ID
            msg = session_manager.add_message(
                db=db,
                session_id=request.session_id,
                role="assistant",
                content=response.answer,
                citations=response.citations,
                confidence_score=response.confidence,
                reasoning_trace=[{"step": t.step, "action": t.action, "detail": t.detail} for t in response.reasoning_trace],
                model_used=response.model,
            )

            # Send the database message ID so the frontend can attach feedback
            event = {"type": "message_id", "data": str(msg.id)}
            yield f"data: {json.dumps(event)}\n\n"

            # Audit log
            audit = AuditLog(
                user_id=user_id,
                action="chat_query",
                resource_type="session",
                resource_id=request.session_id,
                details={
                    "query_length": len(request.message),
                    "role": role.value,
                    "confidence": response.confidence,
                    "citations_count": len(response.citations),
                    "model": response.model,
                },
                ip_address=client_host,
            )
            db.add(audit)
            db.commit()

            yield f"data: [DONE]\n\n"

        except Exception as e:
            error_event = {"type": "error", "data": str(e)}
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ── Legacy query endpoint (no auth required for backward compat) ──

@router.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Submit a clinical query (legacy endpoint, no auth)."""
    try:
        response = await engine.query(
            query=request.query,
            role=request.role,
            document_id=request.document_id,
            num_hops=request.num_hops,
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query/stream")
async def stream_query(request: QueryRequest):
    """Stream a clinical query response (legacy endpoint, no auth)."""

    async def event_generator():
        try:
            response = await engine.query(
                query=request.query,
                role=request.role,
                document_id=request.document_id,
                num_hops=request.num_hops,
            )

            # Send trace steps
            for trace in response.reasoning_trace:
                event = {
                    "type": "trace",
                    "step": trace.step,
                    "data": json.dumps({"action": trace.action, "detail": trace.detail})
                }
                yield f"data: {json.dumps(event)}\n\n"
                await asyncio.sleep(0.15)

            # Stream answer
            words = response.answer.split(' ')
            for i, word in enumerate(words):
                event = {"type": "token", "data": (" " if i > 0 else "") + word}
                yield f"data: {json.dumps(event)}\n\n"
                await asyncio.sleep(0.02)

            # Confidence
            event = {"type": "confidence", "data": str(response.confidence)}
            yield f"data: {json.dumps(event)}\n\n"

            yield f"data: [DONE]\n\n"

        except Exception as e:
            error_event = {"type": "error", "data": str(e)}
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
