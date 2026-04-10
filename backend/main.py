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
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount Routers ──────────────────────────────────────────
from routers import auth as auth_router
from routers import chat as chat_router
from routers import documents as doc_router
from routers import image as image_router
from routers import admin as admin_router
from routers import indexing as indexing_router
query_router = None
try:
    from routers import query as query_router
except Exception as e:
    print(f"[main] PageIndex query router disabled: {e}")

app.include_router(auth_router.router, prefix="/auth", tags=["Authentication"])
app.include_router(chat_router.router, prefix="/api/chat", tags=["Chat"])
app.include_router(chat_router.router, prefix="/api", tags=["Legacy Query"])  # backward compat
if query_router:
    app.include_router(query_router.router, prefix="/api/pi", tags=["PageIndex Query"])
app.include_router(doc_router.router, prefix="/api/documents", tags=["Documents"])
app.include_router(image_router.router, prefix="/api/image", tags=["Image Analysis"])
app.include_router(admin_router.router, prefix="/api/admin", tags=["Admin"])
app.include_router(indexing_router.router, prefix="/api/index", tags=["Hierarchical Indexing"])

# ── Static files for uploaded images ───────────────────────
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "images"), exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# ── Health Check ───────────────────────────────────────────
@app.get("/")
@app.get("/health")
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

    # Ensure default admin exists
    try:
        from create_admin import create_admin
        create_admin()
    except Exception as e:
        print(f"   [!] Failed to create default admin: {e}")

    # Preload embedding model at startup so first query is fast
    if settings.ENABLE_SEMANTIC_RETRIEVAL:
        print("   Loading embedding model...", end=" ", flush=True)
        try:
            from services.hybrid_retriever import EmbeddingManager, compute_embeddings_for_chunks
            ready = EmbeddingManager.warmup()
            print(f"{'✓ loaded' if ready else '✗ unavailable'}")

            # Backfill embeddings for any existing chunks that don't have them
            if ready:
                from database import SessionLocal
                from models.db_models import DocumentChunk, Document
                db = SessionLocal()
                try:
                    missing_count = db.query(DocumentChunk).filter(
                        DocumentChunk.embedding.is_(None)
                    ).count()
                    if missing_count > 0:
                        print(f"   Backfilling embeddings for {missing_count} chunks...", end=" ", flush=True)
                        docs = db.query(Document).filter(Document.status == "indexed").all()
                        total = 0
                        for doc in docs:
                            n = compute_embeddings_for_chunks(db, doc.id)
                            total += n
                        print(f"✓ {total} chunks embedded")
                    else:
                        print("   All chunks have embeddings ✓")
                finally:
                    db.close()
        except Exception as e:
            print(f"✗ error: {e}")

    # Show PageIndex Tree RAG status
    if settings.ENABLE_PAGEINDEX_TREE:
        print(f"   PageIndex Tree RAG: ✓ enabled (model: {settings.PAGEINDEX_MODEL})")
        try:
            from database import SessionLocal
            from models.db_models import DocumentTree
            db = SessionLocal()
            try:
                tree_count = db.query(DocumentTree).count()
                print(f"   Document trees: {tree_count} indexed")
            finally:
                db.close()
        except Exception:
            print("   Document trees: 0 (tables initializing)")
    else:
        print("   PageIndex Tree RAG: ✗ disabled")

    print("   Ready! 🚀")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=False)
