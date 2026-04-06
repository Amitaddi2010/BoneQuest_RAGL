# ============================================================
# BoneQuest v2 — Image Analysis Router
# ============================================================

import os
import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models.db_models import User, ImageAnalysis, AuditLog
from models.schemas import ImageAnalysisResponse, ImageFinding
from auth.permissions import get_current_user
from image_analysis.groq_vision import vision_analyzer
from config import settings

router = APIRouter()

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/jpg", "image/webp"}


@router.post("/analyze", response_model=ImageAnalysisResponse)
async def analyze_image(
    req: Request,
    file: UploadFile = File(...),
    query: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload and analyze a medical image using Groq vision."""

    # Validate file type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Allowed: JPEG, PNG, WebP"
        )

    # Read file
    image_bytes = await file.read()

    # Validate file size
    if len(image_bytes) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum: {settings.MAX_UPLOAD_SIZE_MB}MB"
        )

    # Save file
    file_id = uuid.uuid4().hex[:12]
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg"
    save_path = os.path.join(settings.UPLOAD_DIR, "images", f"{file_id}.{ext}")
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    with open(save_path, "wb") as f:
        f.write(image_bytes)

    # Analyze with Groq vision
    analysis = await vision_analyzer.analyze_image(
        image_bytes=image_bytes,
        filename=file.filename,
        content_type=file.content_type,
        specific_query=query,
    )

    # Save to database
    db_analysis = ImageAnalysis(
        user_id=user.id,
        session_id=session_id,
        filename=file.filename,
        file_path=save_path,
        image_type=analysis.get("image_type"),
        raw_analysis=analysis.get("raw_analysis"),
        findings=analysis.get("findings"),
        recommendations=analysis.get("recommendations"),
        confidence_score=analysis.get("confidence_score", 0.0),
        validation_status=analysis.get("validation_status", "pending_review"),
        ai_disclaimer=analysis.get("ai_disclaimer"),
    )
    db.add(db_analysis)

    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action="image_analysis",
        resource_type="image",
        resource_id=db_analysis.id,
        details={
            "filename": file.filename,
            "file_size": len(image_bytes),
            "image_type": analysis.get("image_type"),
            "findings_count": len(analysis.get("findings", [])),
            "query": query,
        },
        ip_address=req.client.host if req.client else None,
    )
    db.add(audit)
    db.commit()
    db.refresh(db_analysis)

    # Build response
    findings = [
        ImageFinding(
            name=f.get("name", ""),
            confidence=f.get("confidence", 0.0),
            description=f.get("description", ""),
        )
        for f in analysis.get("findings", [])
    ]

    return ImageAnalysisResponse(
        id=db_analysis.id,
        filename=file.filename,
        image_type=analysis.get("image_type"),
        raw_analysis=analysis.get("raw_analysis"),
        findings=findings,
        recommendations=analysis.get("recommendations", []),
        confidence_score=analysis.get("confidence_score", 0.0),
        validation_status=analysis.get("validation_status", "pending_review"),
        ai_disclaimer=analysis.get("ai_disclaimer", ""),
        created_at=db_analysis.created_at.isoformat() if db_analysis.created_at else None,
    )


@router.get("/{analysis_id}", response_model=ImageAnalysisResponse)
async def get_analysis(
    analysis_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific image analysis result."""
    analysis = db.query(ImageAnalysis).filter(
        ImageAnalysis.id == analysis_id,
        ImageAnalysis.user_id == user.id
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    findings = [
        ImageFinding(name=f.get("name", ""), confidence=f.get("confidence", 0.0), description=f.get("description", ""))
        for f in (analysis.findings or [])
    ]

    return ImageAnalysisResponse(
        id=analysis.id,
        filename=analysis.filename,
        image_type=analysis.image_type,
        raw_analysis=analysis.raw_analysis,
        findings=findings,
        recommendations=analysis.recommendations or [],
        confidence_score=analysis.confidence_score or 0.0,
        validation_status=analysis.validation_status or "pending_review",
        ai_disclaimer=analysis.ai_disclaimer or "",
        created_at=analysis.created_at.isoformat() if analysis.created_at else None,
    )
