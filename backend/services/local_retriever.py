import math
import os
import re
import json
import gzip
import pickle
import logging
from collections import Counter
from typing import Dict, List, Tuple

import pdfplumber

try:
    from PyPDF2 import PdfReader  # type: ignore
except Exception:
    PdfReader = None


_STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "are", "was", "were", "have",
    "has", "had", "not", "all", "any", "into", "than", "then", "them", "they", "their",
    "would", "could", "should", "about", "between", "after", "before", "which", "when",
    "what", "where", "how", "why", "your", "you", "our", "can", "may", "might", "will",
}

_HEADING_RE = re.compile(r"^([A-Z][A-Z0-9\-\s\(\)\.:,]{6,})$")


class LocalRetriever:
    """
    Local free retriever with:
    - Heading-aware chunking
    - BM25 lexical retrieval
    - Optional embedding rerank (if sentence-transformers exists)
    """

    def __init__(self, uploads_dir: str = "data/uploads", max_pages: int = 0):
        self.uploads_dir = uploads_dir
        self.max_pages = int(max_pages or 0)
        self._chunk_cache: Dict[str, List[dict]] = {}
        self._bm25_cache: Dict[str, dict] = {}
        self._embedder = None
        self._index_dir = os.path.join(os.path.dirname(self.uploads_dir), "index")
        os.makedirs(self._index_dir, exist_ok=True)

    def _pdf_path(self, document_id: str) -> str:
        return os.path.join(self.uploads_dir, f"{document_id}.pdf")

    def _index_path(self, document_id: str) -> str:
        return os.path.join(self._index_dir, f"{document_id}.pkl.gz")

    def _try_load_index(self, document_id: str) -> bool:
        """
        Load cached chunks and BM25 structures from disk if present.
        Returns True when loaded.
        """
        p = self._index_path(document_id)
        if not os.path.exists(p):
            return False
        try:
            with gzip.open(p, "rb") as f:
                payload = pickle.load(f)
            chunks = payload.get("chunks") or []
            bm25 = payload.get("bm25") or {}
            if chunks:
                self._chunk_cache[document_id] = chunks
            if bm25:
                self._bm25_cache[document_id] = bm25
            return bool(chunks)
        except Exception:
            return False

    def _save_index(self, document_id: str, chunks: List[dict], bm25: dict) -> None:
        p = self._index_path(document_id)
        try:
            with gzip.open(p, "wb") as f:
                pickle.dump({"chunks": chunks, "bm25": bm25}, f, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception:
            return

    def has_local_doc(self, document_id: str) -> bool:
        return os.path.exists(self._pdf_path(document_id))

    def _tokenize(self, text: str) -> List[str]:
        toks = re.findall(r"[a-zA-Z][a-zA-Z0-9\-]{2,}", (text or "").lower())
        return [t for t in toks if t not in _STOPWORDS]

    def _is_heading(self, line: str) -> bool:
        s = (line or "").strip()
        if len(s) < 6 or len(s) > 120:
            return False
        return bool(_HEADING_RE.match(s))

    def _chunk_page(self, page_num: int, text: str) -> List[dict]:
        lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
        if not lines:
            return []

        chunks: List[dict] = []
        current_heading = f"Page {page_num}"
        buffer: List[str] = []

        def flush():
            if not buffer:
                return
            content = " ".join(buffer).strip()
            if len(content) < 80:
                return
            chunks.append(
                {
                    "page_num": page_num,
                    "heading": current_heading,
                    "text": content,
                }
            )
            buffer.clear()

        for line in lines:
            if self._is_heading(line):
                flush()
                current_heading = line.title()
                continue
            buffer.append(line)
            # soft chunk length limit
            if len(" ".join(buffer)) > 1500:
                flush()

        flush()
        return chunks

    def _build_chunks(self, document_id: str) -> List[dict]:
        if document_id in self._chunk_cache:
            return self._chunk_cache[document_id]
        # Fast path: disk cache
        if self._try_load_index(document_id):
            return self._chunk_cache.get(document_id, [])

        path = self._pdf_path(document_id)
        chunks: List[dict] = []
        if not os.path.exists(path):
            self._chunk_cache[document_id] = chunks
            return chunks

        # Prefer PyPDF2 for speed; fall back to pdfplumber/pdfminer.
        if PdfReader is not None:
            try:
                reader = PdfReader(path)
                for idx, page in enumerate(reader.pages, start=1):
                    if self.max_pages and idx > self.max_pages:
                        break
                    raw = page.extract_text() or ""
                    raw = raw.strip()
                    if not raw:
                        continue
                    page_chunks = self._chunk_page(idx, raw)
                    chunks.extend(page_chunks)
            except Exception:
                chunks = []

        if not chunks:
            # Silence extremely noisy pdfminer warnings for some PDFs
            logging.getLogger("pdfminer").setLevel(logging.ERROR)
            with pdfplumber.open(path) as pdf:
                for idx, page in enumerate(pdf.pages, start=1):
                    if self.max_pages and idx > self.max_pages:
                        break
                    raw = page.extract_text() or ""
                    raw = raw.strip()
                    if not raw:
                        continue
                    page_chunks = self._chunk_page(idx, raw)
                    chunks.extend(page_chunks)

        self._chunk_cache[document_id] = chunks
        return chunks

    def _build_bm25(self, document_id: str, chunks: List[dict]) -> dict:
        if document_id in self._bm25_cache:
            return self._bm25_cache[document_id]
        # If we loaded chunks from disk cache, bm25 may already exist too.
        if document_id not in self._bm25_cache:
            self._try_load_index(document_id)
            if document_id in self._bm25_cache:
                return self._bm25_cache[document_id]

        tokenized_docs = [self._tokenize(c["text"]) for c in chunks]
        doc_lens = [len(toks) for toks in tokenized_docs]
        avg_dl = (sum(doc_lens) / len(doc_lens)) if doc_lens else 1.0
        df = Counter()
        for toks in tokenized_docs:
            for term in set(toks):
                df[term] += 1

        bm25 = {
            "tokenized_docs": tokenized_docs,
            "doc_lens": doc_lens,
            "avg_dl": avg_dl,
            "df": df,
            "N": max(1, len(tokenized_docs)),
            "k1": 1.5,
            "b": 0.75,
        }
        self._bm25_cache[document_id] = bm25
        # Persist after first build to make future retrieval instant
        self._save_index(document_id, chunks, bm25)
        return bm25

    def _bm25_score(self, query_tokens: List[str], bm25: dict, doc_idx: int) -> float:
        toks = bm25["tokenized_docs"][doc_idx]
        if not toks:
            return 0.0
        tf = Counter(toks)
        dl = bm25["doc_lens"][doc_idx]
        avg_dl = bm25["avg_dl"]
        k1 = bm25["k1"]
        b = bm25["b"]
        N = bm25["N"]
        score = 0.0
        for term in query_tokens:
            n = bm25["df"].get(term, 0)
            if n == 0:
                continue
            idf = math.log(1 + (N - n + 0.5) / (n + 0.5))
            freq = tf.get(term, 0)
            denom = freq + k1 * (1 - b + b * (dl / avg_dl))
            if denom > 0:
                score += idf * ((freq * (k1 + 1)) / denom)
        return score

    def _get_embedder(self):
        if self._embedder is not None:
            return self._embedder
        # Off by default to keep first-query latency predictable on Windows.
        # Enable explicitly with ENABLE_LOCAL_EMBED_RERANK=true
        if os.getenv("ENABLE_LOCAL_EMBED_RERANK", "false").lower() != "true":
            self._embedder = False
            return self._embedder
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            self._embedder = False
        return self._embedder

    def clear_cache(self, document_id: str = "") -> None:
        """Clear retrieval caches for one document or all documents."""
        if document_id:
            self._chunk_cache.pop(document_id, None)
            self._bm25_cache.pop(document_id, None)
            try:
                os.remove(self._index_path(document_id))
            except Exception:
                pass
            return
        self._chunk_cache.clear()
        self._bm25_cache.clear()
        try:
            for name in os.listdir(self._index_dir):
                if name.endswith(".pkl.gz"):
                    os.remove(os.path.join(self._index_dir, name))
        except Exception:
            pass

    def retrieve(self, query: str, document_id: str, top_k: int = 4) -> List[dict]:
        chunks = self._build_chunks(document_id)
        if not chunks:
            return []

        q_toks = self._tokenize(query)
        if not q_toks:
            return []

        bm25 = self._build_bm25(document_id, chunks)
        scored = []
        for i, ch in enumerate(chunks):
            bm = self._bm25_score(q_toks, bm25, i)
            if bm <= 0:
                continue
            overlap = sorted(list(set(q_toks).intersection(set(self._tokenize(ch["text"])))))
            scored.append((bm, i, overlap))

        if not scored:
            return []
        scored.sort(key=lambda x: x[0], reverse=True)
        candidates = scored[: max(12, top_k * 3)]

        # Optional semantic rerank on short candidate set
        embedder = self._get_embedder()
        if embedder:
            try:
                q_vec = embedder.encode([query], normalize_embeddings=True)[0]
                c_texts = [chunks[i]["text"][:1200] for _, i, _ in candidates]
                c_vecs = embedder.encode(c_texts, normalize_embeddings=True)
                reranked = []
                for (bm, i, overlap), v in zip(candidates, c_vecs):
                    sim = float((q_vec * v).sum())
                    final = (0.65 * bm) + (0.35 * max(sim, 0.0))
                    reranked.append((final, bm, i, overlap))
                reranked.sort(key=lambda x: x[0], reverse=True)
                candidates = [(f, i, overlap) for f, _bm, i, overlap in reranked]
            except Exception:
                pass

        top = candidates[:top_k]
        citations = []
        for score, idx, overlap in top:
            ch = chunks[idx]
            text = ch["text"]
            page_num = ch["page_num"]
            heading = ch["heading"]
            citations.append(
                {
                    "guideline": f"Local Document {document_id}",
                    "section": heading,
                    "page_range": f"p. {page_num}",
                    "evidence_strength": "moderate",
                    "reasoning": f"BM25/semantic match on: {', '.join(overlap[:8])}",
                    "content": text[:1800],
                    "text": text[:1800],
                    "snippet": text[:220] + ("..." if len(text) > 220 else ""),
                    "matched_keywords": overlap,
                    "score": round(float(score), 4),
                }
            )
        return citations
