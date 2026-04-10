
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))
from database import SessionLocal
from models.db_models import DocumentTree

db = SessionLocal()
try:
    trees = db.query(DocumentTree).all()
    print(f"Total Document Trees: {len(trees)}")
    for t in trees:
        print(f"ID: {t.id}, Name: {t.doc_name}, Type: {t.doc_type}")
finally:
    db.close()
