# ============================================================
# BoneQuest v2 — Vectorless Indexing Service
# ============================================================

import pypdf
import pdfplumber
import json
import re
import asyncio
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from models.db_models import DocumentTree, TreeNode
from config import settings

class PDFHierarchyExtractor:
    """Extract structure + content from PDFs while preserving hierarchy"""
    
    def __init__(self):
        self.document_structure = []
        self.current_hierarchy = []
    
    async def extract_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract PDF maintaining document structure
        Return: {pages: [], structure: [], content: {}}
        """
        print(f"[Indexer] Extracting from {pdf_path}...")
        
        pages_content = []
        total_pages = 0
        
        # Use pdfplumber for text extraction and table detection
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                # Simplified table detection: just check if any tables exist
                has_tables = len(page.find_tables()) > 0
                
                pages_content.append({
                    "page_number": page_num + 1,
                    "text": page_text or "",
                    "has_tables": has_tables,
                    "has_images": len(page.images) > 0
                })
        
        # Detect structure (headings)
        hierarchy = self._detect_document_structure(pages_content)
        
        return {
            "pdf_path": pdf_path,
            "total_pages": total_pages,
            "pages": pages_content,
            "detected_hierarchy": hierarchy
        }
    
    def _detect_document_structure(self, pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detect headings, sections, subsections using patterns
        """
        structure = {
            "chapters": [],
            "sections": [],
            "subsections": []
        }
        
        current_chapter = None
        current_section = None
        
        for page in pages:
            text = page["text"]
            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Detect Chapter (ALL CAPS, short, but not just numbers)
                if len(line) < 80 and line.isupper() and len(line.split()) > 1 and not line.replace(".","").isdigit():
                    current_chapter = {
                        "title": line,
                        "page": page["page_number"],
                        "sections": []
                    }
                    structure["chapters"].append(current_chapter)
                    current_section = None # Reset section when new chapter starts
                
                # Detect Section (Number + Title, e.g., "1. Introduction")
                elif re.match(r'^\d+\.\s+[A-Z]', line) and len(line) < 100:
                    current_section = {
                        "title": line,
                        "page": page["page_number"],
                        "subsections": []
                    }
                    if current_chapter:
                        current_chapter["sections"].append(current_section)
                    else:
                        structure["sections"].append(current_section)
                
                # Detect Subsection (e.g., "1.1 Background")
                elif re.match(r'^\d+\.\d+\s+[A-Z]', line) and len(line) < 100:
                    subsection = {
                        "title": line,
                        "page": page["page_number"]
                    }
                    if current_section:
                        current_section["subsections"].append(subsection)
                    elif current_chapter:
                        # Sometimes headings go Chapter -> 1.1 directly
                        current_chapter["sections"].append({"title": line, "page": page["page_number"], "subsections": []})
                    else:
                        structure["subsections"].append(subsection)
        
        return structure


class HierarchicalTreeBuilder:
    """Build LLM-optimized hierarchical tree from extracted PDF"""
    
    def __init__(self, groq_client):
        self.groq = groq_client
        self.tree = None
    
    async def build_tree(self, pdf_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use Groq to build optimized tree structure
        """
        print("[Indexer] Building hierarchical tree using Groq reasoning...")
        
        doc_overview = self._create_document_overview(pdf_data)
        
        prompt = f"""
        Analyze this document structure and create a hierarchical tree index for a medical guideline.
        
        Document Overview:
        {doc_overview}
        
        Please create a logical hierarchical tree structure. 
        Ensure nodes have meaningful page ranges based on where chapters/sections start.
        
        Return as JSON with this format:
        {{
            "doc_name": "string",
            "total_pages": number,
            "tree": {{
                "node_id": "root",
                "title": "Document Title",
                "page_start": 1,
                "page_end": last_page,
                "summary": "Overall document purpose",
                "children": [
                    {{
                        "node_id": "1",
                        "title": "Chapter/Section Title",
                        "page_start": X,
                        "page_end": Y,
                        "summary": "What this section covers",
                        "children": []
                    }}
                ]
            }}
        }}
        """
        
        try:
            response = self.groq.chat.completions.create(
                model=settings.GROQ_SMALL_MODEL,  # Use faster model for structure
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            tree_content = response.choices[0].message.content
            self.tree = json.loads(tree_content)
            return self.tree
        except Exception as e:
            print(f"[Indexer] Tree building failed: {e}")
            # Fallback to simple tree if LLM fails
            return self._build_fallback_tree(pdf_data)
    
    def _create_document_overview(self, pdf_data: Dict[str, Any]) -> str:
        overview = f"Total Pages: {pdf_data['total_pages']}\n\nDetected Structure:\n"
        hierarchy = pdf_data.get('detected_hierarchy', {})
        
        for chapter in hierarchy.get('chapters', [])[:15]:
            overview += f"- CHAPTER: {chapter['title']} (Starts Page {chapter['page']})\n"
            for section in chapter.get('sections', [])[:5]:
                overview += f"  - Section: {section['title']} (Starts Page {section['page']})\n"
        
        return overview

    def _build_fallback_tree(self, pdf_data: Dict[str, Any]) -> Dict[str, Any]:
        """Basic tree structure if LLM fails"""
        return {
            "doc_name": "Document",
            "total_pages": pdf_data["total_pages"],
            "tree": {
                "node_id": "root",
                "title": "Document Root",
                "page_start": 1,
                "page_end": pdf_data["total_pages"],
                "summary": "Full document content",
                "children": []
            }
        }

    async def add_summaries_and_content(self, pdf_data: Dict[str, Any]):
        """
        Populate summaries and text for each node in the tree.
        """
        if not self.tree:
            return
            
        pages_map = {p["page_number"]: p["text"] for p in pdf_data["pages"]}
        
        async def process_node(node):
            page_start = node.get("page_start", 1)
            page_end = node.get("page_end", page_start)
            
            # Combine text from page range
            node_text = ""
            for p in range(page_start, page_end + 1):
                node_text += pages_map.get(p, "") + "\n"
            
            # Truncate content for summary generation if too large
            summary_input = node_text[:3000]
            
            if len(summary_input) > 100:
                prompt = f"Summarize this medical guideline section in 1-2 professional sentences:\n\nTitle: {node.get('title')}\nContent: {summary_input}"
                try:
                    # Non-blocking if possible, but Groq lib is usually sync for completions. 
                    # We'll use a small sleep or wrap in thread if needed for scale.
                    response = self.groq.chat.completions.create(
                        model=settings.GROQ_SMALL_MODEL,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=150,
                        temperature=0.3
                    )
                    node["summary"] = response.choices[0].message.content.strip()
                except Exception:
                    node["summary"] = node.get("summary") or "Section content summary unavailable."
            
            node["full_text"] = node_text
            
            # Process children recursively
            tasks = [process_node(child) for child in node.get("children", [])]
            if tasks:
                await asyncio.gather(*tasks)
        
        await process_node(self.tree["tree"])
        return self.tree


class TreeStorage:
    """Handles saving the tree structure and nodes to SQLite via SQLAlchemy"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def save_tree(self, tree_data: Dict[str, Any], doc_name: str) -> int:
        """Save top-level tree and all its nodes"""
        # 1. Create DocumentTree record
        db_tree = DocumentTree(
            doc_name=doc_name,
            total_pages=tree_data.get("total_pages"),
            tree_structure=tree_data.get("tree")
        )
        self.db.add(db_tree)
        self.db.commit()
        self.db.refresh(db_tree)
        
        # 2. Flatten and save nodes
        self._save_node_recursive(db_tree.id, tree_data["tree"], "root")
        self.db.commit()
        
        return db_tree.id
    
    def _save_node_recursive(self, tree_id: int, node_data: Dict[str, Any], parent_id: str):
        node_id = node_data.get("node_id", "unknown")
        
        db_node = TreeNode(
            tree_id=tree_id,
            node_id=node_id,
            parent_id=parent_id,
            title=node_data.get("title"),
            page_start=node_data.get("page_start"),
            page_end=node_data.get("page_end"),
            summary=node_data.get("summary"),
            full_text=node_data.get("full_text")
        )
        self.db.add(db_node)
        
        for child in node_data.get("children", []):
            self._save_node_recursive(tree_id, child, node_id)
