import argparse
import shutil
import uuid
from pathlib import Path
import sys

from sqlalchemy.orm import Session

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import SessionLocal, ensure_sqlite_migrations
from models.db_models import Document


def import_folder(folder_path: str, doc_type: str = "general", recursive: bool = True) -> dict:
    src_dir = Path(folder_path).expanduser()
    if not src_dir.exists() or not src_dir.is_dir():
        raise SystemExit(f"Folder not found: {folder_path}")

    backend_dir = Path(__file__).resolve().parents[1]
    upload_dir = backend_dir / "data" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    pattern = "**/*.pdf" if recursive else "*.pdf"
    pdfs = sorted(src_dir.glob(pattern))
    if not pdfs:
        raise SystemExit(f"No PDFs found in: {folder_path}")

    ensure_sqlite_migrations()
    db: Session = SessionLocal()
    results = []
    try:
        for pdf_path in pdfs:
            internal_id = uuid.uuid4().hex[:8]
            dest_path = upload_dir / f"{internal_id}.pdf"
            title = pdf_path.stem.replace("_", " ").replace("-", " ").strip().title()

            shutil.copyfile(str(pdf_path), str(dest_path))
            row = Document(
                doc_id=internal_id,
                internal_id=internal_id,
                name=title or internal_id,
                status="indexed",
                doc_type=doc_type if doc_type in ("general", "guideline") else "general",
            )
            db.add(row)
            results.append({"internal_id": internal_id, "file": pdf_path.name, "title": title})

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return {"total_found": len(pdfs), "imported": len(results), "results": results}


def main() -> None:
    p = argparse.ArgumentParser(description="Import local PDFs into BoneQuest local RAG store.")
    p.add_argument("folder_path", help="Folder containing PDFs")
    p.add_argument("--doc-type", default="general", choices=["general", "guideline"])
    p.add_argument("--no-recursive", action="store_true", help="Do not scan subfolders")
    args = p.parse_args()

    payload = import_folder(args.folder_path, doc_type=args.doc_type, recursive=not args.no_recursive)
    # Print only summary + first few IDs (copy-paste friendly)
    print(f"Found PDFs: {payload['total_found']}")
    print(f"Imported:   {payload['imported']}")
    print("Sample IDs:")
    for r in payload["results"][:10]:
        print(f"- {r['internal_id']}  {r['file']}")


if __name__ == "__main__":
    main()

