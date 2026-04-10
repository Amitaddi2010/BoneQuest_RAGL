
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))
from database import SessionLocal
from models.db_models import DocumentTree, TreeNode

db = SessionLocal()
try:
    trees = db.query(DocumentTree).all()
    for t in trees:
        print(f"TREE: ID {t.id}, {t.doc_name}")
        nodes = db.query(TreeNode).filter(TreeNode.tree_id == t.id).all()
        print(f"  Nodes: {len(nodes)}")
        for n in nodes[:5]: # Show first 5
            print(f"    - [{n.node_id}] {n.title}")
finally:
    db.close()
