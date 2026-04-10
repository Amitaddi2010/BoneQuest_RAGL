import sys
import os
import json
from datetime import datetime

# Add backend to sys.path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from database import SessionLocal
from models.db_models import DocumentTree, TreeNode

def setup_mock():
    print("--- Setting up Mock Document Tree for Verification ---")
    db = SessionLocal()
    
    try:
        # 1. Create Tree
        tree_structure = {
            "title": "Mock Orthopaedic Protocol 2025",
            "summary": "Covers emergency management of fractures and joint dislocations.",
            "chapters": [
                {
                    "title": "Chapter 1: Lower Limb",
                    "page": 1,
                    "sections": [
                        {"title": "Section 1.1: Femoral Neck", "id": "node_1", "page": 5}
                    ]
                }
            ]
        }
        
        tree = DocumentTree(
            doc_name="Mock Protocol",
            doc_type="guideline",
            tree_structure=tree_structure
        )
        db.add(tree)
        db.commit()
        db.refresh(tree)
        print(f"Created tree with ID: {tree.id}")
        
        # 2. Create Node
        node = TreeNode(
            tree_id=tree.id,
            node_id="node_1",
            title="Section 1.1: Femoral Neck",
            summary="Emergency protocols for displaced femoral neck fractures.",
            full_text="HEMIARTHROPLASTY PROTOCOL: For patients over 65 with displaced fractures, hemiarthroplasty is the preferred treatment to allow early mobilization.",
            page_start=5,
            page_end=10
        )
        db.add(node)
        db.commit()
        print(f"Created node for {tree.doc_name}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    setup_mock()
