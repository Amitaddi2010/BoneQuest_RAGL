# ============================================================
# BoneQuest v2 — Unified Hybrid Retriever
# Best-in-class RAG: BM25 + Semantic + PageIndex Tree + RRF + MMR
# ============================================================

import json
import math
import re
import logging
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
from sqlalchemy.orm import Session

from config import settings
from models.db_models import Document, DocumentChunk
from services.document_processing import detect_source_type, parse_document_to_chunks

logger = logging.getLogger(__name__)

# ── Stopwords & Synonyms ────────────────────────────────────

STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "are", "was", "were", "have",
    "has", "had", "not", "all", "any", "into", "than", "then", "them", "they", "their",
    "would", "could", "should", "about", "between", "after", "before", "which", "when",
    "what", "where", "how", "why", "your", "you", "our", "can", "may", "might", "will",
}

SYNONYM_MAP = {
    "tha": {"total", "hip", "arthroplasty", "replacement"},
    "arthroplasty": {"replacement", "prosthesis", "implant"},
    "orif": {"open", "reduction", "internal", "fixation"},
    "ddh": {"developmental", "dysplasia", "hip", "pavlik"},
    "fracture": {"break", "fractured", "fractures"},
    "pediatric": {"paediatric", "child", "children"},
    "osteonecrosis": {"avn", "avascular", "necrosis"},
    "avascular": {"osteonecrosis", "avn"},
    "palsy": {"neuropraxia", "neuropathy", "nerve"},
    "femoral": {"thigh", "femur"},
    "complication": {"adverse", "risk", "sequelae"},
    "rehabilitation": {"rehab", "recovery", "physiotherapy"},
    "implant": {"prosthesis", "hardware", "device"},
    "infection": {"sepsis", "septic", "osteomyelitis"},
}


# ── Tokenizer ────────────────────────────────────────────────

def tokenize(text: str) -> List[str]:
    """Tokenize text: extract words, de-hyphenate, light singularization."""
    toks = re.findall(r"[a-zA-Z][a-zA-Z0-9\-]{2,}", (text or "").lower())
    out: List[str] = []
    for t in toks:
        if t in STOPWORDS:
            continue
        out.append(t)
        if "-" in t:
            for part in t.split("-"):
                if len(part) >= 3 and part not in STOPWORDS:
                    out.append(part)
        if len(t) >= 6 and t.endswith("s"):
            out.append(t[:-1])
    return out


def expand_query_tokens(query_tokens: List[str]) -> List[str]:
    """Expand query tokens with synonyms."""
    expanded: Set[str] = set(query_tokens)
    for tok in query_tokens:
        for syn in SYNONYM_MAP.get(tok, set()):
            if len(syn) >= 3 and syn not in STOPWORDS:
                expanded.add(syn)
    return list(expanded)


# ── Embedding Manager ────────────────────────────────────────

class EmbeddingManager:
    """Lazy-loaded singleton for sentence-transformer embeddings."""

    _instance = None
    _model = None
    _init_attempted = False

    @classmethod
    def get_model(cls):
        if cls._init_attempted:
            return cls._model
        cls._init_attempted = True
        if not settings.ENABLE_SEMANTIC_RETRIEVAL:
            cls._model = None
            return None
        try:
            from sentence_transformers import SentenceTransformer
            cls._model = SentenceTransformer(settings.EMBEDDING_MODEL)
            logger.info(f"[HybridRetriever] Loaded embedding model: {settings.EMBEDDING_MODEL}")
        except Exception as e:
            logger.warning(f"[HybridRetriever] Embedding model unavailable: {e}")
            cls._model = None
        return cls._model

    @classmethod
    def warmup(cls):
        """Eagerly load the model at startup so first query isn't slow."""
        model = cls.get_model()
        if model is not None:
            # Run a tiny encode to trigger all internal lazy inits (tokenizer, ONNX, etc.)
            try:
                model.encode(["warmup"], normalize_embeddings=True, show_progress_bar=False)
                logger.info("[HybridRetriever] Embedding model warmed up")
            except Exception:
                pass
        return model is not None

    @classmethod
    def encode(cls, texts: List[str]) -> Optional[List[List[float]]]:
        """Encode texts into embeddings. Returns None if model unavailable."""
        model = cls.get_model()
        if model is None or not texts:
            return None
        try:
            vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
            return [v.tolist() for v in vectors]
        except Exception as e:
            logger.warning(f"[HybridRetriever] Encoding failed: {e}")
            return None

    @classmethod
    def encode_single(cls, text: str) -> Optional[List[float]]:
        """Encode a single text into an embedding vector."""
        result = cls.encode([text])
        return result[0] if result else None


# ── BM25 Scorer ──────────────────────────────────────────────

class BM25Scorer:
    """Okapi BM25 scoring over a set of tokenized documents."""

    def __init__(self, tokenized_docs: List[List[str]], k1: float = 1.5, b: float = 0.75):
        self.tokenized_docs = tokenized_docs
        self.k1 = k1
        self.b = b
        self.n_docs = max(len(tokenized_docs), 1)
        self.doc_lens = [len(toks) for toks in tokenized_docs]
        self.avg_dl = sum(self.doc_lens) / self.n_docs if self.n_docs else 1.0

        # Document frequency
        self.df: Counter = Counter()
        for toks in tokenized_docs:
            for term in set(toks):
                self.df[term] += 1

    def score(self, query_tokens: List[str], doc_idx: int) -> float:
        """Score a single document against query tokens."""
        toks = self.tokenized_docs[doc_idx]
        if not toks:
            return 0.0
        tf = Counter(toks)
        dl = self.doc_lens[doc_idx]
        score = 0.0
        for term in query_tokens:
            n = self.df.get(term, 0)
            if n <= 0:
                continue
            idf = math.log(1 + (self.n_docs - n + 0.5) / (n + 0.5))
            freq = tf.get(term, 0)
            denom = freq + self.k1 * (1 - self.b + self.b * (dl / max(self.avg_dl, 1.0)))
            if denom > 0:
                score += idf * ((freq * (self.k1 + 1)) / denom)
        return score

    def score_all(self, query_tokens: List[str]) -> List[Tuple[int, float]]:
        """Score all documents, return sorted (doc_idx, score) pairs with score > 0."""
        results = []
        for i in range(self.n_docs):
            s = self.score(query_tokens, i)
            if s > 0:
                results.append((i, s))
        results.sort(key=lambda x: x[1], reverse=True)
        return results


# ── Reciprocal Rank Fusion ───────────────────────────────────

def reciprocal_rank_fusion(
    ranked_lists: List[List[Tuple[int, float]]],
    k: int = 60,
) -> List[Tuple[int, float]]:
    """
    Merge multiple ranked lists using Reciprocal Rank Fusion (RRF).
    
    Each list is [(doc_idx, score), ...] sorted by score desc.
    Returns [(doc_idx, rrf_score), ...] sorted by RRF score desc.
    
    RRF formula: RRF(d) = Σ 1/(k + rank_i(d)) for each ranking_list i
    """
    scores: Dict[int, float] = {}
    for ranked_list in ranked_lists:
        for rank, (doc_idx, _original_score) in enumerate(ranked_list):
            if doc_idx not in scores:
                scores[doc_idx] = 0.0
            scores[doc_idx] += 1.0 / (k + rank + 1)  # rank is 0-indexed

    result = [(idx, score) for idx, score in scores.items()]
    result.sort(key=lambda x: x[1], reverse=True)
    return result


# ── MMR Diversity Selector ───────────────────────────────────

def mmr_select(
    candidates: List[Dict],
    chunk_cap: int,
    token_budget: int,
    lambda_mult: float = 0.72,
) -> List[Dict]:
    """
    Maximal Marginal Relevance selection for diversity.
    
    candidates: list of dicts with 'score', 'tokens_set', 'chunk' keys
    Returns selected candidates respecting chunk_cap and token_budget.
    """
    selected: List[Dict] = []
    used_tokens = 0
    remaining = list(candidates)

    while remaining and len(selected) < chunk_cap and used_tokens < token_budget:
        best = None
        best_mmr = -1e9

        for cand in remaining:
            c_tokens = cand["tokens_set"]
            novelty_penalty = 0.0
            if selected:
                novelty_penalty = max(
                    len(c_tokens.intersection(sel["tokens_set"])) / max(len(c_tokens), 1)
                    for sel in selected
                )
            mmr = (lambda_mult * cand["score"]) - ((1.0 - lambda_mult) * novelty_penalty)
            if mmr > best_mmr:
                best_mmr = mmr
                best = cand

        if not best:
            break

        token_count = best["chunk"].token_count or 0
        if used_tokens + token_count <= token_budget:
            selected.append(best)
            used_tokens += token_count
        remaining = [r for r in remaining if r["chunk"].id != best["chunk"].id]

    return selected


# ── Cross-Encoder Reranker ───────────────────────────────────

class CrossEncoderReranker:
    """Optional cross-encoder reranking for top candidates."""

    _model = None
    _init_attempted = False

    @classmethod
    def get_model(cls):
        if cls._init_attempted:
            return cls._model
        cls._init_attempted = True
        if not bool(getattr(settings, "ENABLE_HYBRID_RERANK", False)):
            cls._model = None
            return None
        try:
            from sentence_transformers import CrossEncoder
            cls._model = CrossEncoder(settings.HYBRID_RERANK_MODEL)
            logger.info(f"[HybridRetriever] Loaded cross-encoder: {settings.HYBRID_RERANK_MODEL}")
        except Exception as e:
            logger.warning(f"[HybridRetriever] Cross-encoder unavailable: {e}")
            cls._model = None
        return cls._model

    @classmethod
    def rerank(cls, query: str, candidates: List[Dict], topn: int = 24) -> List[Dict]:
        """Rerank top candidates using cross-encoder. Blends CE score with existing score."""
        model = cls.get_model()
        if not model or not candidates:
            return candidates

        topn = max(4, min(topn, len(candidates)))
        blend = float(getattr(settings, "HYBRID_RERANK_BLEND", 0.25) or 0.25)
        blend = min(max(blend, 0.0), 0.5)

        rerank_pool = candidates[:topn]
        try:
            pairs = [(query, c["chunk"].content[:2200]) for c in rerank_pool]
            preds = model.predict(pairs)
            for c, ce_score in zip(rerank_pool, preds):
                ce_norm = 1.0 / (1.0 + math.exp(-float(ce_score)))
                c["score"] = ((1.0 - blend) * float(c["score"])) + (blend * ce_norm)
            rerank_pool.sort(key=lambda x: x["score"], reverse=True)
            return rerank_pool + candidates[topn:]
        except Exception:
            return candidates


# ── Main Hybrid Retriever ────────────────────────────────────

class HybridRetriever:
    """
    Unified hybrid retrieval pipeline:
    1. BM25 lexical retrieval
    2. Dense semantic embedding retrieval
    3. Reciprocal Rank Fusion to merge rankings
    4. Optional cross-encoder reranking
    5. MMR diversity selection with token budgeting
    """

    def __init__(self):
        self.min_relevance = float(settings.MIN_RELEVANCE_SCORE)
        self._uploads_dir = Path(__file__).resolve().parent.parent / "data" / "uploads"

    def build_context_package(
        self,
        db: Session,
        query: str,
        document_id: Optional[str] = None,
        token_budget: Optional[int] = None,
        max_chunks: Optional[int] = None,
    ) -> Dict:
        """
        Main entry point: retrieve relevant document chunks for a query.
        
        Returns dict with:
        - context: formatted text context for LLM
        - citations: list of citation dicts
        - retrieval: metadata about the retrieval process
        """
        budget = min(
            token_budget or settings.DEFAULT_CONTEXT_TOKEN_BUDGET,
            settings.MAX_CONTEXT_TOKEN_BUDGET,
        )
        chunk_cap = max_chunks or settings.MAX_CONTEXT_CHUNKS

        # 1. Resolve target documents
        docs, doc_ids, selected_scope = self._resolve_documents(db, document_id)
        requested_document_id = document_id

        if not doc_ids:
            return self._empty_result("no_documents", requested_document_id, selected_scope)

        # 2. Fetch all chunks
        chunks = self._fetch_chunks(db, doc_ids, docs)
        if not chunks:
            return self._empty_result("no_chunks", requested_document_id, selected_scope)

        # 3. Tokenize query
        query_tokens = tokenize(query)
        if not query_tokens:
            # Fallback: still try semantic retrieval even with empty tokens
            if not settings.ENABLE_SEMANTIC_RETRIEVAL:
                return self._empty_result("empty_query_tokens", requested_document_id, selected_scope)

        expanded_tokens = expand_query_tokens(query_tokens) if query_tokens else []

        # 4. Run BM25 retrieval
        tokenized_chunks = [tokenize(ch.content) for ch in chunks]
        bm25_ranked = []
        if expanded_tokens:
            bm25_scorer = BM25Scorer(tokenized_chunks)
            bm25_ranked = bm25_scorer.score_all(expanded_tokens)

        # 5. Run semantic embedding retrieval  
        semantic_ranked = self._semantic_retrieval(query, chunks)

        # 6. Run PageIndex tree search (3rd retrieval signal)
        tree_ranked = self._tree_retrieval(db, query, document_id)
        tree_search_used = bool(tree_ranked)

        # 7. Reciprocal Rank Fusion (2-way or 3-way)
        rank_lists = [r for r in [bm25_ranked, semantic_ranked, tree_ranked] if r]
        if len(rank_lists) >= 2:
            fused = reciprocal_rank_fusion(rank_lists, k=settings.RRF_K)
            methods = []
            if bm25_ranked: methods.append("bm25")
            if semantic_ranked: methods.append("semantic")
            if tree_ranked: methods.append("tree")
            retrieval_method = f"hybrid_{'_'.join(methods)}_rrf"
        elif len(rank_lists) == 1:
            fused = rank_lists[0]
            if bm25_ranked: retrieval_method = "bm25_only"
            elif semantic_ranked: retrieval_method = "semantic_only"
            else: retrieval_method = "tree_only"
        else:
            return self._empty_result("no_relevant_chunks", requested_document_id, selected_scope)

        # 8. Build scored candidate list
        scored_candidates = self._build_scored_candidates(
            fused, chunks, tokenized_chunks, query_tokens, expanded_tokens, query
        )

        if not scored_candidates:
            return self._empty_result("no_relevant_chunks", requested_document_id, selected_scope)

        # 9. Optional cross-encoder reranking
        scored_candidates = CrossEncoderReranker.rerank(
            query, scored_candidates,
            topn=int(getattr(settings, "HYBRID_RERANK_TOPN", 24)),
        )

        # 10. MMR diversity selection
        selected = mmr_select(scored_candidates, chunk_cap=chunk_cap, token_budget=budget)
        used_tokens = sum((s["chunk"].token_count or 0) for s in selected)

        if not selected:
            return self._empty_result("no_relevant_chunks", requested_document_id, selected_scope)

        # 11. Build context and citations
        docs_by_id = {d.id: d for d in docs}
        context_parts, citations, chunks_meta = self._build_output(
            selected, docs_by_id, query_tokens, retrieval_method
        )

        # 12. Deduplication
        citations, chunks_meta = self._deduplicate(citations, chunks_meta)

        # 13. Compute quality metrics
        avg_overlap_ratio = sum(float(s["overlap_ratio"]) for s in selected) / max(len(selected), 1)
        direct_hits = sum(1 for c in citations if c.get("match_type") == "direct")

        return {
            "context": "\n\n".join(context_parts),
            "citations": citations,
            "retrieval": {
                "strategy": "context_injection",
                "source": "hybrid_document_chunks",
                "used_rag": bool(citations),
                "ranker": retrieval_method,
                "rerank_enabled": bool(getattr(settings, "ENABLE_HYBRID_RERANK", False)),
                "semantic_enabled": bool(semantic_ranked),
                "tree_search_enabled": tree_search_used,
                "requested_document_id": requested_document_id,
                "scope": selected_scope,
                "document_id": document_id,
                "citations_count": len(citations),
                "token_budget": budget,
                "tokens_used": used_tokens,
                "avg_overlap_ratio": round(avg_overlap_ratio, 3),
                "direct_hits": direct_hits,
                "indirect_hits": max(len(citations) - direct_hits, 0),
                "evidence_mode": "direct" if direct_hits > 0 else "indirect",
                "selected_chunks": chunks_meta,
            },
        }

    # ── Internal Methods ─────────────────────────────────────

    def _resolve_documents(
        self, db: Session, document_id: Optional[str]
    ) -> Tuple[List, List[int], str]:
        """Resolve which documents to search."""
        docs_query = db.query(Document).filter(Document.status == "indexed")
        selected_scope = "global"

        if document_id and document_id not in {"global", "all"}:
            selected_scope = "document_specific"
            docs = docs_query.filter(
                (Document.internal_id == document_id)
                | (Document.doc_id == document_id)
                | (Document.name == document_id)
            ).all()

            # doc-N alias support
            if not docs:
                m = re.match(r"^doc-(\d+)$", (document_id or "").strip().lower())
                if m:
                    idx = max(int(m.group(1)) - 1, 0)
                    ordered_docs = docs_query.order_by(Document.created_at.asc()).all()
                    if idx < len(ordered_docs):
                        docs = [ordered_docs[idx]]

            # Fallback to all docs if specific ID not found
            if not docs:
                docs = docs_query.all()
                selected_scope = "document_fallback_global"
        else:
            docs = docs_query.all()

        doc_ids = [d.id for d in docs]
        return docs, doc_ids, selected_scope

    def _fetch_chunks(self, db: Session, doc_ids: List[int], docs: List) -> List:
        """Fetch chunks from DB, auto-indexing if needed."""
        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id.in_(doc_ids))
            .order_by(DocumentChunk.document_id.asc(), DocumentChunk.chunk_index.asc())
            .all()
        )
        if not chunks:
            self._ensure_chunks_for_docs(db, docs)
            chunks = (
                db.query(DocumentChunk)
                .filter(DocumentChunk.document_id.in_(doc_ids))
                .order_by(DocumentChunk.document_id.asc(), DocumentChunk.chunk_index.asc())
                .all()
            )
        return chunks

    def _semantic_retrieval(
        self, query: str, chunks: List
    ) -> List[Tuple[int, float]]:
        """Run dense semantic embedding retrieval over chunks."""
        if not settings.ENABLE_SEMANTIC_RETRIEVAL:
            return []

        query_embedding = EmbeddingManager.encode_single(query)
        if query_embedding is None:
            return []

        query_vec = np.array(query_embedding, dtype=np.float32)

        # Parse precomputed embeddings and identify missing ones
        chunk_vectors: List[Optional[np.ndarray]] = []
        missing_indices: List[int] = []
        missing_texts: List[str] = []

        for i, chunk in enumerate(chunks):
            vec = None
            if chunk.embedding:
                try:
                    raw = json.loads(chunk.embedding) if isinstance(chunk.embedding, str) else chunk.embedding
                    vec = np.array(raw, dtype=np.float32)
                except Exception:
                    pass
            chunk_vectors.append(vec)
            if vec is None:
                missing_indices.append(i)
                missing_texts.append((chunk.content or "")[:1500])

        # Batch-compute ALL missing embeddings in a single model call
        if missing_texts:
            batch_embeddings = EmbeddingManager.encode(missing_texts)
            if batch_embeddings:
                for idx, emb in zip(missing_indices, batch_embeddings):
                    chunk_vectors[idx] = np.array(emb, dtype=np.float32)

        # Score all chunks
        results = []
        for i, vec in enumerate(chunk_vectors):
            if vec is not None:
                sim = float(np.dot(query_vec, vec))
                if sim > 0.15:
                    results.append((i, sim))

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def _tree_retrieval(
        self, db: Session, query: str, document_id: Optional[str]
    ) -> List[Tuple[int, float]]:
        """Run PageIndex tree search and return (chunk_index, score) tuples."""
        if not settings.ENABLE_TREE_SEARCH:
            return []
        try:
            from services.pageindex_service import tree_search
            tree_results = tree_search(db, query, document_id)
            # tree_search returns (chunk_idx, score, title) — drop title for RRF
            return [(idx, score) for idx, score, _ in tree_results]
        except ImportError:
            return []
        except Exception as e:
            logger.warning(f"[HybridRetriever] Tree search failed: {e}")
            return []

    def _build_scored_candidates(
        self,
        fused_ranking: List[Tuple[int, float]],
        chunks: List,
        tokenized_chunks: List[List[str]],
        query_tokens: List[str],
        expanded_tokens: List[str],
        query: str,
    ) -> List[Dict]:
        """Build scored candidate list from fused ranking."""
        query_token_set = set(query_tokens)
        expanded_token_set = set(expanded_tokens)
        max_fused_score = max((s for _, s in fused_ranking), default=1.0)

        candidates = []
        for doc_idx, fused_score in fused_ranking:
            if doc_idx >= len(chunks):
                continue

            chunk = chunks[doc_idx]
            toks = tokenized_chunks[doc_idx] if doc_idx < len(tokenized_chunks) else []
            tok_set = set(toks)

            # Compute overlap metrics
            overlap_terms = query_token_set.intersection(tok_set)
            overlap_ratio = len(overlap_terms) / max(len(query_token_set), 1)
            coverage = len(expanded_token_set.intersection(tok_set)) / max(len(expanded_token_set), 1)

            # Phrase overlap
            phrase_score = self._phrase_overlap_score(query, chunk.content or "")

            # Normalize fused score
            norm_score = fused_score / max(max_fused_score, 1e-9)

            # Final composite score
            score = (0.55 * norm_score) + (0.25 * coverage) + (0.15 * phrase_score) + (0.05 * overlap_ratio)

            if score >= self.min_relevance:
                candidates.append({
                    "score": float(score),
                    "overlap_ratio": float(overlap_ratio),
                    "overlap_terms": overlap_terms,
                    "chunk": chunk,
                    "tokens_set": tok_set,
                })

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates

    def _phrase_overlap_score(self, query: str, chunk_text: str) -> float:
        """Score based on multi-word phrase matches."""
        q = (query or "").lower()
        c = (chunk_text or "").lower()
        phrases = re.findall(r"[a-zA-Z][a-zA-Z0-9\-]{3,}(?:\s+[a-zA-Z][a-zA-Z0-9\-]{3,})+", q)
        if not phrases:
            return 0.0
        hits = sum(1 for p in set(phrases) if p in c)
        return hits / max(len(set(phrases)), 1)

    def _format_reasoning_label(self, retrieval_method: str) -> str:
        """Convert internal retrieval_method to a human-readable reasoning label."""
        rm = (retrieval_method or "").lower()

        # Map signal keys to display names
        signals = []
        if "bm25" in rm:
            signals.append("BM25")
        if "semantic" in rm:
            signals.append("Semantic")
        if "tree" in rm:
            signals.append("Tree")

        if not signals:
            # Fallback for unknown method identifiers
            if "only" in rm:
                return f"{rm.replace('_only', '').replace('_', ' ').title()} retrieval"
            return "Hybrid retrieval"

        if len(signals) == 1:
            return f"{signals[0]} retrieval"

        return f"Hybrid {'+'.join(signals)} retrieval"

    def _build_output(
        self,
        selected: List[Dict],
        docs_by_id: Dict,
        query_tokens: List[str],
        retrieval_method: str = "hybrid_bm25_semantic_rrf",
    ) -> Tuple[List[str], List[Dict], List[Dict]]:
        """Build context text, citations, and chunk metadata."""
        query_token_set = set(query_tokens)
        context_parts = []
        citations = []
        chunks_meta = []

        for sel in selected:
            chunk = sel["chunk"]
            score = sel["score"]
            overlap_ratio = sel["overlap_ratio"]
            overlap_terms = sel["overlap_terms"]

            doc = docs_by_id.get(chunk.document_id)
            title = doc.name if doc else "Document"
            content = chunk.content  # No truncation — let token budget handle limits

            context_parts.append(
                f"[{title} | {chunk.section or 'General'} | {chunk.page_label or 'n/a'}]\n{content}"
            )

            # Determine match type
            min_overlap_terms = 2 if len(query_token_set) >= 4 else 1
            is_direct = overlap_ratio >= 0.25 and len(overlap_terms) >= min_overlap_terms
            match_type = "direct" if is_direct else "indirect"

            citations.append({
                "guideline": title,
                "section": chunk.section or "General",
                "page_range": chunk.page_label or "",
                "evidence_strength": "moderate",
                "reasoning": self._format_reasoning_label(retrieval_method),
                "content": content,
                "text": content,
                "snippet": content[:220] + ("..." if len(content) > 220 else ""),
                "score": round(float(score), 4),
                "overlap_ratio": round(float(overlap_ratio), 3),
                "match_type": match_type,
            })

            chunks_meta.append({
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "score": round(float(score), 4),
                "token_count": chunk.token_count or 0,
                "overlap_terms": sorted(list(overlap_terms))[:10],
                "overlap_ratio": round(float(overlap_ratio), 3),
            })

        return context_parts, citations, chunks_meta

    def _deduplicate(
        self, citations: List[Dict], chunks_meta: List[Dict]
    ) -> Tuple[List[Dict], List[Dict]]:
        """Remove near-duplicate citations."""
        deduped_citations = []
        deduped_chunks = []
        seen = set()

        for c, m in zip(citations, chunks_meta):
            key = (
                (c.get("section") or "").strip().lower(),
                (c.get("page_range") or "").strip().lower(),
                re.sub(r"\s+", " ", (c.get("snippet") or "").strip().lower())[:140],
            )
            if key in seen:
                continue
            seen.add(key)
            deduped_citations.append(c)
            deduped_chunks.append(m)

        return deduped_citations, deduped_chunks

    def _empty_result(
        self, source: str, requested_document_id: Optional[str], scope: str = "global"
    ) -> Dict:
        return {
            "context": "",
            "citations": [],
            "retrieval": {
                "strategy": "context_injection",
                "source": source,
                "used_rag": False,
                "requested_document_id": requested_document_id,
                "scope": scope,
            },
        }

    # ── Auto-indexing ────────────────────────────────────────

    def _resolve_document_file_path(self, doc: Document) -> Optional[Path]:
        file_key = doc.internal_id or doc.doc_id
        if not file_key:
            return None
        for ext in [".pdf", ".docx", ".txt", ".md"]:
            p = self._uploads_dir / f"{file_key}{ext}"
            if p.exists():
                return p
        return None

    def _ensure_chunks_for_docs(self, db: Session, docs: List[Document]) -> None:
        """Auto-index documents that have no chunks. No artificial cap."""
        for doc in docs:
            existing = db.query(DocumentChunk.id).filter(DocumentChunk.document_id == doc.id).first()
            if existing:
                continue
            file_path = self._resolve_document_file_path(doc)
            if not file_path:
                continue
            if file_path.stat().st_size > 50 * 1024 * 1024:  # 50MB limit
                doc.status = "error"
                db.commit()
                continue
            try:
                source_type = detect_source_type(file_path.name)
                chunks_data = parse_document_to_chunks(
                    str(file_path), source_type,
                    overlap_chars=settings.CHUNK_OVERLAP_CHARS,
                )

                # Compute embeddings for all chunks in batch
                chunk_texts = [ch["content"][:1500] for ch in chunks_data]
                embeddings = EmbeddingManager.encode(chunk_texts)

                for i, ch in enumerate(chunks_data):
                    emb = embeddings[i] if embeddings and i < len(embeddings) else None
                    db.add(
                        DocumentChunk(
                            document_id=doc.id,
                            chunk_index=ch["chunk_index"],
                            source_type=ch["source_type"],
                            section=ch.get("section"),
                            page_label=ch.get("page_label"),
                            content=ch["content"],
                            token_count=ch.get("token_count", 0),
                            embedding=emb,
                            embedding_model=settings.EMBEDDING_MODEL if emb else None,
                        )
                    )
                if chunks_data:
                    doc.status = "indexed"
            except Exception as e:
                logger.error(f"[HybridRetriever] Auto-index failed for {doc.name}: {e}")
                doc.status = "error"
            finally:
                db.commit()


def compute_embeddings_for_chunks(db: Session, doc_id: int) -> int:
    """
    Compute and store embeddings for all chunks of a document that don't have them.
    Returns the number of chunks updated.
    """
    chunks = (
        db.query(DocumentChunk)
        .filter(
            DocumentChunk.document_id == doc_id,
            DocumentChunk.embedding.is_(None),
        )
        .all()
    )
    if not chunks:
        return 0

    texts = [ch.content[:1500] for ch in chunks]
    embeddings = EmbeddingManager.encode(texts)
    if not embeddings:
        return 0

    count = 0
    for chunk, emb in zip(chunks, embeddings):
        chunk.embedding = emb
        chunk.embedding_model = settings.EMBEDDING_MODEL
        count += 1

    db.commit()
    return count
