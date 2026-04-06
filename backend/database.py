from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

from config import settings


def _resolve_database_url() -> str:
    """
    Anchor SQLite files to this package directory so the DB path does not depend
    on the process working directory (avoids empty/wrong DB when cwd differs).
    """
    url = settings.DATABASE_URL.strip()
    if not url.startswith("sqlite:///"):
        return url
    rest = url[len("sqlite:///") :]
    p = Path(rest)
    if not p.is_absolute():
        p = (Path(__file__).resolve().parent / p).resolve()
    return f"sqlite:///{p.as_posix()}"


SQLALCHEMY_DATABASE_URL = _resolve_database_url()

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def _sqlite_table_columns(conn, table: str) -> set:
    rows = conn.execute(text(f'PRAGMA table_info("{table}")')).fetchall()
    return {row[1] for row in rows}


def ensure_sqlite_migrations() -> None:
    """Best-effort column adds for older SQLite files (avoids 500s on new code)."""
    if not str(engine.url).startswith("sqlite"):
        return
    migrations = [
        ("chat_sessions", "is_deleted", "INTEGER DEFAULT 0"),
        ("chat_sessions", "deleted_at", "DATETIME"),
        ("chat_sessions", "context", "TEXT"),
        ("chat_messages", "user_feedback", "INTEGER DEFAULT 0"),
        ("chat_messages", "metadata_extra", "TEXT"),
        ("chat_messages", "reasoning_trace", "TEXT"),
        ("chat_messages", "citations", "TEXT"),
    ]
    with engine.begin() as conn:
        for table, col, ddl in migrations:
            try:
                cols = _sqlite_table_columns(conn, table)
                if col in cols:
                    continue
                conn.execute(text(f'ALTER TABLE "{table}" ADD COLUMN {col} {ddl}'))
            except Exception:
                continue


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
