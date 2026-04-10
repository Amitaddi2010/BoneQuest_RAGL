# ============================================================
# BoneQuest v2 — PageIndex Engine (Modular Intent-Driven Pipeline)
# ============================================================

import os
import uuid
import json
import re
from typing import List, Optional, AsyncGenerator, Dict, Any, Tuple
from pydantic import BaseModel
from models.schemas import QueryResponse, TraceStep, UserRole, Citation
from config import settings
from services.hybrid_retriever import HybridRetriever
from database import SessionLocal

GROQ_API_KEY = settings.GROQ_API_KEY
GROQ_MODEL   = settings.GROQ_TEXT_MODEL
PAGEINDEX_API_KEY = settings.PAGEINDEX_API_KEY
GROQ_SMALL_MODEL = getattr(settings, "GROQ_SMALL_MODEL", "") or GROQ_MODEL
USE_PAGEINDEX_CLOUD = os.getenv("USE_PAGEINDEX_CLOUD", "false").lower() == "true"

# Optional PageIndex client (real retrieval over indexed documents)
pi_client = None
try:
    from pageindex.client import PageIndexClient  # type: ignore
    if PAGEINDEX_API_KEY and USE_PAGEINDEX_CLOUD:
        pi_client = PageIndexClient(api_key=PAGEINDEX_API_KEY)
except Exception:
    pi_client = None


# ── Prompts ────────────────────────────────────────────────

INTENT_CLASSIFIER_PROMPT = """Analyze the user query and prior context (if any) and classify the intent into EXACTLY one of the following four labels:
- "greeting": basic salutations, casual chat (e.g., "hi", "how are you", "thanks")
- "meta": instructions about the AI, capabilities, testing, multiple choice questions, or providing feedback/corrections (e.g., "but the correct answer is", "test you", "ignore previous")
- "follow_up": an ambiguous reference or short continuation of previous clinical context (e.g., "why?", "what about diabetes?", "what dosage?")
- "clinical": direct medical question, symptom description, clinical protocol request

Rules:
1. If the user is giving you a test, a multiple-choice question, or correcting your previous answer (e.g., "but the correct ans is..."), classify it as "meta" or "follow_up". Do NOT classify as "clinical" to avoid massive headers.
2. Return ONLY a JSON object with a single key "intent". Example: {"intent": "clinical"}"""

PROMPT_GREETING = """You are BoneQuest AI, a friendly orthopaedic clinical assistant.
The user is greeting you or chatting casually.
Respond warmly, concisely, and professionally. Do NOT include clinical warnings or strict headers."""

PROMPT_META = """You are BoneQuest AI, an advanced orthopaedic clinical decision support system.
The user is asking about your capabilities, testing you, or giving meta-instructions.
Answer clearly and concisely.
If the query is an MCQ and evidence is not explicitly available in retrieved context, say you cannot verify and ask for source/reference.
Do NOT hallucinate medical protocols and do NOT use strict clinical headers."""

PROMPT_CLINICAL = """You are BoneQuest AI, an expert orthopaedic clinical assistant serving a {role}.
Based on the following orthopaedic clinical protocol sections retrieved via PageIndex tree navigation:
---
{context}
---

Provide a comprehensive, well-structured answer using EXACTLY these section headers (each on its own line):

📋 CLINICAL RECOMMENDATION
[Direct answer — what to do]

🔬 GUIDELINE EVIDENCE
[What the protocol says, cite page numbers exactly. DO NOT hallucinate evidence.]

💡 CLINICAL REASONING
[Why this recommendation makes sense]

⚠️ CONSIDERATIONS
[Special factors, contraindications, comorbidities]

🎯 KEY TAKEAWAY
[Single most important sentence]

Critical constraints:
- Use ONLY retrieved context as evidence.
- If context does not directly support a specific claim, explicitly state that evidence is insufficient.
- Never give high-certainty language when evidence is missing or indirect."""

PROMPT_FOLLOW_UP = """You are BoneQuest AI. The user is asking a follow-up question related to the prior context.
---
Retrieved protocol context (if newly relevant):
{context}
---
Answer the follow-up question directly and concisely without repeating the full multi-section clinical headers unless specifically necessary. Focus on accuracy and cite guidelines if providing new protocol data. Do NOT hallucinate sources."""

THINKING_PROMPT = """You are an expert orthopaedic clinical AI. Think through the following clinical query step by step.
Keep each step SHORT (one sentence). Output exactly 5 numbered steps covering:
1. What is the core clinical question?
2. What patient factors or comorbidities matter?
3. Which guideline sections are relevant?
4. What are the key treatment options?
5. How confident are you and why?"""

STRUCTURED_REASONING_POLICY = """
You are BoneQuest, a clinical orthopedic decision support assistant.

BEFORE answering ANY question, you MUST follow this exact reasoning chain:

STEP 1 - CLASSIFY: What type of question is this?
- Types: [complication | diagnosis | treatment | anatomy | pharmacology | MCQ-except | MCQ-most-likely | MCQ-best-next-step]

STEP 2 - IDENTIFY: Extract key clinical entities
- Condition, patient factors, age, comorbidities, fracture type, implant.

STEP 3 - RETRIEVE: What guideline/source covers this?
- Name the specific guideline and section/recommendation from retrieved context.

STEP 4 - VERIFY EACH OPTION (for MCQ questions only):
- For EXCEPT questions: evaluate ALL options independently as TRUE or FALSE.
- The correct answer to an EXCEPT question = the FALSE statement.

STEP 5 - VALIDATE: Does your answer contradict any retrieved guideline?
- If yes, revise or explicitly flag contradiction risk.
- If no guideline covers this, state "No strong guideline evidence".

STEP 6 - CONFIDENCE: Assign based on evidence grade:
- Strong guideline evidence = 85-95%
- Moderate evidence = 70-84%
- Limited/consensus evidence = 50-69%
- No guideline found = 30-49%
- Never assign >95% unless multiple strong sources agree.

OUTPUT FORMAT:
1) "REASONING STEPS" with Step 1 through Step 6.
2) "FINAL ANSWER".
"""

VALIDATION_PROMPT = """You are a strict orthopedic answer validator.
You validate an existing model answer against the retrieved context.

Return ONLY JSON with keys:
- contradiction: boolean
- evidence_level: one of ["strong", "moderate", "limited", "none"]
- suggested_confidence: integer 30-95
- rationale: short string

For MCQ input, also include:
- option_checks: array of objects [{ "option": "...", "label": "true|false|uncertain", "why": "..." }]
"""


class PageIndexEngine:
    def __init__(self):
        self.groq_client = None
        self.hybrid_retriever = HybridRetriever()
        self._init_groq()

    def _init_groq(self):
        try:
            from groq import Groq
            self.groq_client = Groq(api_key=GROQ_API_KEY)
        except ImportError:
            pass
        except Exception:
            pass

    def _can_use_pageindex(self, document_id: str) -> bool:
        if not pi_client:
            return False
        if not document_id or document_id == "doc-1":
            return False
        try:
            return bool(pi_client.is_retrieval_ready(document_id))
        except Exception:
            return True

    async def _retrieve_hybrid_context(
        self, query: str, document_id: str, intent: str
    ) -> Tuple[str, List[dict], Dict[str, Any]]:
        """
        Unified hybrid retrieval using HybridRetriever.
        Uses BM25 + semantic embeddings + RRF fusion.
        """
        db = SessionLocal()
        try:
            package = self.hybrid_retriever.build_context_package(
                db=db,
                query=query,
                document_id=document_id,
            )
            context = package.get("context", "")
            citations = package.get("citations", [])
            retrieval_meta = package.get("retrieval", {
                "strategy": "hybrid",
                "source": "none",
                "document_id": document_id,
                "used_rag": False,
            })
            return context, citations, retrieval_meta
        except Exception as e:
            print(f"[Engine] Hybrid retrieval failed: {e}")
            return "", [], {
                "strategy": "hybrid",
                "source": "error",
                "document_id": document_id,
                "used_rag": False,
                "error": str(e),
            }
        finally:
            db.close()

    async def _pageindex_stream_answer_and_citations(
        self,
        messages: List[dict],
        document_id: str,
    ) -> AsyncGenerator[dict, None]:
        """
        Uses PageIndex indexed documents to stream tokens and capture citations.
        Emits our standard event format: token/citation.
        """
        citations_payload: List[dict] = []
        answer_full = ""
        try:
            stream_iter = pi_client.chat_completions(
                messages=messages,
                doc_id=document_id,
                stream=True,
                stream_metadata=True,
                enable_citations=True,
            )
            for chunk in stream_iter:
                # Citations metadata chunk
                if chunk.get("object") == "chat.completion.citations":
                    raw = chunk.get("citations", []) or []
                    citations_payload = []
                    for ref in raw:
                        title = ref.get("title") or ref.get("guideline") or "Indexed Document"
                        text = ref.get("text") or ref.get("content") or ""
                        citations_payload.append({
                            "guideline": title,
                            "section": ref.get("section") or title,
                            "page_range": ref.get("page_range") or ref.get("pages") or "",
                            "evidence_strength": ref.get("evidence_strength") or "moderate",
                            "reasoning": "Retrieved from indexed document",
                            "content": text,
                            "text": text,
                            "snippet": (text[:100] + "...") if len(text) > 100 else text,
                            "matched_keywords": [],
                        })
                    if citations_payload:
                        yield {"type": "citation", "data": json.dumps(citations_payload)}
                else:
                    # Token chunk
                    content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if content:
                        answer_full += content
                        yield {"type": "token", "data": content}
        except Exception as e:
            yield {"type": "error", "data": str(e)}

        yield {"type": "_pageindex_done", "data": json.dumps({"answer": answer_full, "citations": citations_payload})}

    # ── Pipeline Components ────────────────────────────────────

    async def classify_intent(self, query: str, history: List[dict] = None) -> str:
        """Classify user intent using Groq JSON mode or fallback heuristics."""
        default_intent = "clinical"
        if not self.groq_client:
            return self._heuristic_intent(query)
            
        history = history or []
        # Keep only last 3 messages for context in classification
        ctx_messages = history[-3:] if len(history) >= 3 else history
        ctx_string = " | ".join([f"{m['role']}: {m['content']}" for m in ctx_messages])
        
        user_msg = f"History: {ctx_string}\nQuery: {query}"
        
        try:
            completion = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": INTENT_CLASSIFIER_PROMPT},
                    {"role": "user", "content": user_msg}
                ],
                model=GROQ_SMALL_MODEL,
                response_format={"type": "json_object"},
                temperature=0.0
            )
            data = json.loads(completion.choices[0].message.content)
            intent = data.get("intent", "clinical").lower()
            return intent if intent in ["greeting", "meta", "clinical", "follow_up"] else "clinical"
        except Exception as e:
            print(f"Intent classification failed: {e}. Using fallback.")
            return self._heuristic_intent(query)

    def _heuristic_intent(self, query: str) -> str:
        q = query.lower().strip()
        greetings = {'hi', 'hello', 'hey', 'how are you', 'howdy', 'thanks', 'ok', 'okay'}
        if q in greetings: return "greeting"
        
        meta = ['test you', 'ask you', 'what can you', 'who created', 'testing you', 'help me understand', 'some questions', 'correct ans', 'correct answer', 'is incorrect', 'you are wrong']
        if any(m in q for m in meta): return "meta"
        
        # Detect multiple choice questions based on typical format "1)", "2)", "a)", "b)", "except:"
        if "except:" in q or "1)" in q or "a)" in q:
            return "meta"
            
        if len(q.split()) <= 4: return "follow_up"
        return "clinical"

    def should_use_rag(self, intent: str) -> bool:
        """Only fetch from Vector DB for clinical or follow-up."""
        return intent in ["clinical", "follow_up"]

    def retrieve_context(self, query: str, document_id: str = "doc-1") -> str:
        """Retrieve relevant context using the unified hybrid retriever."""
        db = SessionLocal()
        try:
            package = self.hybrid_retriever.build_context_package(
                db=db, query=query, document_id=document_id,
            )
            return package.get("context", "")
        except Exception:
            return ""
        finally:
            db.close()

    def _is_mcq_query(self, query: str) -> bool:
        q = query.lower()
        return (
            "except" in q
            or bool(re.search(r"\b[1-9]\)", q))
            or bool(re.search(r"\b[a-d]\)", q))
            or "all of the following" in q
        )

    def _detect_mcq_type(self, query: str) -> str:
        q = query.lower()
        if not self._is_mcq_query(query):
            return "non-mcq"
        if "except" in q:
            return "MCQ-except"
        if "most likely" in q:
            return "MCQ-most-likely"
        if "best next step" in q or "next best step" in q:
            return "MCQ-best-next-step"
        return "MCQ-most-likely"

    def _extract_mcq_options(self, query: str) -> List[str]:
        options = []
        for line in query.splitlines():
            s = line.strip()
            if re.match(r"^([a-eA-E]|\d{1,2})[\)\.\-:]\s+.+", s):
                options.append(s)
        return options

    def _normalize_option_checks(self, option_checks: List[dict], mcq_options: List[str]) -> List[dict]:
        normalized = []
        seen = set()
        for row in option_checks or []:
            option = str(row.get("option", "")).strip()
            if not option:
                continue
            label = str(row.get("label", "uncertain")).lower()
            if label not in {"true", "false", "uncertain"}:
                label = "uncertain"
            normalized.append({
                "option": option,
                "label": label,
                "why": str(row.get("why", "")).strip(),
            })
            seen.add(option.lower())

        # Ensure every detected MCQ option has an explicit check row.
        for opt in mcq_options:
            if opt.lower() not in seen:
                normalized.append({
                    "option": opt,
                    "label": "uncertain",
                    "why": "Option was not explicitly validated by the model.",
                })
        return normalized

    def _infer_mcq_selected_option(self, mcq_type: str, option_checks: List[dict]) -> Optional[str]:
        if not option_checks:
            return None
        if mcq_type == "MCQ-except":
            for row in option_checks:
                if row.get("label") == "false":
                    return row.get("option")
            return None
        # For most-likely / best-next-step, prefer the strongest affirmed option.
        for row in option_checks:
            if row.get("label") == "true":
                return row.get("option")
        return None

    def _build_mcq_analysis(self, mcq_type: str, mcq_options: List[str], validation: Dict[str, Any]) -> Dict[str, Any]:
        checks = self._normalize_option_checks(validation.get("option_checks", []), mcq_options)
        selected = self._infer_mcq_selected_option(mcq_type, checks)
        return {
            "detected": True,
            "mcq_type": mcq_type,
            "options": mcq_options,
            "option_checks": checks,
            "selected_option": selected,
            "selection_rule": "FALSE option for EXCEPT; TRUE option for most-likely/best-next-step.",
        }

    def _estimate_confidence(self, intent: str, citations: List[dict], answer: str) -> float:
        if intent in ["greeting", "meta"]:
            base = 0.55
        elif len(citations) >= 2:
            base = 0.82
        elif len(citations) == 1:
            base = 0.68
        else:
            base = 0.35

        lowered = (answer or "").lower()
        uncertainty_phrases = [
            "insufficient evidence",
            "cannot verify",
            "cannot determine",
            "not enough evidence",
            "uncertain",
            "unable to confirm",
        ]
        if any(p in lowered for p in uncertainty_phrases):
            base = min(base, 0.45)

        return round(max(0.2, min(base, 0.92)), 2)

    def _score_from_validation(self, validation: Dict[str, Any], citations: List[dict], is_mcq: bool) -> float:
        band = validation.get("evidence_level", "none")
        suggested = validation.get("suggested_confidence", 45)
        if band == "strong":
            lo, hi = 85, 95
        elif band == "moderate":
            lo, hi = 70, 84
        elif band == "limited":
            lo, hi = 50, 69
        else:
            lo, hi = 30, 49

        confidence_pct = max(lo, min(hi, int(suggested)))
        if validation.get("contradiction"):
            confidence_pct = min(confidence_pct, 45)
        if is_mcq and len(citations) == 0:
            confidence_pct = min(confidence_pct, 45)
        return round(confidence_pct / 100.0, 2)

    def _fallback_validation(self, answer: str, citations: List[dict], is_mcq: bool) -> Dict[str, Any]:
        if len(citations) >= 2:
            evidence = "strong"
            suggested = 88
        elif len(citations) == 1:
            evidence = "moderate"
            suggested = 76
        else:
            evidence = "none"
            suggested = 40

        if "cannot verify" in (answer or "").lower():
            evidence = "none"
            suggested = 40

        return {
            "contradiction": False,
            "evidence_level": evidence,
            "suggested_confidence": suggested,
            "rationale": "Fallback validation based on available retrieved evidence.",
            "option_checks": [],
        }

    def _validate_answer(
        self,
        query: str,
        answer: str,
        context: str,
        citations: List[dict],
        mcq_options: List[str],
    ) -> Dict[str, Any]:
        if not self.groq_client:
            return self._fallback_validation(answer, citations, bool(mcq_options))

        user_payload = {
            "query": query,
            "answer": answer,
            "retrieved_context": context[:3500],
            "citations": citations[:4],
            "mcq_options": mcq_options,
        }
        try:
            completion = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": VALIDATION_PROMPT},
                    {"role": "user", "content": json.dumps(user_payload)},
                ],
                model=GROQ_SMALL_MODEL,
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            data = json.loads(completion.choices[0].message.content)
            return {
                "contradiction": bool(data.get("contradiction", False)),
                "evidence_level": data.get("evidence_level", "none"),
                "suggested_confidence": int(data.get("suggested_confidence", 45)),
                "rationale": data.get("rationale", "Validation complete."),
                "option_checks": data.get("option_checks", []),
            }
        except Exception:
            return self._fallback_validation(answer, citations, bool(mcq_options))

    def _extract_citations(self, query: str, document_id: str) -> List[dict]:
        """Extract citations using the unified hybrid retriever."""
        db = SessionLocal()
        try:
            package = self.hybrid_retriever.build_context_package(
                db=db, query=query, document_id=document_id,
            )
            return package.get("citations", [])
        except Exception:
            return []
        finally:
            db.close()

    def build_prompt(self, intent: str, context: str, role: UserRole) -> str:
        if intent == "greeting":
            return PROMPT_GREETING
        elif intent == "meta":
            return STRUCTURED_REASONING_POLICY + "\n\n" + PROMPT_META
        elif intent == "follow_up":
            return STRUCTURED_REASONING_POLICY + "\n\n" + PROMPT_FOLLOW_UP.format(context=context)
        else:
            return STRUCTURED_REASONING_POLICY + "\n\n" + PROMPT_CLINICAL.format(role=role.value, context=context)

    # ── Master Orchestration ───────────────────────────────────

    async def generate_response_stream(
        self,
        query: str,
        role: UserRole,
        document_id: Optional[str] = None,
        history: List[dict] = None
    ) -> AsyncGenerator[dict, None]:
        """
        Master method yielding structured payloads (`{type: '...', data: '...'}`)
        It handles intent, gating, prompt wiring, thinking, and final response tokens.
        """
        query_id = f"q-{uuid.uuid4().hex[:8]}"
        history = history or []

        # 1. Classify Intent
        intent = await self.classify_intent(query, history)
        yield {"type": "intent", "data": intent}
        
        # 2. Gate RAG
        # MCQs must always attempt retrieval/validation; never answer from pure generalization.
        is_mcq = self._is_mcq_query(query)
        use_rag = self.should_use_rag(intent) or is_mcq
        context = ""
        citations = []
        trace = []
        retrieval_meta: Dict[str, Any] = {
            "strategy": "none",
            "source": "none",
            "used_rag": False,
            "document_id": document_id,
        }
        
        if use_rag:
            context, citations, retrieval_meta = await self._retrieve_hybrid_context(query, document_id, intent)
            
            # Emit Citations
            if citations:
                yield {"type": "citation", "data": json.dumps(citations)}

            # If clinical, we do thinking and explicit trace steps
            if intent == "clinical":
                # DNA: Dynamic Navigation Arch
                trace = []
                step_val = 1
                
                trace.append(TraceStep(step=step_val, action="Clinical Intent Analysis", detail=f"Contextualizing query for {role.value} perspective"))
                step_val += 1
                
                if retrieval_meta.get("strategy") in ("global_vectorless", "librarian_institutional_fallback"):
                    trace.append(TraceStep(step=step_val, action="AI Librarian Discovery", detail=retrieval_meta.get("selection_reasoning", "Scanning entire digital library")))
                    step_val += 1
                
                trace.append(TraceStep(step=step_val, action="PageIndex Tree Navigation", detail="Retrieving institutional orthopaedic protocols")),
                step_val += 1
                
                trace.append(TraceStep(step=step_val, action="Evidence Mapping", detail=f"Extracted {len(citations)} relevant guideline segments"))
                
                for t in trace:
                    trace_data_str = json.dumps({"action": t.action, "detail": t.detail})
                    yield {"type": "trace", "step": t.step, "data": trace_data_str}
                
                # Stream Thinking Block (Groq)
                if self.groq_client:
                    try:
                        t_stream = self.groq_client.chat.completions.create(
                            messages=[
                                {"role": "system", "content": THINKING_PROMPT},
                                {"role": "user", "content": f"Query: {query}\nRole: {role.value}\nContext: {context[:500]}"}
                            ],
                            model=GROQ_MODEL,
                            temperature=0.3,
                            max_tokens=200,
                            stream=True,
                        )
                        buffer = ""
                        for chunk in t_stream:
                            delta = chunk.choices[0].delta.content or ""
                            buffer += delta
                            while "\n" in buffer:
                                line, buffer = buffer.split("\n", 1)
                                if line.strip():
                                    yield {"type": "thinking", "data": line.strip() + "\n"}
                        if buffer.strip():
                            yield {"type": "thinking", "data": buffer.strip() + "\n"}
                    except Exception as e:
                        pass
                yield {"type": "thinking_done", "data": ""}

        # 3. Build Prompt & Format History
        system_prompt = self.build_prompt(intent, context, role)
        mcq_type = self._detect_mcq_type(query)
        mcq_options = self._extract_mcq_options(query)
        if is_mcq:
            system_prompt += (
                "\n\nMCQ guardrail:\n"
                "- This appears to be a multiple-choice question.\n"
                f"- MCQ type detected: {mcq_type}.\n"
                "- If options cannot be validated from retrieved context, do NOT pick a definitive option.\n"
                "- State that available guideline context is insufficient and request the exact source/chapter."
            )
            if mcq_options:
                system_prompt += "\n- Verify each option explicitly before final answer."
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Include past 6 user/assistant messages for context
        for msg in history[-6:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        messages.append({"role": "user", "content": query})

        # 4. Generate Final Stream
        answer_full = ""
        confidence = 0.35

        if use_rag and not citations:
            answer_full = (
                "I cannot verify this from the currently retrieved guideline context.\n\n"
                "Please share the exact source/chapter (or enable the relevant DDH/Pavlik section) "
                "so I can give a reliable option-by-option answer."
            )
            for chunk in answer_full.split(" "):
                yield {"type": "token", "data": chunk + " "}
            validation = self._fallback_validation(answer_full, citations, is_mcq)
            confidence = self._score_from_validation(validation, citations, is_mcq)
            mcq_analysis = self._build_mcq_analysis(mcq_type, mcq_options, validation) if is_mcq else None
            if mcq_analysis:
                yield {"type": "mcq_analysis", "data": json.dumps(mcq_analysis)}
            yield {"type": "confidence", "data": str(confidence)}
            final_payload = {
                "answer": answer_full,
                "citations": citations,
                "confidence": confidence,
                "trace": [t.model_dump() for t in trace],
                "model": GROQ_MODEL if self.groq_client else "mock",
                "intent": intent,
                "validation": validation,
                "question_type": mcq_type if is_mcq else "clinical",
                "mcq_analysis": mcq_analysis,
                "retrieval": retrieval_meta,
            }
            yield {"type": "final_payload", "data": final_payload}
            yield {"type": "done", "data": "[DONE]"}
            return
        
        # If a real indexed document is selected, use PageIndex for retrieval+generation.
        # This makes the chat truly RAG-backed on your indexed PDFs.
        if USE_PAGEINDEX_CLOUD and self._can_use_pageindex(document_id):
            # Stream via PageIndex, then validate+score like usual.
            pi_messages = messages
            pi_answer = ""
            pi_citations: List[dict] = []
            async for ev in self._pageindex_stream_answer_and_citations(pi_messages, document_id):
                if ev.get("type") == "_pageindex_done":
                    payload = json.loads(ev.get("data", "{}") or "{}")
                    pi_answer = payload.get("answer", "") or ""
                    pi_citations = payload.get("citations", []) or []
                    break
                yield ev

            # Build context from citations text (for validator)
            context_from_cits = "\n\n".join([(c.get("content") or c.get("text") or "") for c in (pi_citations or [])])[:5000]
            validation = self._validate_answer(query, pi_answer, context_from_cits, pi_citations, mcq_options)
            mcq_analysis = self._build_mcq_analysis(mcq_type, mcq_options, validation) if is_mcq else None
            if mcq_analysis:
                yield {"type": "mcq_analysis", "data": json.dumps(mcq_analysis)}
            confidence = self._score_from_validation(validation, pi_citations, is_mcq)
            trace.append(
                TraceStep(
                    step=len(trace) + 1,
                    action="Guideline Consistency Validation",
                    detail=validation.get("rationale", "Validated answer against retrieved evidence."),
                )
            )
            yield {"type": "confidence", "data": str(confidence)}

            final_payload = {
                "answer": pi_answer,
                "citations": pi_citations,
                "confidence": confidence,
                "trace": [t.model_dump() for t in trace],
                "model": "pageindex",
                "intent": intent,
                "validation": validation,
                "question_type": mcq_type if is_mcq else "clinical",
                "mcq_analysis": mcq_analysis,
                "retrieval": {
                    "strategy": "pageindex_cloud",
                    "source": "pageindex",
                    "used_rag": bool(pi_citations),
                    "document_id": document_id,
                    "citations_count": len(pi_citations),
                },
            }
            yield {"type": "final_payload", "data": final_payload}
            yield {"type": "done", "data": "[DONE]"}
            return

        if self.groq_client:
            try:
                stream = self.groq_client.chat.completions.create(
                    messages=messages,
                    model=GROQ_MODEL,
                    temperature=0.4,
                    max_tokens=1500,
                    stream=True,
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta.content or ""
                    if delta:
                        answer_full += delta
                        yield {"type": "token", "data": delta}
            except Exception as e:
                yield {"type": "error", "data": str(e)}
        else:
            answer_full = f"Mock response for intent: {intent}"
            for word in answer_full.split():
                yield {"type": "token", "data": " " + word}

        # 5. Validate answer against retrieved evidence, then score confidence
        validation = self._validate_answer(query, answer_full, context, citations, mcq_options)
        mcq_analysis = self._build_mcq_analysis(mcq_type, mcq_options, validation) if is_mcq else None
        if mcq_analysis:
            yield {"type": "mcq_analysis", "data": json.dumps(mcq_analysis)}
        confidence = self._score_from_validation(validation, citations, is_mcq)
        trace.append(
            TraceStep(
                step=len(trace) + 1,
                action="Guideline Consistency Validation",
                detail=validation.get("rationale", "Validated answer against retrieved evidence."),
            )
        )
        yield {"type": "confidence", "data": str(confidence)}
        
        # 6. Yield Final Package for DB Saving in `chat.py`
        final_payload = {
            "answer": answer_full,
            "citations": citations,
            "confidence": confidence,
            "trace": [t.model_dump() for t in trace],
            "model": GROQ_MODEL if self.groq_client else "mock",
            "intent": intent,
            "validation": validation,
            "question_type": mcq_type if is_mcq else "clinical",
            "mcq_analysis": mcq_analysis,
            "retrieval": retrieval_meta,
        }
        yield {"type": "final_payload", "data": final_payload}
        yield {"type": "done", "data": "[DONE]"}
