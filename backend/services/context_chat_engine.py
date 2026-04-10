# ============================================================
# BoneQuest v2 — Context Chat Engine (Unified Hybrid Retrieval)
# ============================================================

import json
import re
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal
from models.schemas import UserRole
from services.hybrid_retriever import HybridRetriever


SYSTEM_PROMPT = """You are BoneQuest AI, an orthopaedic clinical assistant.
Use only the provided document context as evidence for clinical claims.
If context is weak or missing, explicitly say that no strong document match was found.
Keep responses actionable, concise, and safe.

Output format requirements:
- Use these section headers in order:
  1) 📋 CLINICAL RECOMMENDATION
  2) 🔬 GUIDELINE EVIDENCE
  3) 💡 CLINICAL REASONING
  4) ⚠️ CONSIDERATIONS
  5) 🎯 KEY TAKEAWAY
- In GUIDELINE EVIDENCE, distinguish direct evidence vs indirect mention.
- Never claim a direct comparison unless the retrieved context explicitly compares both options.
- If evidence is indirect, state that limitation plainly and avoid strong wording."""

UNGROUNDED_PROMPT = """You are BoneQuest AI.
No strong document-grounded context is available for this query.
Do not provide clinical recommendations without supporting document evidence.
Ask for the exact protocol/chapter if evidence is insufficient."""


class ContextChatEngine:
    def __init__(self) -> None:
        self.retriever = HybridRetriever()
        self.groq_client = None
        self.anthropic_client = None
        self._async_anthropic_client = None
        self._init_clients()

    def _init_clients(self) -> None:
        try:
            from groq import Groq
            if settings.GROQ_API_KEY:
                self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
        except Exception:
            self.groq_client = None
        try:
            from anthropic import Anthropic  # type: ignore
            if settings.CLAUDE_API_KEY:
                self.anthropic_client = Anthropic(api_key=settings.CLAUDE_API_KEY)
        except Exception:
            self.anthropic_client = None
        # Async client for non-blocking calls in async handlers
        try:
            from anthropic import AsyncAnthropic  # type: ignore
            if settings.CLAUDE_API_KEY:
                self._async_anthropic_client = AsyncAnthropic(api_key=settings.CLAUDE_API_KEY)
        except Exception:
            self._async_anthropic_client = None

    async def generate_response_stream(
        self,
        db: Optional[Session],
        query: str,
        role: UserRole,
        document_id: Optional[str] = None,
        history: Optional[List[dict]] = None,
        max_context_tokens: Optional[int] = None,
        max_context_chunks: Optional[int] = None,
    ) -> AsyncGenerator[dict, None]:
        history = history or []
        created_db = False
        if db is None:
            db = SessionLocal()
            created_db = True
        try:
            package = self.retriever.build_context_package(
                db=db,
                query=query,
                document_id=document_id,
                token_budget=max_context_tokens,
                max_chunks=max_context_chunks,
            )
        finally:
            if created_db:
                db.close()
        context = package.get("context", "")
        citations = package.get("citations", [])
        retrieval = package.get("retrieval", {})
        is_mcq = bool(self._is_mcq_query(query))

        # Quality gate: check if evidence is relevant enough
        avg_overlap_ratio = float(retrieval.get("avg_overlap_ratio", 0.0) or 0.0)
        direct_hits = int(retrieval.get("direct_hits", 0) or 0)
        weak_match = bool(citations) and avg_overlap_ratio < 0.12 and direct_hits == 0

        if weak_match:
            citations = []
            context = ""
            retrieval = dict(retrieval or {})
            retrieval["source"] = "weak_match_downgraded"
            retrieval["used_rag"] = False

        thinking_lines = [
            "Classifying query and retrieval strategy.",
            f"Searching uploaded library with budgeted context (max chunks: {max_context_chunks or settings.MAX_CONTEXT_CHUNKS}).",
            f"Retrieved {len(citations)} evidence chunks.",
        ]
        if not citations:
            thinking_lines.append("No strong evidence found; applying fallback safety behavior.")
        for line in thinking_lines:
            yield {"type": "thinking", "data": line}

        trace_steps = [
            {"action": "Query Analysis", "detail": "Interpreted intent and scope of the question."},
            {"action": "Context Retrieval", "detail": f"Selected {len(citations)} chunks from uploaded documents."},
        ]
        if not citations:
            trace_steps.append({"action": "Fallback Routing", "detail": "Insufficient evidence; switched to safe fallback mode."})
        for step in trace_steps:
            yield {"type": "trace", "data": json.dumps(step)}

        # Hard guardrail for MCQs: never guess when evidence is weak/absent
        if is_mcq and not citations:
            mcq_hint = self._build_mcq_non_grounded_hint(query)
            answer = (
                "📋 CLINICAL RECOMMENDATION\n"
                "I cannot verify this MCQ from retrieved uploaded-document evidence.\n\n"
                "🔬 GUIDELINE EVIDENCE\n"
                "No strong matching citation was retrieved for this question.\n\n"
                "💡 CLINICAL REASONING\n"
                f"{mcq_hint}\n\n"
                "⚠️ CONSIDERATIONS\n"
                "This is non-grounded best-effort reasoning and may be incorrect. Please verify against the source chapter.\n\n"
                "🎯 KEY TAKEAWAY\n"
                "Upload or reference the exact guideline section to get a fully grounded answer."
            )
            for chunk in self._iter_stream_chunks(answer):
                yield {"type": "token", "data": chunk}
            confidence = 0.28
            yield {"type": "thinking_done", "data": ""}
            yield {"type": "confidence", "data": str(confidence)}
            yield {
                "type": "final_payload",
                "data": {
                    "id": f"q-{uuid.uuid4().hex[:8]}",
                    "answer": answer,
                    "citations": [],
                    "confidence": confidence,
                    "trace": [],
                    "model": "fallback",
                    "intent": "clinical",
                    "retrieval": retrieval,
                },
            }
            yield {"type": "done", "data": "[DONE]"}
            return

        mcq_options = self._extract_mcq_options(query) if is_mcq else []
        if is_mcq and citations:
            mcq_eval = self._evaluate_mcq_options(query, mcq_options, citations)
            if mcq_eval:
                yield {"type": "mcq_analysis", "data": json.dumps(mcq_eval)}
                if mcq_eval.get("mcq_type") == "MCQ-except":
                    selected = mcq_eval.get("selected_option")
                    if selected:
                        yield {"type": "citation", "data": json.dumps(citations)}
                        checks = mcq_eval.get("option_checks", []) or []
                        rationale = "Option-level support scoring identified this choice as the EXCEPT outlier."
                        for ch in checks:
                            opt = str(ch.get("option", ""))
                            if opt == selected:
                                rationale = f"Option-level support score is lowest for '{selected}', making it the EXCEPT choice."
                                break
                        deterministic_answer = (
                            "📋 CLINICAL RECOMMENDATION\n"
                            f"{selected} is the most likely EXCEPT option.\n\n"
                            "🔬 GUIDELINE EVIDENCE\n"
                            "Retrieved evidence contains partial/indirect support; option-level verifier selected the lowest-supported outlier.\n\n"
                            "💡 CLINICAL REASONING\n"
                            f"{rationale}\n\n"
                            "⚠️ CONSIDERATIONS\n"
                            "This is an option-level determination from retrieved evidence and may still require chapter-level verification.\n\n"
                            "🎯 KEY TAKEAWAY\n"
                            f"Selected EXCEPT answer: {selected}."
                        )
                        for chunk in self._iter_stream_chunks(deterministic_answer):
                            yield {"type": "token", "data": chunk}
                        retrieval = dict(retrieval or {})
                        retrieval["option_level_selected"] = selected
                        retrieval["option_level_uncertain"] = False
                        retrieval["used_rag"] = bool(citations)
                        yield {"type": "thinking_done", "data": ""}
                        yield {"type": "confidence", "data": str(0.74)}
                        yield {
                            "type": "final_payload",
                            "data": {
                                "id": f"q-{uuid.uuid4().hex[:8]}",
                                "answer": deterministic_answer,
                                "citations": citations,
                                "confidence": 0.74,
                                "trace": [],
                                "model": "option_verifier",
                                "intent": "clinical",
                                "retrieval": retrieval,
                            },
                        }
                        yield {"type": "done", "data": "[DONE]"}
                        return
                    if not selected:
                        yield {"type": "citation", "data": json.dumps(citations)}
                        safe_answer = (
                            "I found partial evidence, but not enough option-level support to safely choose an EXCEPT answer.\n\n"
                            "Please provide the exact source chapter or a cleaner excerpt containing the option statements."
                        )
                        for chunk in self._iter_stream_chunks(safe_answer):
                            yield {"type": "token", "data": chunk}
                        yield {"type": "thinking_done", "data": ""}
                        retrieval = dict(retrieval or {})
                        retrieval["option_level_uncertain"] = True
                        retrieval["used_rag"] = bool(citations)
                        yield {"type": "confidence", "data": str(0.46)}
                        yield {
                            "type": "final_payload",
                            "data": {
                                "id": f"q-{uuid.uuid4().hex[:8]}",
                                "answer": safe_answer,
                                "citations": citations,
                                "confidence": 0.46,
                                "trace": [],
                                "model": "option_verifier",
                                "intent": "clinical",
                                "retrieval": retrieval,
                            },
                        }
                        yield {"type": "done", "data": "[DONE]"}
                        return

        if citations:
            yield {"type": "citation", "data": json.dumps(citations)}

        is_comparison_query = self._is_comparison_query(query)
        if is_comparison_query and direct_hits <= 0:
            safe_answer = (
                "📋 CLINICAL RECOMMENDATION\n"
                "I cannot provide a direct preference because the retrieved evidence is indirect for this head-to-head comparison.\n\n"
                "🔬 GUIDELINE EVIDENCE\n"
                "The available citations discuss related approach details, but do not explicitly compare both requested options.\n\n"
                "💡 CLINICAL REASONING\n"
                "A safe comparison requires explicit side-by-side evidence in the uploaded sources.\n\n"
                "⚠️ CONSIDERATIONS\n"
                "Please provide the exact chapter or protocol section that directly compares these approaches.\n\n"
                "🎯 KEY TAKEAWAY\n"
                "No direct comparative evidence was retrieved, so a recommendation is withheld."
            )
            for chunk in self._iter_stream_chunks(safe_answer):
                yield {"type": "token", "data": chunk}
            confidence = 0.42
            yield {"type": "thinking_done", "data": ""}
            yield {"type": "confidence", "data": str(confidence)}
            yield {
                "type": "final_payload",
                "data": {
                    "id": f"q-{uuid.uuid4().hex[:8]}",
                    "answer": safe_answer,
                    "citations": citations,
                    "confidence": confidence,
                    "trace": [],
                    "model": "policy_gate",
                    "intent": "clinical",
                    "retrieval": retrieval,
                },
            }
            yield {"type": "done", "data": "[DONE]"}
            return

        if citations:
            system_prompt = f"{SYSTEM_PROMPT}\n\nRole: {role.value}\n\nContext:\n{context}"
        else:
            system_prompt = f"{UNGROUNDED_PROMPT}\n\nRole: {role.value}"
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history[-6:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": query})

        answer = ""
        model_used = "fallback"
        try:
            if self._async_anthropic_client:
                # Non-blocking async Claude call
                model_used = settings.CLAUDE_MODEL
                text = await self._call_claude_async(messages)
                for chunk in self._iter_stream_chunks(text):
                    answer += chunk
                    yield {"type": "token", "data": chunk}
            elif self.anthropic_client:
                # Fallback to sync if async not available
                model_used = settings.CLAUDE_MODEL
                text = self._call_claude(messages)
                for chunk in self._iter_stream_chunks(text):
                    answer += chunk
                    yield {"type": "token", "data": chunk}
            elif self.groq_client:
                model_used = settings.GROQ_TEXT_MODEL
                stream = self.groq_client.chat.completions.create(
                    messages=messages,
                    model=settings.GROQ_TEXT_MODEL,
                    temperature=0.3,
                    max_tokens=1500,
                    stream=True,
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta.content or ""
                    if delta:
                        answer += delta
                        yield {"type": "token", "data": delta}
            else:
                answer = "No model provider is configured. Please set CLAUDE_API_KEY or GROQ_API_KEY."
                yield {"type": "token", "data": answer}
        except Exception as e:
            if not answer:
                answer = "I could not complete the request right now due to a model provider error. Please retry."
            yield {"type": "error", "data": str(e)}

        answer = answer.strip()
        if not answer:
            answer = "No response was generated."

        support_ratio = 1.0
        if citations:
            answer, support_ratio = self._enforce_supported_claims(answer, citations)
            answer = self._normalize_structured_output(answer, citations=True)
        else:
            answer = (
                "📋 CLINICAL RECOMMENDATION\n"
                "I cannot provide a clinical recommendation because no strong supporting evidence was retrieved from uploaded documents.\n\n"
                "🔬 GUIDELINE EVIDENCE\n"
                "No relevant guideline excerpt was retrieved for this query.\n\n"
                "💡 CLINICAL REASONING\n"
                "To avoid unsafe or hallucinated guidance, I only provide clinical recommendations when evidence is available.\n\n"
                "⚠️ CONSIDERATIONS\n"
                "Upload or reference the exact protocol/chapter section and I will re-evaluate.\n\n"
                "🎯 KEY TAKEAWAY\n"
                "Insufficient evidence in the current library for a safe answer."
            )
            answer = self._normalize_structured_output(answer, citations=False)

        if citations:
            scores = [float(c.get("score", 0.0)) for c in citations if isinstance(c, dict)]
            avg_score = (sum(scores) / len(scores)) if scores else 0.0
            avg_overlap_ratio = float(retrieval.get("avg_overlap_ratio", 0.0) or 0.0)
            score_boost = min(max(avg_score / 10.0, 0.0), 0.2)
            overlap_boost = min(max(avg_overlap_ratio, 0.0), 0.22)
            confidence = round(min(0.88, 0.5 + (0.05 * min(len(citations), 5)) + score_boost + overlap_boost), 2)
            if retrieval.get("evidence_mode") == "indirect":
                confidence = min(confidence, 0.62)
            confidence = min(confidence, round(0.35 + (0.53 * support_ratio), 2))
            retrieval = dict(retrieval or {})
            retrieval["support_ratio"] = round(float(support_ratio), 3)
        else:
            confidence = 0.35
        yield {"type": "thinking_done", "data": ""}
        yield {"type": "confidence", "data": str(confidence)}
        yield {
            "type": "final_payload",
            "data": {
                "id": f"q-{uuid.uuid4().hex[:8]}",
                "answer": answer,
                "citations": citations,
                "confidence": confidence,
                "trace": [],
                "model": model_used,
                "intent": "clinical",
                "retrieval": retrieval,
            },
        }
        yield {"type": "done", "data": "[DONE]"}

    def _is_mcq_query(self, query: str) -> bool:
        q = (query or "").lower()
        return bool(
            re.search(
                r"\bexcept\b|\bmost likely\b|\bbest next step\b|\ball of the following\b|\bwhich of the following\b|\bincorrect\b|\bfalse\b|\btrue\b|\b[1-9]\)|\b[a-d]\)",
                q,
            )
        )

    def _is_comparison_query(self, query: str) -> bool:
        q = (query or "").lower()
        return bool(re.search(r"\b(compare|comparison|versus| vs )\b", q))

    def _extract_mcq_options(self, query: str) -> List[str]:
        opts: List[str] = []
        for line in (query or "").splitlines():
            s = line.strip()
            if re.match(r"^([a-eA-E]|\d{1,2})[\)\.\-:]\s+.+", s):
                opts.append(s)
        if not opts:
            inline = re.findall(r"(\d\)\s*[^0-9]+)(?=(?:\d\)|$))", query or "")
            opts = [o.strip() for o in inline if o.strip()]
        if not opts:
            q = (query or "").strip()
            lower_q = q.lower()
            stem_markers = ("which of the following", "all of the following", "incorrect", "except", "false", "true")
            if any(m in lower_q for m in stem_markers):
                split_point = -1
                for ch in ("?", ":"):
                    idx = q.find(ch)
                    if idx != -1:
                        split_point = idx
                        break
                tail = q[split_point + 1:] if split_point != -1 else q
                parts = [p.strip(" \t\r\n-•;") for p in re.split(r"\.\s+|;\s+", tail) if p.strip()]
                parts = [p for p in parts if len(p) >= 18]
                if len(parts) >= 2:
                    opts = [f"{i+1}) {p}" for i, p in enumerate(parts[:8])]
        return opts[:8]

    def _build_mcq_non_grounded_hint(self, query: str) -> str:
        options = self._extract_mcq_options(query)
        if not options:
            return "I cannot infer a likely option safely without source evidence."
        try:
            if self.anthropic_client:
                prompt = (
                    "This is an orthopaedic MCQ without source evidence. "
                    "Give one line only: 'Best-effort likely option: <option text>'. "
                    "Then one short sentence: 'Reason (non-grounded): ...'. "
                    "Do not claim certainty."
                )
                text = self._call_claude(
                    [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": query},
                    ]
                )
                return text.strip() or "I cannot infer a likely option safely without source evidence."
        except Exception:
            pass
        return "I cannot infer a likely option safely without source evidence."

    def _evaluate_mcq_options(self, query: str, options: List[str], citations: List[dict]) -> Optional[Dict[str, Any]]:
        if not options:
            return None
        ctx = " ".join([(c.get("content") or c.get("text") or "") for c in citations]).lower()
        checks = []
        support_scores = []
        for opt in options:
            cleaned = re.sub(r"^([a-eA-E]|\d{1,2})[\)\.\-:]\s*", "", opt).strip().lower()
            tokens = [t for t in re.findall(r"[a-zA-Z][a-zA-Z0-9\-]{2,}", cleaned) if t not in {"following", "complications", "treatment"}]
            if not tokens:
                score = 0
            else:
                score = sum(1 for t in set(tokens) if t in ctx)
            support_scores.append(score)
            checks.append({"option": opt, "support_score": score})

        q = (query or "").lower()
        is_except_style = bool(re.search(r"\bexcept\b|\bincorrect\b|\bfalse\b|\bnot true\b", q))
        mcq_type = "MCQ-except" if is_except_style else "MCQ"
        selected = None
        if mcq_type == "MCQ-except" and len(support_scores) >= 2:
            sorted_scores = sorted(support_scores)
            if sorted_scores[0] + 2 <= sorted_scores[1]:
                min_idx = support_scores.index(sorted_scores[0])
                selected = options[min_idx]
            if not selected:
                absolute_cues = ("safely", "without an adverse effect", "without adverse effect", "always", "never", "must")
                cue_hits = []
                for i, opt in enumerate(options):
                    ol = opt.lower()
                    hits = sum(1 for c in absolute_cues if c in ol)
                    cue_hits.append((hits, i))
                cue_hits.sort(reverse=True)
                if cue_hits and cue_hits[0][0] >= 1:
                    selected = options[cue_hits[0][1]]
            if not selected:
                selected = self._llm_mcq_option_tiebreak(query, options, citations, mcq_type=mcq_type)

        return {
            "detected": True,
            "mcq_type": mcq_type,
            "options": options,
            "option_checks": checks,
            "selected_option": selected,
        }

    def _llm_mcq_option_tiebreak(
        self, query: str, options: List[str], citations: List[dict], mcq_type: str = "MCQ",
    ) -> Optional[str]:
        if not options or not citations:
            return None
        evidence_lines = []
        for i, c in enumerate(citations[:6], start=1):
            txt = (c.get("content") or c.get("text") or "")[:700]
            sec = c.get("section") or "General"
            evidence_lines.append(f"[{i}] {sec}: {txt}")
        evidence_blob = "\n".join(evidence_lines)
        options_blob = "\n".join([f"- {o}" for o in options])
        task = "choose the EXCEPT/incorrect option (least supported / contradicted by evidence)" if mcq_type == "MCQ-except" else "choose the best-supported option"
        prompt = (
            "You are an orthopedic MCQ verifier.\n"
            f"Task: {task}.\n"
            "Use ONLY the provided evidence snippets. Do not use outside knowledge.\n"
            'Return strict JSON: {"selected_option": "<exact option text or empty>", "confidence": 0.0-1.0, "reason": "..."}\n\n'
            f"Question:\n{query}\n\n"
            f"Options:\n{options_blob}\n\n"
            f"Evidence:\n{evidence_blob}\n"
        )
        try:
            if self.groq_client:
                resp = self.groq_client.chat.completions.create(
                    model=settings.GROQ_SMALL_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    response_format={"type": "json_object"},
                )
                payload = json.loads(resp.choices[0].message.content or "{}")
                chosen = str(payload.get("selected_option") or "").strip()
                conf = float(payload.get("confidence", 0.0) or 0.0)
                if not chosen or conf < 0.45:
                    return None
                for o in options:
                    if chosen == o:
                        return o
                norm = lambda s: re.sub(r"\s+", " ", re.sub(r"^([a-eA-E]|\d{1,2})[\)\.\-:]\s*", "", (s or "").lower())).strip(" .")
                chosen_n = norm(chosen)
                for o in options:
                    on = norm(o)
                    if chosen_n and (chosen_n == on or chosen_n in on or on in chosen_n):
                        return o
                return None
        except Exception:
            return None
        return None

    def _enforce_supported_claims(self, answer: str, citations: List[dict]) -> tuple[str, float]:
        if not answer:
            return answer, 0.0
        evidence_text = " ".join([(c.get("content") or c.get("text") or "") for c in citations]).lower()
        lines = [ln for ln in answer.split("\n") if ln.strip()]
        if len(lines) < 3:
            return answer, 1.0
        supported = []
        checkable_count = 0
        unsupported_count = 0
        for ln in lines:
            probe = ln.strip()
            if probe.startswith(("📋", "🔬", "💡", "⚠️", "🎯")):
                supported.append(ln)
                continue
            toks = re.findall(r"[a-zA-Z][a-zA-Z0-9\-]{3,}", probe.lower())
            significant = [t for t in toks if t not in {"clinical", "guideline", "evidence", "approach", "patient", "treatment"}]
            hits = sum(1 for t in set(significant[:10]) if t in evidence_text)
            if significant:
                checkable_count += 1
            if significant and hits == 0:
                unsupported_count += 1
                continue
            supported.append(ln)
        support_ratio = 1.0
        if checkable_count > 0:
            support_ratio = max(0.0, min(1.0, (checkable_count - unsupported_count) / checkable_count))
        if unsupported_count == 0:
            return answer, support_ratio
        supported.append("")
        supported.append("⚠️ Note: Some unsupported statements were removed because they were not verifiable in retrieved evidence.")
        return "\n".join(supported), support_ratio

    def _normalize_structured_output(self, answer: str, citations: bool) -> str:
        text = (answer or "").strip()
        needed = ["📋", "🔬", "💡", "⚠️", "🎯"]
        if all(h in text for h in needed):
            return text
        if any(h in text for h in needed):
            return text
        if citations:
            return (
                "📋 CLINICAL RECOMMENDATION\n"
                f"{text}\n\n"
                "🔬 GUIDELINE EVIDENCE\n"
                "Evidence was retrieved and used for this response.\n\n"
                "💡 CLINICAL REASONING\n"
                "Reasoning was constrained to retrieved content.\n\n"
                "⚠️ CONSIDERATIONS\n"
                "Interpret findings within local protocol context.\n\n"
                "🎯 KEY TAKEAWAY\n"
                "Use cited evidence as primary reference."
            )
        return (
            "📋 CLINICAL RECOMMENDATION\n"
            "No safe recommendation can be issued from current retrieved evidence.\n\n"
            "🔬 GUIDELINE EVIDENCE\n"
            "No strong matching citation was retrieved.\n\n"
            "💡 CLINICAL REASONING\n"
            "To avoid hallucinations, guidance is withheld without evidence.\n\n"
            "⚠️ CONSIDERATIONS\n"
            "Upload or point to the exact chapter/protocol and retry.\n\n"
            "🎯 KEY TAKEAWAY\n"
            "Insufficient evidence for a safe, grounded answer."
        )

    def _iter_stream_chunks(self, text: str) -> List[str]:
        parts = re.findall(r".{1,120}(?:\s+|$)", text or "", flags=re.S)
        return parts or ([text] if text else [])

    def _call_claude(self, messages: List[Dict[str, str]]) -> str:
        """Synchronous Claude call (fallback)."""
        if not self.anthropic_client:
            raise RuntimeError("Claude client not configured")
        system_text = ""
        user_msgs: List[Dict[str, str]] = []
        for m in messages:
            if m["role"] == "system":
                system_text = m["content"]
            elif m["role"] in {"user", "assistant"}:
                user_msgs.append({"role": m["role"], "content": m["content"]})

        resp = self.anthropic_client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=1500,
            temperature=0.2,
            system=system_text,
            messages=user_msgs,
        )
        parts = []
        for block in resp.content:
            t = getattr(block, "text", None)
            if t:
                parts.append(t)
        return "".join(parts).strip()

    async def _call_claude_async(self, messages: List[Dict[str, str]]) -> str:
        """Non-blocking async Claude call — prevents event loop blocking under concurrency."""
        if not self._async_anthropic_client:
            # Fallback to sync if async not available
            return self._call_claude(messages)
        system_text = ""
        user_msgs: List[Dict[str, str]] = []
        for m in messages:
            if m["role"] == "system":
                system_text = m["content"]
            elif m["role"] in {"user", "assistant"}:
                user_msgs.append({"role": m["role"], "content": m["content"]})

        resp = await self._async_anthropic_client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=1500,
            temperature=0.2,
            system=system_text,
            messages=user_msgs,
        )
        parts = []
        for block in resp.content:
            t = getattr(block, "text", None)
            if t:
                parts.append(t)
        return "".join(parts).strip()
