"""
Generate PageIndex trees for all existing indexed documents.
Run once: python generate_trees.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal
from models.db_models import Document, DocumentTree
from config import settings

def main():
    db = SessionLocal()
    try:
        # Get all indexed documents
        docs = db.query(Document).filter(Document.status == "indexed").all()
        print(f"Found {len(docs)} indexed documents")
        
        # Check which already have trees
        existing_trees = {t.doc_name for t in db.query(DocumentTree).all()}
        print(f"Existing trees: {len(existing_trees)}")
        
        upload_dir = settings.UPLOAD_DIR
        
        for i, doc in enumerate(docs):
            if doc.name in existing_trees:
                print(f"  [{i+1}/{len(docs)}] ⏭ '{doc.name}' — tree exists, skipping")
                continue
            
            # Find the PDF file
            internal_id = doc.internal_id or doc.doc_id
            pdf_path = None
            for ext in ['.pdf', '.docx', '.txt']:
                candidate = os.path.join(upload_dir, f"{internal_id}{ext}")
                if os.path.isfile(candidate):
                    pdf_path = candidate
                    break
            
            if not pdf_path:
                print(f"  [{i+1}/{len(docs)}] ✗ '{doc.name}' — file not found ({internal_id})")
                continue
            
            if not pdf_path.lower().endswith('.pdf'):
                print(f"  [{i+1}/{len(docs)}] ⏭ '{doc.name}' — not a PDF, skipping")
                continue
            
            print(f"  [{i+1}/{len(docs)}] 🌳 '{doc.name}' — generating tree...", flush=True)
            try:
                from services.pageindex_service import generate_tree_for_document
                result = generate_tree_for_document(db, doc.id, pdf_path)
                if result:
                    print(f"           ✓ Tree generated!")
                else:
                    print(f"           ✗ Tree generation returned None")
            except Exception as e:
                print(f"           ✗ Error: {e}")
                # Continue with next doc
                continue
    finally:
        db.close()

if __name__ == "__main__":
    main()
