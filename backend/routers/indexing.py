# ============================================================
# BoneQuest v2 — Hierarchical Indexing Router
# ============================================================

import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any

from database import get_db
from models.db_models import Document, User, DocumentTree
from models.schemas import DocumentStatus
from auth.permissions import require_admin
from services.vectorless_index import PDFHierarchyExtractor, HierarchicalTreeBuilder, TreeStorage
import services.pageindex_engine as engine_module

router = APIRouter()

# Anchor upload dir to backend package directory
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_UPLOAD_DIR = _BACKEND_DIR / "data" / "uploads"

async def run_indexing_task(doc_id: int, internal_id: str, doc_name: str, db: Session):
    """Background task to build hierarchical tree"""
    try:
        # 1. Initialize services
        # We need a fresh Groq client from the engine
        engine = engine_module.PageIndexEngine()
        groq_client = engine.groq_client
        
        extractor = PDFHierarchyExtractor()
        builder = HierarchicalTreeBuilder(groq_client)
        
        pdf_path = str(_UPLOAD_DIR / f"{internal_id}.pdf")
        if not os.path.exists(pdf_path):
            print(f"[Indexer Task] File not found: {pdf_path}")
            return
            
        # 2. Extract and Build
        pdf_data = await extractor.extract_from_pdf(pdf_path)
        tree_json = await builder.build_tree(pdf_data)
        
        # 3. Summarize (this takes time)
        await builder.add_summaries_and_content(pdf_data)
        
        # 4. Save to DB
        storage = TreeStorage(db)
        tree_id = storage.save_tree(builder.tree, doc_name)
        
        # 5. Update Document status
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc:
            doc.status = "indexed"
            db.commit()
            
        print(f"[Indexer Task] Successfully indexed tree for {doc_name} (Tree ID: {tree_id})")
        
    except Exception as e:
        print(f"[Indexer Task] Failed for {doc_name}: {e}")
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc:
            doc.status = "error"
            db.commit()

@router.post("/{doc_id}/build-tree")
async def build_document_tree(
    doc_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Manually trigger hierarchical tree building for a document.
    Admin only.
    """
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # Check if tree already exists
    existing_tree = db.query(DocumentTree).filter(DocumentTree.doc_name == doc.name).first()
    if existing_tree:
        return {"message": "Tree already exists for this document", "tree_id": existing_tree.id}
        
    # Update status to processing
    doc.status = "processing"
    db.commit()
    
    # Run heavy processing in background
    background_tasks.add_task(
        run_indexing_task, 
        doc.id, 
        doc.internal_id or doc.doc_id, 
        doc.name, 
        db
    )
    
    return {"message": "Hierarchical indexing started in background", "doc_id": doc_id}

@router.get("/{doc_id}/status")
async def get_indexing_status(
    doc_id: int,
    db: Session = Depends(get_db)
):
    """Check if a hierarchical tree exists for a document"""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    tree = db.query(DocumentTree).filter(DocumentTree.doc_name == doc.name).first()
    
    return {
        "doc_id": doc_id,
        "status": doc.status,
        "has_hierarchical_tree": tree is not None,
        "tree_id": tree.id if tree else None
    }
