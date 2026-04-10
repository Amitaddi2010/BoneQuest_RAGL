# ============================================================
# BoneQuest v2 — PageIndex Tree RAG Service
# Self-hosted PageIndex integration for reasoning-based retrieval
# ============================================================

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from config import settings
from models.db_models import Document, DocumentChunk, DocumentTree, TreeNode

logger = logging.getLogger(__name__)

# ── Add PageIndex to Python path ─────────────────────────────
# PageIndex is cloned into backend/lib/PageIndex/ (no setup.py)
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_PAGEINDEX_LIB = _BACKEND_DIR / "lib" / "PageIndex"
if _PAGEINDEX_LIB.is_dir() and str(_PAGEINDEX_LIB) not in sys.path:
    sys.path.insert(0, str(_PAGEINDEX_LIB))

# ── PageIndex Workspace ──────────────────────────────────────

_WORKSPACE = Path(settings.PAGEINDEX_WORKSPACE)
_WORKSPACE.mkdir(parents=True, exist_ok=True)


def _extract_pdf_text_by_page(file_path: str) -> List[Dict]:
    """Extract text from each page of a PDF using PyPDF2."""
    try:
        import PyPDF2
        pages = []
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for i, page in enumerate(reader.pages, 1):
                text = page.extract_text() or ''
                pages.append({'page': i, 'content': text})
        return pages
    except Exception as e:
        logger.error(f"[PageIndexService] PDF extraction failed: {e}")
        return []


def _generate_tree_via_groq(doc_name: str, pages: List[Dict]) -> Optional[List]:
    """
    Generate a hierarchical tree structure using Groq LLM directly.
    
    Instead of the full PageIndex pipeline (which requires many LLM calls
    for TOC detection, title verification, etc.), we send a condensed
    version of the document to Groq and ask it to build the tree in one shot.
    This is faster, cheaper, and avoids the complex import chain.
    """
    from groq import Groq
    
    # Build condensed document text (first ~300 chars per page to stay within context)
    condensed = []
    for p in pages:
        snippet = p['content'][:300].replace('\n', ' ').strip()
        if snippet:
            condensed.append(f"[Page {p['page']}] {snippet}")
    
    # Limit to avoid Groq context overflow (~8K tokens)
    doc_text = "\n".join(condensed)
    if len(doc_text) > 25000:
        doc_text = doc_text[:25000] + "\n... (truncated)"
    
    prompt = f"""You are a document structure expert. Analyze this document and generate a hierarchical tree structure (table of contents with page ranges).

DOCUMENT: "{doc_name}"
PAGE PREVIEWS:
{doc_text}

INSTRUCTIONS:
- Return a JSON array of top-level sections
- Each section has: "title", "start_index" (start page), "end_index" (end page), "summary" (1-2 sentence description)
- Sections can have nested "nodes" array for subsections
- Cover ALL pages from 1 to {len(pages)}
- Use the actual section/chapter titles from the text
- Return ONLY the JSON array, no other text

RESPONSE:"""

    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        response = client.chat.completions.create(
            model=settings.GROQ_TEXT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=4000,
        )
        raw = response.choices[0].message.content.strip()
        
        # Parse JSON (handle markdown code blocks)
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        
        structure = json.loads(raw)
        if isinstance(structure, list):
            return structure
        elif isinstance(structure, dict) and 'structure' in structure:
            return structure['structure']
        return None
    except Exception as e:
        logger.error(f"[PageIndexService] Groq tree generation failed: {e}")
        return None


# ── Tree Generation ──────────────────────────────────────────

def generate_tree_for_document(
    db: Session,
    document_id: int,
    file_path: str,
) -> Optional[Dict]:
    """
    Generate a tree structure for a document using Groq LLM directly.
    
    Extracts text from the PDF page-by-page, sends a condensed version
    to Groq, and asks it to produce a hierarchical tree structure.
    
    Returns the tree structure dict or None on failure.
    """
    if not settings.ENABLE_PAGEINDEX_TREE:
        logger.info("[PageIndexService] Tree generation disabled")
        return None

    doc = db.query(Document).get(document_id)
    if not doc:
        logger.warning(f"[PageIndexService] Document {document_id} not found")
        return None

    # Check if tree already exists
    existing_tree = db.query(DocumentTree).filter(
        DocumentTree.doc_name == doc.name
    ).first()
    if existing_tree and existing_tree.tree_structure:
        logger.info(f"[PageIndexService] Tree already exists for '{doc.name}'")
        return existing_tree.tree_structure

    ext = Path(file_path).suffix.lower()
    if ext not in ('.pdf', '.md', '.markdown'):
        logger.info(f"[PageIndexService] Skipping tree generation for {ext} file")
        return None

    try:
        logger.info(f"[PageIndexService] Generating tree for '{doc.name}' via Groq...")

        # Step 1: Extract text from PDF
        pages = _extract_pdf_text_by_page(file_path)
        if not pages:
            logger.warning(f"[PageIndexService] No pages extracted from '{doc.name}'")
            return None

        # Step 2: Generate tree structure via Groq
        structure = _generate_tree_via_groq(doc.name, pages)
        if not structure:
            logger.warning(f"[PageIndexService] Groq returned no structure for '{doc.name}'")
            return None

        # Step 3: Add node IDs
        _assign_node_ids(structure)

        # Step 4: Store in DB
        db_tree = DocumentTree(
            doc_name=doc.name,
            doc_type=doc.doc_type or "general",
            total_pages=len(pages),
            tree_structure=structure,
        )
        db.add(db_tree)
        db.flush()

        # Store individual nodes for fast lookups
        _store_tree_nodes(db, db_tree.id, structure)

        db.commit()
        logger.info(
            f"[PageIndexService] ✓ Tree generated for '{doc.name}': "
            f"{_count_nodes(structure)} nodes, {len(pages)} pages"
        )

        return structure

    except Exception as e:
        logger.error(f"[PageIndexService] Tree generation failed for '{doc.name}': {e}")
        db.rollback()
        return None


def _assign_node_ids(nodes: list, counter: list = None):
    """Assign sequential node IDs to tree nodes."""
    if counter is None:
        counter = [0]
    if not isinstance(nodes, list):
        return
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node['node_id'] = str(counter[0]).zfill(4)
        counter[0] += 1
        if 'nodes' in node and node['nodes']:
            _assign_node_ids(node['nodes'], counter)


def _store_tree_nodes(
    db: Session, tree_id: int, nodes: list, parent_id: str = None
):
    """Recursively store tree nodes in the DB for fast lookups."""
    if not isinstance(nodes, list):
        return
    for node in nodes:
        if not isinstance(node, dict):
            continue
        db_node = TreeNode(
            tree_id=tree_id,
            node_id=node.get("node_id", ""),
            parent_id=parent_id or "",
            title=node.get("title", ""),
            page_start=node.get("start_index"),
            page_end=node.get("end_index"),
            summary=node.get("summary", ""),
            full_text=node.get("text", ""),
        )
        db.add(db_node)
        # Recurse into children
        children = node.get("nodes", [])
        if children:
            _store_tree_nodes(db, tree_id, children, node.get("node_id", ""))


def _count_nodes(nodes: list) -> int:
    """Count total nodes in a tree structure."""
    if not isinstance(nodes, list):
        return 0
    count = len(nodes)
    for node in nodes:
        if isinstance(node, dict):
            count += _count_nodes(node.get("nodes", []))
    return count


# ── Tree Search (Query-Time Retrieval) ───────────────────────

def tree_search(
    db: Session,
    query: str,
    document_id: Optional[str] = None,
    max_pages: int = 8,
) -> List[Tuple[int, float, str]]:
    """
    Perform reasoning-based tree search for a query.
    
    Uses the Groq LLM to reason over the tree structure and identify
    which page ranges are most relevant to the query. Returns a list
    of (chunk_index, relevance_score, page_text) tuples that can be
    fed into the RRF pipeline alongside BM25 and semantic results.
    
    Instead of calling the full PageIndex agent (which requires OpenAI 
    Agents SDK), we do a lightweight version: feed the tree structure
    + query to Groq and ask it to select the most relevant sections.
    """
    if not settings.ENABLE_TREE_SEARCH:
        return []

    # Find the tree for the specified document
    tree_data = _get_tree_for_document(db, document_id)
    if not tree_data:
        return []

    tree_structure = tree_data.get("structure")
    if not tree_structure:
        return []

    # Use Groq to reason over the tree and find relevant sections
    relevant_sections = _llm_tree_navigate(query, tree_structure)
    if not relevant_sections:
        return []

    # Map the identified pages/sections back to chunk indices
    return _map_sections_to_chunks(db, relevant_sections, document_id)


def _get_tree_for_document(
    db: Session, document_id: Optional[str]
) -> Optional[Dict]:
    """Get the tree structure for a document."""
    if not document_id or document_id in {"global", "all"}:
        # For global queries, return the first available tree
        tree = db.query(DocumentTree).first()
    else:
        # Find the document first
        doc = db.query(Document).filter(
            (Document.internal_id == document_id)
            | (Document.doc_id == document_id)
            | (Document.name == document_id)
        ).first()
        if not doc:
            return None
        tree = db.query(DocumentTree).filter(
            DocumentTree.doc_name == doc.name
        ).first()

    if not tree or not tree.tree_structure:
        return None

    return {
        "structure": tree.tree_structure,
        "doc_name": tree.doc_name,
        "total_pages": tree.total_pages,
        "tree_id": tree.id,
    }


def _llm_tree_navigate(
    query: str, tree_structure: list
) -> List[Dict]:
    """
    Use Groq LLM to reason over the tree structure and find relevant sections.
    
    Returns a list of dicts with: title, start_page, end_page, relevance
    """
    # Build a compact tree representation for the LLM
    tree_text = _format_tree_for_llm(tree_structure)

    prompt = f"""You are a document retrieval expert. Given a document's hierarchical structure and a query, identify the MOST RELEVANT sections.

DOCUMENT STRUCTURE:
{tree_text}

QUERY: {query}

INSTRUCTIONS:
- Return the 3-5 most relevant sections as a JSON array
- Each section should have: "title", "start_page", "end_page", "relevance" (0.0-1.0)
- Consider both direct keyword matches AND sections that would contextually answer the query
- Prefer leaf nodes (specific sections) over broad parent nodes
- Return ONLY the JSON array, no other text

RESPONSE:"""

    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
        response = client.chat.completions.create(
            model=settings.GROQ_SMALL_MODEL,  # Use fast model for tree navigation
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=500,
        )
        raw = response.choices[0].message.content.strip()

        # Parse JSON from response (handle markdown code blocks)
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        sections = json.loads(raw)
        if isinstance(sections, list):
            logger.info(
                f"[PageIndexService] Tree search found {len(sections)} relevant sections"
            )
            return sections
        return []
    except Exception as e:
        logger.warning(f"[PageIndexService] Tree navigation LLM call failed: {e}")
        return []


def _format_tree_for_llm(nodes: list, depth: int = 0) -> str:
    """Format tree structure as indented text for LLM consumption."""
    if not isinstance(nodes, list):
        return ""
    lines = []
    indent = "  " * depth
    for node in nodes:
        if not isinstance(node, dict):
            continue
        title = node.get("title", "Untitled")
        pages = ""
        if node.get("start_index") and node.get("end_index"):
            pages = f" [pages {node['start_index']}-{node['end_index']}]"
        summary = ""
        if node.get("summary"):
            summary = f" — {node['summary'][:120]}"
        lines.append(f"{indent}• {title}{pages}{summary}")
        children = node.get("nodes", [])
        if children:
            lines.append(_format_tree_for_llm(children, depth + 1))
    return "\n".join(lines)


def _map_sections_to_chunks(
    db: Session,
    sections: List[Dict],
    document_id: Optional[str],
) -> List[Tuple[int, float, str]]:
    """
    Map LLM-selected sections (page ranges) back to chunk indices.
    
    Returns list of (chunk_index, score, section_title) tuples.
    """
    results = []

    # Find the document
    doc_query = db.query(Document).filter(Document.status == "indexed")
    if document_id and document_id not in {"global", "all"}:
        doc_query = doc_query.filter(
            (Document.internal_id == document_id)
            | (Document.doc_id == document_id)
            | (Document.name == document_id)
        )
    docs = doc_query.all()
    if not docs:
        return results

    doc_ids = [d.id for d in docs]

    # Get all chunks for these documents
    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id.in_(doc_ids))
        .order_by(DocumentChunk.document_id.asc(), DocumentChunk.chunk_index.asc())
        .all()
    )
    if not chunks:
        return results

    for section in sections:
        if not isinstance(section, dict):
            continue
        start_page = section.get("start_page", 0)
        end_page = section.get("end_page", 0)
        relevance = float(section.get("relevance", 0.5))
        title = section.get("title", "")

        if not start_page or not end_page:
            continue

        # Find chunks that overlap with this page range
        for i, chunk in enumerate(chunks):
            chunk_page = _parse_chunk_page(chunk.page_label)
            if chunk_page is not None and start_page <= chunk_page <= end_page:
                results.append((i, relevance, title))

    # Deduplicate by chunk index, keeping highest score
    seen = {}
    for idx, score, title in results:
        if idx not in seen or score > seen[idx][0]:
            seen[idx] = (score, title)

    return [(idx, score, title) for idx, (score, title) in seen.items()]


def _parse_chunk_page(page_label: Optional[str]) -> Optional[int]:
    """Extract page number from chunk page_label like 'Page 5'."""
    if not page_label:
        return None
    m = re.search(r"(\d+)", str(page_label))
    if m:
        return int(m.group(1))
    return None


# ── Utility ──────────────────────────────────────────────────

def has_tree(db: Session, document_name: str) -> bool:
    """Check if a tree exists for a document."""
    tree = db.query(DocumentTree).filter(
        DocumentTree.doc_name == document_name
    ).first()
    return tree is not None and tree.tree_structure is not None
