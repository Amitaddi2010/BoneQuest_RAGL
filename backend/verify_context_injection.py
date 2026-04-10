from database import SessionLocal
from services.context_injection import ContextInjectionService


def main() -> None:
    db = SessionLocal()
    try:
        service = ContextInjectionService()
        pkg = service.build_context_package(
            db=db,
            query="tibial shaft fracture management in diabetic patient",
            document_id="global",
            token_budget=3000,
            max_chunks=6,
        )
        print("retrieval:", pkg.get("retrieval", {}))
        print("citations:", len(pkg.get("citations", [])))
        print("context_chars:", len(pkg.get("context", "")))
    finally:
        db.close()


if __name__ == "__main__":
    main()
