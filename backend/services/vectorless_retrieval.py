# ============================================================
# BoneQuest v2 — Vectorless Retrieval Service
# ============================================================

import json
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from models.db_models import DocumentTree, TreeNode
from config import settings

class LibraryRouter:
    """Selects the best documents from the library using metadata reasoning"""
    
    def __init__(self, db: Session, groq_client):
        self.db = db
        self.groq = groq_client
        
    async def select_relevant_documents(self, query: str, limit: int = 2) -> List[Dict[str, Any]]:
        """Identify which document trees are likely to contain the answer"""
        
        # 1. Fetch available document trees and their types
        trees = self.db.query(DocumentTree).all()
        if not trees:
            return []
            
        library_metadata = []
        for t in trees:
            library_metadata.append({
                "id": t.id,
                "name": t.doc_name,
                "type": t.doc_type,
                "root_summary": t.tree_structure.get("summary", "No summary available")
            })
            
        prompt = f"""
        You are a clinical librarian. Your task is to select the TOP {limit} most relevant clinical documents from the library to answer a query.
        
        Query: {query}
        
        Available Library:
        {json.dumps(library_metadata, indent=2)}
        
        Instructions:
        1. Select up to {limit} document IDs that are most likely to contain the evidence.
        2. Priority: 'guideline' type is usually better for direct protocols; 'general' for background.
        3. Respond in JSON with "selected_ids" list.
        
        Example: {{"thinking": "...", "selected_ids": [1, 5]}}
        """
        
        try:
            response = self.groq.chat.completions.create(
                model=settings.GROQ_SMALL_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            selected_ids = result.get("selected_ids", [])
            
            # Return full metadata for the selected IDs
            return [t for t in library_metadata if t["id"] in selected_ids]
        except Exception as e:
            print(f"[Librarian] Routing failed: {e}")
            return library_metadata[:1] # Fallback to first doc

class VectorlessTreeSearch:
    """LLM-based retrieval over hierarchical tree (no vectors!)"""
    
    def __init__(self, db: Session, groq_client):
        self.db = db
        self.groq = groq_client
        self.router = LibraryRouter(db, groq_client)
    
    async def search(
        self,
        query: str,
        document_id: Optional[int] = None,
        num_hops: int = 3,
        user_role: str = "resident"
    ) -> Dict[str, Any]:
        """
        Search tree using LLM reasoning. 
        If document_id is None, it uses the LibraryRouter to find documents automatically.
        """
        target_docs = []
        selection_reasoning = ""
        
        # 1. Automated Document Discovery (Global Search)
        if document_id is None:
            print(f"[Retrieval] Global Librarian search for: {query}")
            discovery = await self.router.select_relevant_documents(query)
            target_docs = discovery
            selection_reasoning = f"Librarian selected {len(target_docs)} relevant sources."
        else:
            # Single document mode
            tree = self.db.query(DocumentTree).filter(DocumentTree.id == document_id).first()
            if tree:
                target_docs = [{"id": tree.id, "name": tree.doc_name}]
            else:
                return {"error": "Document tree not found", "content": []}

        # 2. Perform hierarchical search across all selected documents
        all_retrieved_content = []
        all_node_ids = []
        
        for doc_meta in target_docs:
            doc_id = doc_meta["id"]
            
            # Fetch the tree structure
            tree_meta = self.db.query(DocumentTree).filter(DocumentTree.id == doc_id).first()
            if not tree_meta: continue
                
            tree_structure = tree_meta.tree_structure
            
            # Find relevant nodes for this specific tree
            relevant_node_ids = await self._find_relevant_nodes(
                query=query,
                tree=tree_structure,
                user_role=user_role
            )
            all_node_ids.extend([f"{doc_meta['name']}: {nid}" for nid in relevant_node_ids])
            
            # Retrieve content
            for node_id in relevant_node_ids:
                node = self.db.query(TreeNode).filter(
                    TreeNode.tree_id == doc_id, 
                    TreeNode.node_id == node_id
                ).first()
                if node:
                    all_retrieved_content.append({
                        "node_id": node.node_id,
                        "doc_name": doc_meta["name"],
                        "title": node.title,
                        "page_range": f"{node.page_start}-{node.page_end}",
                        "summary": node.summary,
                        "content": node.full_text
                    })

        # 3. Multi-hop across all (simplified to scanning combined content)
        # (Same logic as before but using combined list)
        final_content = all_retrieved_content.copy()
        for hop in range(1, num_hops):
            referenced_ids = self._find_referenced_node_ids(final_content)
            # Fetch globally referenced nodes (simplified to current docs for now)
            # In future, Librarian could be re-invoked for new references
            
        return {
            "query": query,
            "retrieved_nodes": len(final_content),
            "content": final_content,
            "reasoning_trace": all_node_ids,
            "selection_reasoning": selection_reasoning
        }
    
    async def _find_relevant_nodes(self, query: str, tree: Dict[str, Any], user_role: str) -> List[str]:
        """Use Groq to select node IDs from the tree summary"""
        
        tree_summary = self._create_tree_summary(tree)
        
        prompt = f"""
        You are a medical guidelines navigator for a {user_role}.
        Query: {query}
        
        Below is the hierarchical structure of a medical guideline document.
        Identify the identifiers (node_ids) of the sections most likely to contain the answer.
        
        Document Tree Structure:
        {tree_summary}
        
        Instructions:
        1. List EXACT node_ids that are relevant.
        2. Higher-level nodes are good for context; specific leaf nodes are good for detail.
        3. Respond in JSON format only.
        
        Example Response:
        {{
            "thinking": "The user is asking about fracture classification, so the 'Classification' and 'Initial Assessment' sections are relevant.",
            "relevant_node_ids": ["1.2", "2.1.1"],
            "confidence": 0.9
        }}
        """
        
        try:
            response = self.groq.chat.completions.create(
                model=settings.GROQ_SMALL_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            return result.get("relevant_node_ids", [])
        except Exception as e:
            print(f"[Retrieval] Node selection failed: {e}")
            return []
            
    def _create_tree_summary(self, tree: Dict[str, Any], max_depth: int = 3) -> str:
        """Create a readable text summary of the tree for the LLM"""
        def format_node(node, depth=0):
            if depth > max_depth:
                return ""
            indent = "  " * depth
            summary = f"{indent}- [{node.get('node_id')}] {node.get('title')} (Pages {node.get('page_start')}-{node.get('page_end')})\n"
            for child in node.get("children", []):
                summary += format_node(child, depth + 1)
            return summary
            
        return format_node(tree)
        
    def _find_referenced_node_ids(self, content_list: List[Dict[str, Any]]) -> List[str]:
        """Extract potential node_ids from text references"""
        referenced = []
        patterns = [
            r'see (?:also )?(?:section|chapter|table)[\s:]*([\d\w\.]+)',
            r'refer to[\s:]*([\d\w\.]+)',
            r'Section\s+([\d\w\.]+)'
        ]
        
        for item in content_list:
            text_to_scan = item.get("content", "")
            for pattern in patterns:
                matches = re.findall(pattern, text_to_scan, re.IGNORECASE)
                for m in matches:
                    m = m.strip(".")
                    if m and m not in referenced:
                        referenced.append(m)
        return referenced
