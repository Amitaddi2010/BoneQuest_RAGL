import math
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Set

from sqlalchemy.orm import Session

from config import settings
from models.db_models import Document, DocumentChunk
from services.document_processing import detect_source_type, parse_document_to_chunks

STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "are", "was", "were", "have",
    "has", "had", "not", "all", "any", "into", "than", "then", "them", "they", "their",
    "would", "could", "should", "about", "between", "after", "before", "which", "when",
    "what", "where", "how", "why", "your", "you", "our", "can", "may", "might", "will",
}
ANATOMY_NOISE_TERMS = {"knee", "ankle", "foot", "upper extremity", "wrist", "elbow", "shoulder"}
PAVLIK_NOISE_TERMS = {"acetabular fracture", "intramedullary", "femoral shaft", "kocher-langenbeck", "ilioinguinal"}
TOC_NOISE_PATTERNS = (
    r"\b\d{2,3}\.\s+[A-Z]",
    r"\btable of contents\b",
    r"\bchapter\s+\d+\b",
)
COMPARISON_HINTS = {"vs", "versus", "compare", "comparison", "difference"}
SYNONYM_MAP = {
    "tha": {"total", "hip", "arthroplasty", "replacement"},
    "arthroplasty": {"replacement", "prosthesis", "implant"},
    "orif": {"open", "reduction", "internal", "fixation"},
    "ddh": {"developmental", "dysplasia", "hip", "pavlik"},
    "fracture": {"break", "fractured", "fractures"},
    "pediatric": {"paediatric", "child", "children"},
    "osteonecrosis": {"avn", "avascular", "necrosis"},
    "avascular": {"osteonecrosis", "avn"},
    "necrosis": {"osteonecrosis", "avn"},
    "palsy": {"neuropraxia", "neuropathy", "nerve"},
    "femoral": {"thigh", "femur"},
    "sciatic": {"ischiadic"},
    "complication": {"adverse", "risk", "sequelae"},
}
MCQ_COMPLICATION_SYNONYM_GROUPS = [
    {"complication", "complications", "adverse", "sequelae"},
    {"osteonecrosis", "avascular", "necrosis", "avn"},
    {"palsy", "neuropraxia", "neuropathy", "nerve"},
]


def _tokenize(text: str) -> List[str]:
    toks = re.findall(r"[a-zA-Z][a-zA-Z0-9\-]{2,}", (text or "").lower())
    out: List[str] = []
    for t in toks:
        if t in STOPWORDS:
            continue
        out.append(t)
        # Add de-hyphenated components to improve matching for terms like "chicken-wire".
        if "-" in t:
            for part in t.split("-"):
                if len(part) >= 3 and part not in STOPWORDS:
                    out.append(part)
        # Light singularization for common plural variants (calcifications -> calcification).
        if len(t) >= 6 and t.endswith("s"):
            out.append(t[:-1])
    return out


class ContextInjectionService:
    def __init__(self) -> None:
        self.min_relevance = float(settings.MIN_RELEVANCE_SCORE)
        self._uploads_dir = (Path(__file__).resolve().parent.parent / "data" / "uploads")
        self._cross_encoder = None
        self._cross_encoder_init_attempted = False

    def _bm25_score(self, q_tokens: List[str], d_tokens: List[str], df: Counter, n_docs: int, avg_dl: float) -> float:
        tf = Counter(d_tokens)
        dl = len(d_tokens)
        k1 = 1.5
        b = 0.75
        score = 0.0
        for term in q_tokens:
            n = df.get(term, 0)
            if n <= 0:
                continue
            idf = math.log(1 + (n_docs - n + 0.5) / (n + 0.5))
            freq = tf.get(term, 0)
            denom = freq + k1 * (1 - b + b * (dl / max(avg_dl, 1.0)))
            if denom:
                score += idf * ((freq * (k1 + 1)) / denom)
        return score

    def _expand_query_tokens(self, query_tokens: List[str]) -> List[str]:
        expanded: Set[str] = set(query_tokens)
        for tok in query_tokens:
            for syn in SYNONYM_MAP.get(tok, set()):
                if len(syn) >= 3 and syn not in STOPWORDS:
                    expanded.add(syn)
        return list(expanded)

    def _mcq_semantic_overlap(self, query_tokens: List[str], chunk_tokens: List[str]) -> int:
        if not query_tokens or not chunk_tokens:
            return 0
        qset = set(query_tokens)
        cset = set(chunk_tokens)
        hits = len(qset.intersection(cset))
        for group in MCQ_COMPLICATION_SYNONYM_GROUPS:
            if qset.intersection(group) and cset.intersection(group):
                hits += 1
        return hits

    def _phrase_overlap_score(self, query: str, chunk_text: str) -> float:
        q = (query or "").lower()
        c = (chunk_text or "").lower()
        phrases = re.findall(r"[a-zA-Z][a-zA-Z0-9\-]{3,}(?:\s+[a-zA-Z][a-zA-Z0-9\-]{3,})+", q)
        if not phrases:
            return 0.0
        hits = sum(1 for p in set(phrases) if p in c)
        return hits / max(len(set(phrases)), 1)

    def _proximity_boost(self, query_tokens: List[str], chunk_tokens: List[str]) -> float:
        if len(query_tokens) < 2 or not chunk_tokens:
            return 0.0
        first = query_tokens[0]
        last = query_tokens[-1]
        idx_first = [i for i, t in enumerate(chunk_tokens[:250]) if t == first][:3]
        idx_last = [i for i, t in enumerate(chunk_tokens[:250]) if t == last][:3]
        if not idx_first or not idx_last:
            return 0.0
        min_dist = min(abs(i - j) for i in idx_first for j in idx_last)
        return max(0.0, 1.0 - (min_dist / 40.0))

    def _mmr_select(
        self,
        candidates: List[dict],
        chunk_cap: int,
        budget: int,
        lambda_mult: float = 0.72,
    ) -> List[dict]:
        selected: List[dict] = []
        used_tokens = 0
        remaining = candidates[:]
        while remaining and len(selected) < chunk_cap and used_tokens < budget:
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
            if used_tokens + token_count <= budget:
                selected.append(best)
                used_tokens += token_count
            remaining = [r for r in remaining if r["chunk"].id != best["chunk"].id]
        return selected

    def _get_cross_encoder(self):
        if self._cross_encoder_init_attempted:
            return self._cross_encoder
        self._cross_encoder_init_attempted = True
        if not bool(getattr(settings, "ENABLE_HYBRID_RERANK", False)):
            self._cross_encoder = False
            return self._cross_encoder
        try:
            from sentence_transformers import CrossEncoder  # type: ignore

            self._cross_encoder = CrossEncoder(settings.HYBRID_RERANK_MODEL)
        except Exception:
            self._cross_encoder = False
        return self._cross_encoder

    def _cross_encoder_rerank(self, query: str, candidates: List[dict]) -> List[dict]:
        model = self._get_cross_encoder()
        if not model or not candidates:
            return candidates
        topn = int(getattr(settings, "HYBRID_RERANK_TOPN", 24) or 24)
        topn = max(4, min(topn, len(candidates)))
        blend = float(getattr(settings, "HYBRID_RERANK_BLEND", 0.25) or 0.25)
        blend = min(max(blend, 0.0), 0.5)
        rerank_pool = candidates[:topn]
        try:
            pairs = [(query, c["chunk"].content[:2200]) for c in rerank_pool]
            preds = model.predict(pairs)
            for c, ce_score in zip(rerank_pool, preds):
                # Normalize pair score to [0,1] and keep lexical rank dominant.
                ce_norm = 1.0 / (1.0 + math.exp(-float(ce_score)))
                c["score"] = ((1.0 - blend) * float(c["score"])) + (blend * ce_norm)
            rerank_pool.sort(key=lambda x: x["score"], reverse=True)
            return rerank_pool + candidates[topn:]
        except Exception:
            return candidates

    def build_context_package(
        self,
        db: Session,
        query: str,
        document_id: Optional[str],
        token_budget: Optional[int] = None,
        max_chunks: Optional[int] = None,
    ) -> Dict:
        budget = min(token_budget or settings.DEFAULT_CONTEXT_TOKEN_BUDGET, settings.MAX_CONTEXT_TOKEN_BUDGET)
        chunk_cap = max_chunks or settings.MAX_CONTEXT_CHUNKS

        docs_query = db.query(Document).filter(Document.status == "indexed")
        selected_scope = "global"
        requested_document_id = document_id
        docs = []
        if document_id and document_id not in {"global", "all"}:
            selected_scope = "document_specific"
            docs = docs_query.filter(
                (Document.internal_id == document_id)
                | (Document.doc_id == document_id)
                | (Document.name == document_id)
            ).all()
            # Backward-compatible alias support: doc-1, doc-2, ... maps to nth indexed doc.
            if not docs:
                m = re.match(r"^doc-(\d+)$", (document_id or "").strip().lower())
                if m:
                    idx = max(int(m.group(1)) - 1, 0)
                    ordered_docs = docs_query.order_by(Document.created_at.asc()).all()
                    if idx < len(ordered_docs):
                        docs = [ordered_docs[idx]]
            # Safety fallback: if explicit id is stale/non-existent, search all indexed docs.
            if not docs:
                docs = docs_query.all()
                selected_scope = "document_fallback_global"
        else:
            docs = docs_query.all()
        doc_ids = [d.id for d in docs]
        if not doc_ids:
            return {
                "context": "",
                "citations": [],
                "retrieval": {
                    "strategy": "context_injection",
                    "source": "no_documents",
                    "used_rag": False,
                    "requested_document_id": requested_document_id,
                    "scope": selected_scope,
                },
            }

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
        if not chunks:
            return {"context": "", "citations": [], "retrieval": {"strategy": "context_injection", "source": "no_chunks", "used_rag": False}}

        query_tokens = _tokenize(query)
        if not query_tokens:
            return {"context": "", "citations": [], "retrieval": {"strategy": "context_injection", "source": "empty_query_tokens", "used_rag": False}}
        expanded_query_tokens = self._expand_query_tokens(query_tokens)
        query_text = (query or "").lower()
        query_token_set = set(query_tokens)
        expanded_query_token_set = set(expanded_query_tokens)
        has_total_hip_intent = ("hip" in query_token_set and "arthroplasty" in query_token_set) or ("total hip arthroplasty" in query_text)
        has_pavlik_ddh_intent = ("pavlik" in query_text) or ("developmental dysplasia of the hip" in query_text) or (" ddh" in f" {query_text}")
        is_comparison_query = any(h in query_text for h in COMPARISON_HINTS)
        comparison_terms = set()
        if has_total_hip_intent and "anterolateral" in query_text:
            comparison_terms.add("anterolateral")
        if has_total_hip_intent and "medial" in query_text:
            comparison_terms.add("medial")
        is_hip_approach_comparison = has_total_hip_intent and is_comparison_query and bool(comparison_terms)

        tokenized_docs = [_tokenize(ch.content) for ch in chunks]
        df = Counter()
        for toks in tokenized_docs:
            for term in set(toks):
                df[term] += 1
        avg_dl = sum(len(toks) for toks in tokenized_docs) / max(len(tokenized_docs), 1)

        is_mcq = bool(re.search(r"\bexcept\b|\bmost likely\b|\bbest next step\b|\b[1-9]\)|\b[a-d]\)", (query or "").lower()))
        mcq_pattern_query = bool(re.search(r"\btypical of\b|\bclassically\b|\bmost likely\b", query_text))
        raw_candidates = []
        max_bm25 = 0.0
        for ch, toks in zip(chunks, tokenized_docs):
            bm25 = self._bm25_score(expanded_query_tokens, toks, df, len(tokenized_docs), avg_dl)
            if bm25 <= 0:
                continue
            overlap_terms = set(query_tokens).intersection(set(toks))
            overlap = len(overlap_terms)
            semantic_overlap = self._mcq_semantic_overlap(expanded_query_tokens, toks) if is_mcq else overlap
            overlap_ratio = overlap / max(len(query_token_set), 1)
            chunk_text_lower = (ch.content or "").lower()
            # Precision guard for THA-style queries: avoid cross-anatomy contamination.
            if has_total_hip_intent and "hip" not in set(toks):
                continue
            if has_total_hip_intent and any(term in chunk_text_lower for term in ANATOMY_NOISE_TERMS):
                if "hip" not in chunk_text_lower:
                    continue
            # Precision guard for Pavlik/DDH MCQs: require explicit pediatric-hip context.
            if has_pavlik_ddh_intent:
                if "pavlik" not in chunk_text_lower and "developmental dysplasia" not in chunk_text_lower and "ddh" not in chunk_text_lower:
                    continue
                if any(term in chunk_text_lower for term in PAVLIK_NOISE_TERMS):
                    continue
                # For Pavlik/DDH MCQs, require explicit complication/adverse-event semantics,
                # not broad DDH imaging or chapter-index text.
                if is_mcq and not any(
                    t in chunk_text_lower
                    for t in ("complication", "adverse", "nerve palsy", "osteonecrosis", "avascular necrosis")
                ):
                    continue
            if any(re.search(p, ch.content or "") for p in TOC_NOISE_PATTERNS):
                continue
            if is_hip_approach_comparison:
                # Require chunk to actually discuss approach terms for this comparison prompt.
                if not any(t in chunk_text_lower for t in comparison_terms):
                    continue
                # Must stay in hip/THA context, not knee/ankle anterolateral mentions.
                if "hip" not in chunk_text_lower:
                    continue
                if not any(k in chunk_text_lower for k in ("arthroplasty", "approach", "hardinge")):
                    continue
            # MCQ safety: require stronger overlap than generic lexical noise.
            min_mcq_overlap = 2 if mcq_pattern_query else 3
            if is_mcq and semantic_overlap < min_mcq_overlap:
                continue
            raw_candidates.append(
                {
                    "chunk": ch,
                    "chunk_tokens": toks,
                    "overlap_terms": overlap_terms,
                    "semantic_overlap": semantic_overlap,
                    "overlap_ratio": overlap_ratio,
                    "bm25": float(bm25),
                }
            )
            max_bm25 = max(max_bm25, float(bm25))

        if not raw_candidates:
            # Query-aware fallback: if a specific document was requested but has no relevant
            # matches, retry over all indexed docs for distinctive anchors.
            can_retry_global = selected_scope in {"document_specific", "document_fallback_global"}
            if can_retry_global:
                anchor_terms = sorted(
                    set(
                        [t for t in expanded_query_tokens if len(t) >= 4]
                        + [t for t in ("pavlik", "developmental", "dysplasia", "ddh", "arthroplasty") if t in query_text]
                    )
                )[:10]
                all_docs = db.query(Document).filter(Document.status == "indexed").all()
                all_doc_ids = [d.id for d in all_docs]
                if all_doc_ids:
                    fallback_chunks = (
                        db.query(DocumentChunk)
                        .filter(DocumentChunk.document_id.in_(all_doc_ids))
                        .order_by(DocumentChunk.document_id.asc(), DocumentChunk.chunk_index.asc())
                        .all()
                    )
                    fallback_tokenized = [_tokenize(ch.content) for ch in fallback_chunks]
                    f_df = Counter()
                    for toks in fallback_tokenized:
                        for term in set(toks):
                            f_df[term] += 1
                    f_avg_dl = sum(len(toks) for toks in fallback_tokenized) / max(len(fallback_tokenized), 1)
                    for ch, toks in zip(fallback_chunks, fallback_tokenized):
                        chunk_text_lower = (ch.content or "").lower()
                        if anchor_terms and not any(a in chunk_text_lower for a in anchor_terms):
                            continue
                        bm25 = self._bm25_score(expanded_query_tokens, toks, f_df, len(fallback_tokenized), f_avg_dl)
                        if bm25 <= 0:
                            continue
                        overlap_terms = set(query_tokens).intersection(set(toks))
                        overlap = len(overlap_terms)
                        semantic_overlap = self._mcq_semantic_overlap(expanded_query_tokens, toks) if is_mcq else overlap
                        min_mcq_overlap = 2 if mcq_pattern_query else 3
                        if is_mcq and semantic_overlap < min_mcq_overlap:
                            continue
                        overlap_ratio = overlap / max(len(query_token_set), 1)
                        raw_candidates.append(
                            {
                                "chunk": ch,
                                "chunk_tokens": toks,
                                "overlap_terms": overlap_terms,
                                "semantic_overlap": semantic_overlap,
                                "overlap_ratio": overlap_ratio,
                                "bm25": float(bm25),
                            }
                        )
                        max_bm25 = max(max_bm25, float(bm25))
                    if raw_candidates:
                        docs = all_docs
                        doc_ids = all_doc_ids
                        selected_scope = "query_anchor_global_fallback"
            if not raw_candidates:
                return {
                    "context": "",
                    "citations": [],
                    "retrieval": {
                        "strategy": "context_injection",
                        "source": "no_relevant_chunks",
                        "used_rag": False,
                        "requested_document_id": requested_document_id,
                        "scope": selected_scope,
                    },
                }

        scored = []
        for cand in raw_candidates:
            ch = cand["chunk"]
            toks = cand["chunk_tokens"]
            overlap_terms = cand["overlap_terms"]
            overlap_ratio = cand["overlap_ratio"]
            semantic_overlap = int(cand.get("semantic_overlap", len(overlap_terms)))
            chunk_text_lower = (ch.content or "").lower()
            bm25_norm = cand["bm25"] / max(max_bm25, 1e-9)
            coverage_ratio = len(expanded_query_token_set.intersection(set(toks))) / max(len(expanded_query_token_set), 1)
            phrase_score = self._phrase_overlap_score(query, ch.content or "")
            proximity = self._proximity_boost(query_tokens, toks)
            score = (0.58 * bm25_norm) + (0.22 * coverage_ratio) + (0.14 * phrase_score) + (0.06 * proximity)
            if is_mcq and semantic_overlap >= 4:
                score *= 1.08
            # Penalize chunks that likely contain question-bank stems/options noise.
            if is_mcq and re.search(r"\b(except|all of the following|1\)|2\)|3\)|4\)|a\)|b\)|c\)|d\))", chunk_text_lower):
                score *= 0.55
            if "total hip arthroplasty" in chunk_text_lower and has_total_hip_intent:
                score *= 1.25
            if is_comparison_query and comparison_terms:
                comp_hits = sum(1 for t in comparison_terms if t in chunk_text_lower)
                if comp_hits == 0:
                    score *= 0.72
                elif comp_hits == 2:
                    score *= 1.2
            if score >= max(self.min_relevance, 0.12):
                scored.append(
                    {
                        "score": float(score),
                        "overlap_ratio": float(overlap_ratio),
                        "overlap_terms": overlap_terms,
                        "chunk": ch,
                        "tokens_set": set(toks),
                    }
                )
        scored.sort(key=lambda x: x["score"], reverse=True)
        if not scored:
            return {"context": "", "citations": [], "retrieval": {"strategy": "context_injection", "source": "no_relevant_chunks", "used_rag": False}}
        scored = self._cross_encoder_rerank(query, scored)

        selected = self._mmr_select(scored, chunk_cap=chunk_cap, budget=budget)
        used_tokens = sum((s["chunk"].token_count or 0) for s in selected)

        docs_by_id = {d.id: d for d in docs}
        citations = []
        context_parts = []
        selected_chunks_meta = []
        avg_overlap_ratio = 0.0
        topical_hits = 0
        direct_hits = 0
        if selected:
            avg_overlap_ratio = sum(float(s["overlap_ratio"]) for s in selected) / len(selected)
        for sel in selected:
            score = sel["score"]
            overlap_ratio = sel["overlap_ratio"]
            overlap_terms = sel["overlap_terms"]
            chunk = sel["chunk"]
            doc = docs_by_id.get(chunk.document_id)
            title = doc.name if doc else "Document"
            content = chunk.content[:2400]
            chunk_text_lower = (chunk.content or "").lower()
            context_parts.append(f"[{title} | {chunk.section or 'General'} | {chunk.page_label or 'n/a'}]\n{content}")
            citations.append(
                {
                    "guideline": title,
                    "section": chunk.section or "General",
                    "page_range": chunk.page_label or "",
                    "evidence_strength": "moderate",
                    "reasoning": "Auto-ranked by relevance",
                    "content": content,
                    "text": content,
                    "snippet": content[:220] + ("..." if len(content) > 220 else ""),
                    "score": round(float(score), 4),
                    "overlap_ratio": round(float(overlap_ratio), 3),
                }
            )
            if is_comparison_query and comparison_terms:
                comp_hits = sum(1 for t in comparison_terms if t in chunk_text_lower)
                has_compare_connector = bool(re.search(r"\b(vs|versus|compared|comparison|than)\b", chunk_text_lower))
                has_hip_context = "hip" in chunk_text_lower and ("arthroplasty" in chunk_text_lower or "approach" in chunk_text_lower)
                match_type = "direct" if (comp_hits == len(comparison_terms) and has_compare_connector and has_hip_context) else "indirect"
            else:
                min_overlap_terms = 2 if len(query_token_set) >= 4 else 1
                is_direct = overlap_ratio >= 0.3 and len(overlap_terms) >= min_overlap_terms
                match_type = "direct" if is_direct else "indirect"
            citations[-1]["match_type"] = match_type
            if match_type == "direct":
                direct_hits += 1
            selected_chunks_meta.append(
                {
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "score": round(float(score), 4),
                    "token_count": chunk.token_count or 0,
                    "overlap_terms": sorted(list(overlap_terms))[:10],
                    "overlap_ratio": round(float(overlap_ratio), 3),
                }
            )
            if has_pavlik_ddh_intent:
                c_low = (chunk.content or "").lower()
                if "pavlik" in c_low or "developmental dysplasia" in c_low or "ddh" in c_low:
                    topical_hits += 1

        # Final precision gate: avoid labeling weak lexical collisions as grounded.
        exact_phrase_hits = sum(1 for c in citations if "total hip arthroplasty" in (c.get("content", "").lower()))
        low_quality = (avg_overlap_ratio < 0.16) and (exact_phrase_hits == 0)
        if has_pavlik_ddh_intent and topical_hits == 0:
            low_quality = True
        if low_quality:
            return {
                "context": "",
                "citations": [],
                "retrieval": {
                    "strategy": "context_injection",
                    "source": "low_quality_match_filtered",
                    "used_rag": False,
                    "document_id": document_id,
                    "token_budget": budget,
                    "tokens_used": used_tokens,
                    "avg_overlap_ratio": round(avg_overlap_ratio, 3),
                },
            }

        # Dedupe near-duplicate citations from mirrored source names/chunks.
        deduped_citations = []
        deduped_chunks = []
        seen = set()
        for c, m in zip(citations, selected_chunks_meta):
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

        return {
            "context": "\n\n".join(context_parts),
            "citations": deduped_citations,
            "retrieval": {
                "strategy": "context_injection",
                "source": "hybrid_document_chunks",
                "used_rag": bool(deduped_citations),
                "ranker": "hybrid_bm25_coverage_phrase_mmr",
                "rerank_enabled": bool(getattr(settings, "ENABLE_HYBRID_RERANK", False)),
                "rerank_model": settings.HYBRID_RERANK_MODEL if bool(getattr(settings, "ENABLE_HYBRID_RERANK", False)) else "",
                "requested_document_id": requested_document_id,
                "scope": selected_scope,
                "document_id": document_id,
                "citations_count": len(deduped_citations),
                "token_budget": budget,
                "tokens_used": used_tokens,
                "avg_overlap_ratio": round(avg_overlap_ratio, 3),
                "direct_hits": direct_hits,
                "indirect_hits": max(len(deduped_citations) - direct_hits, 0),
                "evidence_mode": "direct" if direct_hits > 0 else "indirect",
                "selected_chunks": deduped_chunks,
            },
        }

    def _resolve_document_file_path(self, doc: Document) -> Optional[Path]:
        file_key = doc.internal_id or doc.doc_id
        if not file_key:
            return None
        candidates = [
            self._uploads_dir / f"{file_key}.pdf",
            self._uploads_dir / f"{file_key}.docx",
            self._uploads_dir / f"{file_key}.txt",
            self._uploads_dir / f"{file_key}.md",
        ]
        for c in candidates:
            if c.exists():
                return c
        return None

    def _ensure_chunks_for_docs(self, db: Session, docs: List[Document]) -> None:
        built_count = 0
        for doc in docs:
            if built_count >= 2:
                break
            existing = db.query(DocumentChunk.id).filter(DocumentChunk.document_id == doc.id).first()
            if existing:
                continue
            file_path = self._resolve_document_file_path(doc)
            if not file_path:
                continue
            if file_path.stat().st_size > 40 * 1024 * 1024:
                doc.status = "error"
                db.commit()
                continue
            try:
                source_type = detect_source_type(file_path.name)
                chunks = parse_document_to_chunks(str(file_path), source_type)
                for ch in chunks:
                    db.add(
                        DocumentChunk(
                            document_id=doc.id,
                            chunk_index=ch["chunk_index"],
                            source_type=ch["source_type"],
                            section=ch.get("section"),
                            page_label=ch.get("page_label"),
                            content=ch["content"],
                            token_count=ch.get("token_count", 0),
                        )
                    )
                if chunks:
                    doc.status = "indexed"
                    built_count += 1
            except Exception:
                doc.status = "error"
            finally:
                db.commit()
