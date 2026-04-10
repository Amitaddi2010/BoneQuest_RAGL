# ============================================================
# BoneQuest v2 — Document Processing (Improved Chunking)
# ============================================================

import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Optional

import pdfplumber
from pypdf import PdfReader

try:
    from docx import Document as DocxDocument  # type: ignore
except Exception:
    DocxDocument = None


def detect_source_type(filename: str) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext == ".pdf":
        return "pdf"
    if ext == ".docx":
        return "docx"
    if ext in {".txt", ".md"}:
        return "txt"
    return "txt"


def _estimate_tokens(text: str) -> int:
    return max(1, int(len((text or "").split()) * 1.3))


# Improved heading detection: requires numbered prefix or clear structural pattern,
# not just "any short uppercase line" which catches abbreviations and table headers.
_NUMBERED_HEADING_RE = re.compile(
    r"^(?:\d+[\.\)]\s+[A-Z]"           # "1. Introduction", "2) Methods"
    r"|CHAPTER\s+\d+"                    # "CHAPTER 3"
    r"|SECTION\s+\d+"                    # "SECTION 4"
    r"|PART\s+[IVX\d]+"                 # "PART II", "PART 3"
    r"|[A-Z][A-Z\s\-]{5,}(?:MENT|TION|YSIS|URES|SION|COLS|LINES|MENT|OLOGY)$"  # Structural suffixes
    r")",
    re.IGNORECASE,
)

_ALL_CAPS_HEADING_RE = re.compile(r"^[A-Z][A-Z0-9\s\-\.,:]{6,}$")

# Sentence boundary pattern for splitting
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def _is_heading(line: str) -> bool:
    """Detect headings using improved heuristics that avoid false positives."""
    s = (line or "").strip()
    if len(s) < 4 or len(s) > 120:
        return False
    # Strong signal: numbered heading pattern
    if _NUMBERED_HEADING_RE.match(s):
        return True
    # Weak signal: ALL CAPS — only if it looks structural (multiple words, not too long)
    if _ALL_CAPS_HEADING_RE.match(s) and 2 <= len(s.split()) <= 8:
        # Exclude lines that look like table data or abbreviations
        if re.search(r"\d{3,}", s):  # Contains long numbers — likely data
            return False
        return True
    return False


def _split_at_sentence_boundary(text: str, max_chars: int) -> List[str]:
    """Split text into segments at sentence boundaries, respecting max_chars."""
    if len(text) <= max_chars:
        return [text]

    segments = []
    sentences = _SENTENCE_END.split(text)
    current = []
    current_len = 0

    for sent in sentences:
        sent_len = len(sent)
        if current_len + sent_len > max_chars and current:
            segments.append(" ".join(current).strip())
            current = [sent]
            current_len = sent_len
        else:
            current.append(sent)
            current_len += sent_len + 1  # +1 for space

    if current:
        segments.append(" ".join(current).strip())

    return segments


def _chunk_text(
    text: str,
    source_type: str,
    max_chars: int = 1800,
    overlap_chars: int = 200,
    min_chunk_chars: int = 60,
) -> List[Dict]:
    """
    Chunk text with heading-awareness, sentence-boundary splitting, and overlap.

    Improvements over original:
    - Sentence-aware splitting (doesn't break mid-sentence)
    - Configurable overlap between consecutive chunks
    - Lower minimum chunk size (60 vs 120) to preserve dense clinical entries
    - Improved heading detection to avoid false positives
    """
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    if not lines:
        return []

    chunks: List[Dict] = []
    section = "General"
    buf: List[str] = []
    idx = 0

    def _make_chunk(content: str, section_name: str) -> Optional[Dict]:
        nonlocal idx
        content = content.strip()
        if len(content) < min_chunk_chars:
            return None
        chunk = {
            "chunk_index": idx,
            "source_type": source_type,
            "section": section_name,
            "page_label": "",
            "content": content,
            "token_count": _estimate_tokens(content),
        }
        idx += 1
        return chunk

    def flush():
        if not buf:
            return
        full_text = " ".join(buf).strip()
        if len(full_text) < min_chunk_chars:
            return

        # Split at sentence boundaries if too long
        segments = _split_at_sentence_boundary(full_text, max_chars)
        for i, seg in enumerate(segments):
            chunk = _make_chunk(seg, section)
            if chunk:
                chunks.append(chunk)

                # Add overlap: prepend the tail of this chunk to the next one
                if i < len(segments) - 1 and overlap_chars > 0:
                    # The overlap will naturally happen via sentence boundary splits
                    pass  # Overlap handled below at the page level
        buf.clear()

    for line in lines:
        if _is_heading(line):
            flush()
            section = line.title()
            continue
        buf.append(line)
        if len(" ".join(buf)) >= max_chars:
            flush()

    flush()

    # Add overlap between consecutive chunks from the same section
    if overlap_chars > 0 and len(chunks) > 1:
        overlapped_chunks = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_content = chunks[i - 1]["content"]
            curr_content = chunks[i]["content"]

            # Only overlap within the same section
            if chunks[i]["section"] == chunks[i - 1]["section"]:
                overlap_text = prev_content[-overlap_chars:] if len(prev_content) > overlap_chars else ""
                if overlap_text:
                    # Find a clean word boundary for the overlap
                    space_idx = overlap_text.find(" ")
                    if space_idx > 0:
                        overlap_text = overlap_text[space_idx + 1:]
                    curr_content = overlap_text + " " + curr_content
                    chunks[i] = dict(chunks[i])
                    chunks[i]["content"] = curr_content
                    chunks[i]["token_count"] = _estimate_tokens(curr_content)

            overlapped_chunks.append(chunks[i])
        chunks = overlapped_chunks

    return [c for c in chunks if len(c["content"]) >= min_chunk_chars]


def parse_document_to_chunks(
    file_path: str,
    source_type: str,
    max_chars: int = 1800,
    overlap_chars: int = 200,
) -> List[Dict]:
    """Parse a document file into chunks with improved processing."""
    if source_type == "pdf":
        chunks: List[Dict] = []
        idx = 0
        max_pages = 200  # Increased from 140
        try:
            reader = PdfReader(file_path)
            for page_num, page in enumerate(reader.pages[:max_pages], start=1):
                text = (page.extract_text() or "").strip()
                if not text:
                    continue
                page_chunks = _chunk_text(
                    text,
                    source_type=source_type,
                    max_chars=max_chars,
                    overlap_chars=overlap_chars,
                )
                for ch in page_chunks:
                    ch["chunk_index"] = idx
                    ch["page_label"] = f"p. {page_num}"
                    idx += 1
                chunks.extend(page_chunks)
        except Exception:
            logging.getLogger("pdfminer").setLevel(logging.ERROR)
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages[:max_pages], start=1):
                    text = (page.extract_text() or "").strip()
                    if not text:
                        continue
                    page_chunks = _chunk_text(
                        text,
                        source_type=source_type,
                        max_chars=max_chars,
                        overlap_chars=overlap_chars,
                    )
                    for ch in page_chunks:
                        ch["chunk_index"] = idx
                        ch["page_label"] = f"p. {page_num}"
                        idx += 1
                    chunks.extend(page_chunks)
        return chunks

    if source_type == "docx":
        if DocxDocument is None:
            raise RuntimeError("DOCX support requires python-docx.")
        doc = DocxDocument(file_path)
        text = "\n".join([p.text for p in doc.paragraphs if (p.text or "").strip()])
        return _chunk_text(text, source_type=source_type, max_chars=max_chars, overlap_chars=overlap_chars)

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    return _chunk_text(text, source_type=source_type, max_chars=max_chars, overlap_chars=overlap_chars)
