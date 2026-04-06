# ============================================================
# BoneQuest v2 — FastAPI Backend (Main Entry)
# ============================================================

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings

app = FastAPI(
    title="BoneQuest v2 API",
    description="Clinical-Grade Orthopaedic Decision Support — PageIndex + Groq",
    version="2.0.0",
)

# ── Database init ──────────────────────────────────────────
from database import engine, Base, ensure_sqlite_migrations
from models import db_models  # noqa: F401 — registers all models
Base.metadata.create_all(bind=engine)
ensure_sqlite_migrations()

# ── CORS ───────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount Routers ──────────────────────────────────────────
from routers import auth as auth_router
from routers import chat as chat_router
from routers import documents as doc_router
from routers import image as image_router
from routers import admin as admin_router

app.include_router(auth_router.router, prefix="/auth", tags=["Authentication"])
app.include_router(chat_router.router, prefix="/api/chat", tags=["Chat"])
app.include_router(chat_router.router, prefix="/api", tags=["Legacy Query"])  # backward compat
app.include_router(doc_router.router, prefix="/api/documents", tags=["Documents"])
app.include_router(image_router.router, prefix="/api/image", tags=["Image Analysis"])
app.include_router(admin_router.router, prefix="/api/admin", tags=["Admin"])

# ── Static files for uploaded images ───────────────────────
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "images"), exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# ── Health Check ───────────────────────────────────────────
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "2.0.0",
        "engine": "PageIndex + Groq LLaMA",
        "features": [
            "authentication",
            "chat_sessions",
            "image_analysis",
            "guideline_validation",
            "audit_trail",
            "admin_analytics",
        ]
    }


# ── Startup Event ──────────────────────────────────────────
@app.on_event("startup")
async def startup():
    print("🦴 BoneQuest v2 API starting...")
    print(f"   Environment: {settings.APP_ENV}")
    print(f"   Groq API: {'✓ configured' if settings.GROQ_API_KEY else '✗ missing'}")
    print(f"   PageIndex: {'✓ configured' if settings.PAGEINDEX_API_KEY else '✗ missing'}")
    print(f"   Database: {settings.DATABASE_URL}")
    print("   Ready! 🚀")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=False)
