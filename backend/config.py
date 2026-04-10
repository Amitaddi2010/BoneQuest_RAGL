# ============================================================
# BoneQuest v2 — Configuration
# ============================================================

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings:
    """Application settings loaded from environment variables."""

    # --- API Keys ---
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    PAGEINDEX_API_KEY: str = os.getenv("PAGEINDEX_API_KEY", "")

    # --- JWT / Auth ---
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev-secret-key")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # --- Database ---
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./bonequest.db")

    # --- App ---
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_DEBUG: bool = os.getenv("APP_DEBUG", "true").lower() == "true"
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

    # --- Groq Models ---
    GROQ_TEXT_MODEL: str = os.getenv("GROQ_TEXT_MODEL", "llama-3.3-70b-versatile")
    GROQ_SMALL_MODEL: str = os.getenv("GROQ_SMALL_MODEL", "llama-3.1-8b-instant")
    GROQ_VISION_MODEL: str = os.getenv("GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")

    # --- File Upload ---
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "data/uploads")
    ENABLE_RAG_LESS_CONTEXT: bool = os.getenv("ENABLE_RAG_LESS_CONTEXT", "true").lower() == "true"
    DEFAULT_CONTEXT_TOKEN_BUDGET: int = int(os.getenv("DEFAULT_CONTEXT_TOKEN_BUDGET", "8000"))
    MAX_CONTEXT_TOKEN_BUDGET: int = int(os.getenv("MAX_CONTEXT_TOKEN_BUDGET", "12000"))
    MAX_CONTEXT_CHUNKS: int = int(os.getenv("MAX_CONTEXT_CHUNKS", "12"))
    MIN_RELEVANCE_SCORE: float = float(os.getenv("MIN_RELEVANCE_SCORE", "0.10"))
    ENABLE_HYBRID_RERANK: bool = os.getenv("ENABLE_HYBRID_RERANK", "false").lower() == "true"
    HYBRID_RERANK_TOPN: int = int(os.getenv("HYBRID_RERANK_TOPN", "24"))
    HYBRID_RERANK_MODEL: str = os.getenv("HYBRID_RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
    HYBRID_RERANK_BLEND: float = float(os.getenv("HYBRID_RERANK_BLEND", "0.25"))

    # --- Semantic Retrieval ---
    ENABLE_SEMANTIC_RETRIEVAL: bool = os.getenv("ENABLE_SEMANTIC_RETRIEVAL", "true").lower() == "true"
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    RRF_K: int = int(os.getenv("RRF_K", "60"))  # Reciprocal Rank Fusion constant
    CHUNK_OVERLAP_CHARS: int = int(os.getenv("CHUNK_OVERLAP_CHARS", "200"))  # Overlap between consecutive chunks
    CLAUDE_API_KEY: str = os.getenv("CLAUDE_API_KEY", "")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-latest")

    # --- PageIndex Tree RAG ---
    ENABLE_PAGEINDEX_TREE: bool = os.getenv("ENABLE_PAGEINDEX_TREE", "true").lower() == "true"
    PAGEINDEX_MODEL: str = os.getenv("PAGEINDEX_MODEL", "groq/llama-3.3-70b-versatile")  # LiteLLM model for tree generation
    PAGEINDEX_RETRIEVE_MODEL: str = os.getenv("PAGEINDEX_RETRIEVE_MODEL", "groq/llama-3.3-70b-versatile")  # LLM for tree search
    PAGEINDEX_WORKSPACE: str = os.getenv("PAGEINDEX_WORKSPACE", "data/pageindex_workspace")  # Where tree JSONs are stored
    ENABLE_TREE_SEARCH: bool = os.getenv("ENABLE_TREE_SEARCH", "true").lower() == "true"  # Use tree search in retrieval

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


settings = Settings()
