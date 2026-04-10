# ============================================================
# BoneQuest v2 — Pydantic Schemas
# ============================================================

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Any
from enum import Enum
from datetime import datetime


# --- Enums ---
class UserRole(str, Enum):
    patient = "patient"
    resident = "resident"
    consultant = "consultant"
    admin = "admin"


class DocumentStatus(str, Enum):
    processing = "processing"
    indexed = "indexed"
    error = "error"


class ValidationStatus(str, Enum):
    pending_review = "pending_review"
    confirmed = "confirmed"
    rejected = "rejected"


class EvidenceStrength(str, Enum):
    strong = "strong"
    moderate = "moderate"
    limited = "limited"
    inconclusive = "inconclusive"


# --- Auth Schemas ---
class SignUpRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)
    hospital_id: Optional[str] = None
    role: UserRole = UserRole.resident


class SignInRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: "UserResponse"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    hospital_id: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6, max_length=128)


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    hospital_id: Optional[str] = None
    role: UserRole
    is_active: bool = True
    created_at: Optional[str] = None
    last_login: Optional[str] = None

    class Config:
        from_attributes = True


# --- Document Schemas ---
class DocumentInfo(BaseModel):
    id: str
    title: str
    filename: str
    pages: int = 0
    doc_type: str = "general"
    status: DocumentStatus = DocumentStatus.processing
    sections: int = 0
    last_queried: str = "Never"
    tree: Optional[dict] = None


class DocumentListResponse(BaseModel):
    documents: List[DocumentInfo]
    total: int


# --- Query / Chat Schemas ---
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    document_id: Optional[str] = None
    num_hops: int = Field(default=3, ge=1, le=5)
    max_context_tokens: Optional[int] = Field(default=None, ge=500, le=12000)
    max_context_chunks: Optional[int] = Field(default=None, ge=1, le=20)


class TraceStep(BaseModel):
    step: int
    action: str
    detail: str


class Citation(BaseModel):
    guideline_id: Optional[str] = None
    guideline_name: Optional[str] = None
    guideline: Optional[str] = None
    section: Optional[str] = None
    page_range: Optional[str] = None
    evidence_strength: Optional[str] = EvidenceStrength.moderate.value
    reasoning: Optional[str] = None
    content: Optional[str] = None
    snippet: Optional[str] = None
    score: Optional[float] = None
    overlap_ratio: Optional[float] = None
    match_type: Optional[str] = None
    text: Optional[str] = None


class QueryResponse(BaseModel):
    id: str
    answer: str
    confidence: float = Field(ge=0, le=1)
    citations: List[Citation] = []
    reasoning_trace: List[TraceStep] = []
    role: UserRole
    model: str = "groq/llama-3.3-70b-versatile"


# --- Chat Session Schemas ---
class ChatSessionCreate(BaseModel):
    title: Optional[str] = None
    context: Optional[dict] = None


class ChatSessionResponse(BaseModel):
    id: str
    title: Optional[str] = None
    context: Optional[dict] = None
    created_at: str
    updated_at: str
    message_count: int = 0
    last_message_preview: Optional[str] = None

    class Config:
        from_attributes = True


class ChatSessionListResponse(BaseModel):
    sessions: List[ChatSessionResponse]
    total: int


class ChatMessageRequest(BaseModel):
    session_id: str
    message: str = Field(..., min_length=1, max_length=4000)
    role: UserRole = UserRole.resident
    document_id: Optional[str] = None
    image_url: Optional[str] = None
    max_context_tokens: Optional[int] = Field(default=None, ge=500, le=12000)
    max_context_chunks: Optional[int] = Field(default=None, ge=1, le=20)


class ChatMessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    citations: Optional[List[Citation]] = None
    confidence_score: Optional[float] = None
    reasoning_trace: Optional[List[dict]] = None
    tokens_used: Optional[int] = None
    model_used: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


# --- Image Analysis Schemas ---
class ImageAnalysisRequest(BaseModel):
    query: Optional[str] = None
    session_id: Optional[str] = None


class ImageFinding(BaseModel):
    name: str
    confidence: float = 0.0
    description: Optional[str] = None


class ImageAnalysisResponse(BaseModel):
    id: str
    filename: str
    image_type: Optional[str] = None
    raw_analysis: Optional[str] = None
    findings: List[ImageFinding] = []
    recommendations: List[str] = []
    confidence_score: float = 0.0
    validation_status: ValidationStatus = ValidationStatus.pending_review
    ai_disclaimer: str = "This analysis is for educational purposes. Clinical decisions must be based on radiologist interpretation."
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


# --- Admin Schemas ---
class AnalyticsResponse(BaseModel):
    daily_active_users: int = 0
    total_users: int = 0
    total_sessions: int = 0
    total_queries: int = 0
    most_queried_conditions: List[dict] = []
    average_confidence: float = 0.0
    queries_by_role: dict = {}
    queries_by_day: List[dict] = []
    system_uptime: float = 99.9
    average_response_time_ms: float = 0.0
    total_validated: int = 0
    total_flagged: int = 0


class AuditLogEntry(BaseModel):
    id: int
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    entries: List[AuditLogEntry]
    total: int
    page: int = 1
    per_page: int = 50


# --- Stream Event ---
class StreamEvent(BaseModel):
    type: str  # "trace", "token", "citation", "done"
    data: str = ""
    step: Optional[int] = None
