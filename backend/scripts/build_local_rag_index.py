import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.local_retriever import LocalRetriever


def main() -> None:
    p = argparse.ArgumentParser(description="Build local RAG disk index for a PDF.")
    p.add_argument("document_id", help="Local document internal_id")
    p.add_argument("--uploads-dir", default=str(BACKEND_DIR / "data" / "uploads"))
    args = p.parse_args()

    r = LocalRetriever(uploads_dir=args.uploads_dir)
    if not r.has_local_doc(args.document_id):
        raise SystemExit(f"PDF not found for document_id={args.document_id} in {args.uploads_dir}")

    # Trigger full build + persist to disk cache
    chunks = r._build_chunks(args.document_id)
    bm25 = r._build_bm25(args.document_id, chunks)
    print(f"Indexed document_id={args.document_id}")
    print(f"Chunks: {len(chunks)}")
    print(f"BM25 docs: {len(bm25.get('tokenized_docs', []))}")


if __name__ == "__main__":
    main()

