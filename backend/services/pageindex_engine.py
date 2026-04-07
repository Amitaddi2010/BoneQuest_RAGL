# ============================================================
# BoneQuest v2 — PageIndex Engine (Modular Intent-Driven Pipeline)
# ============================================================

import os
import uuid
import json
import re
from typing import List, Optional, AsyncGenerator
from pydantic import BaseModel
from models.schemas import QueryResponse, TraceStep, UserRole, Citation
from config import settings

GROQ_API_KEY = settings.GROQ_API_KEY
GROQ_MODEL   = settings.GROQ_TEXT_MODEL
PAGEINDEX_API_KEY = settings.PAGEINDEX_API_KEY

# ── Clinical Knowledge Base (simulates PageIndex tree) ─────

CLINICAL_CONTEXT = {
    "doc-1": {
        "title": "PGIMER Orthopaedic Guidelines 2025",
        "sections": {
            "fracture": {
                "content": """FRACTURE MANAGEMENT GUIDELINES:
- Initial Assessment: Complete neurovascular examination, radiographic evaluation (AP/Lateral), classify using AO/OTA system
- Tibial shaft fractures: Intramedullary nailing is gold standard for displaced fractures. Closed reduction preferred. Union expected 12-16 weeks.
- Comminuted patterns: Consider locking screws at both ends. Reamed nailing preferred for closed fractures.
- Femoral neck fractures: Age-dependent management. <60yo: internal fixation. >60yo: arthroplasty. Displaced: hemiarthroplasty or THR.
- Open fractures: Gustilo-Anderson classification. Emergency debridement within 6 hours. IV antibiotics immediately.""",
                "pages": "p. 1-42",
                "section_title": "Fracture Management",
                "evidence_strength": "strong"
            },
            "joint_replacement": {
                "content": """JOINT REPLACEMENT PROTOCOLS:
- Total Hip Arthroplasty: Posterior approach most common. Anterolateral for reduced dislocation risk. Cement for osteoporotic bone.
- Total Knee Arthroplasty: Medial parapatellar approach standard. Tourniquet time <90min. PCL-retaining vs substituting based on deformity.
- Revision Surgery: Bone defect classification essential. Augments and cones for metaphyseal defects.""",
                "pages": "p. 43-78",
                "section_title": "Joint Replacement",
                "evidence_strength": "strong"
            },
            "comorbidity": {
                "content": """COMORBIDITY CONSIDERATIONS:
- Diabetes: Perioperative glucose target 140-180 mg/dL. HbA1c <8% for elective surgery. Infection risk 3.2x higher in uncontrolled DM. Extended antibiotic prophylaxis (48h vs 24h). Delayed union risk increases 25-30%.
- Cardiac: Pre-op cardiology clearance for major procedures. Beta-blocker optimization. Regional anesthesia preferred. DVT prophylaxis critical.
- Geriatric: Falls risk assessment mandatory. Bone density evaluation. Calcium + Vitamin D supplementation. Early mobilization protocol.""",
                "pages": "p. 79-110",
                "section_title": "Comorbidity Considerations",
                "evidence_strength": "moderate"
            },
            "postop": {
                "content": """POST-OPERATIVE CARE:
- Rehabilitation: Phase-based protocol. Week 1-2: ROM exercises, weight-bearing as tolerated. Week 3-6: progressive strengthening. Month 2-3: functional training.
- Infection Prevention: Cefazolin 2g IV pre-op. Wound inspection at 48h, 1 week, 2 weeks. Risk factors: diabetes, obesity, smoking, immunosuppression.
- ACL Reconstruction Rehab: Week 1-2: extension emphasis, quad sets. Week 3-6: ROM 0-120°, stationary cycling. Month 2-4: closed chain exercises. Month 4-6: sport-specific. Return criteria: >90% limb symmetry.""",
                "pages": "p. 111-142",
                "section_title": "Post-operative Care",
                "evidence_strength": "strong"
            }
        }
    }
}

SECTION_KEYWORDS = {
    "fracture":         ['fracture', 'break', 'broken', 'tibial', 'femoral', 'shaft', 'comminuted', 'displaced', 'open fracture'],
    "joint_replacement":['replacement', 'arthroplasty', 'hip', 'knee', 'thr', 'tka', 'approach', 'revision'],
    "comorbidity":      ['diabetes', 'diabetic', 'cardiac', 'comorbid', 'geriatric', 'elderly', 'chf', 'heart', 'age', 'dm'],
    "postop":           ['rehab', 'rehabilitation', 'recovery', 'postop', 'post-op', 'infection', 'acl', 'follow-up', 'protocol']
}


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


class PageIndexEngine:
    def __init__(self):
        self.groq_client = None
        self._init_groq()

    def _init_groq(self):
        try:
            from groq import Groq
            self.groq_client = Groq(api_key=GROQ_API_KEY)
        except ImportError:
            pass
        except Exception:
            pass

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
                model="llama3-8b-8192", # Fast, lightweight model for intent
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
        """Retrieve relevant context dynamically."""
        doc = CLINICAL_CONTEXT.get(document_id, CLINICAL_CONTEXT["doc-1"])
        query_lower = query.lower()
        relevant = []

        for key, section in doc["sections"].items():
            kws = SECTION_KEYWORDS.get(key, [])
            if any(kw in query_lower for kw in kws):
                relevant.append(section["content"])

        return "\n\n".join(relevant)

    def _is_mcq_query(self, query: str) -> bool:
        q = query.lower()
        return (
            "except" in q
            or bool(re.search(r"\b[1-9]\)", q))
            or bool(re.search(r"\b[a-d]\)", q))
            or "all of the following" in q
        )

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

    def _extract_citations(self, query: str, document_id: str) -> List[dict]:
        doc = CLINICAL_CONTEXT.get(document_id, CLINICAL_CONTEXT["doc-1"])
        query_lower = query.lower()
        citations = []
        for key, section in doc["sections"].items():
            kws = SECTION_KEYWORDS.get(key, [])
            matched_kws = [kw for kw in kws if kw in query_lower]
            if matched_kws:
                # Force-include the content text with multiple aliases for robustness
                content_text = section.get("content", "Text content not found in context dictionary.")
                citations.append({
                    "guideline":        "PGIMER Orthopaedic Guidelines 2025",
                    "section":          section.get("section_title", "Reference"),
                    "page_range":       section.get("pages", ""),
                    "evidence_strength": section.get("evidence_strength", "moderate"),
                    "reasoning":        f"Query contains '{matched_kws[0]}'",
                    "content":          content_text,
                    "text":             content_text,  # alias
                    "snippet":          content_text[:100] + "...", # snippet alias
                    "matched_keywords": matched_kws
                })
        
        print(f"DEBUG [Engine]: Extracted {len(citations)} citations for query '{query}'. First content length: {len(citations[0]['content']) if citations else 0}")
        return citations

    def build_prompt(self, intent: str, context: str, role: UserRole) -> str:
        if intent == "greeting":
            return PROMPT_GREETING
        elif intent == "meta":
            return PROMPT_META
        elif intent == "follow_up":
            return PROMPT_FOLLOW_UP.format(context=context)
        else:
            return PROMPT_CLINICAL.format(role=role.value, context=context)

    # ── Master Orchestration ───────────────────────────────────

    async def generate_response_stream(
        self,
        query: str,
        role: UserRole,
        document_id: str = "doc-1",
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
        use_rag = self.should_use_rag(intent)
        context = ""
        citations = []
        trace = []
        
        if use_rag:
            context = self.retrieve_context(query, document_id)
            citations = self._extract_citations(query, document_id)
            
            # Emit Citations
            if citations:
                yield {"type": "citation", "data": json.dumps(citations)}

            # If clinical, we do thinking and explicit trace steps
            if intent == "clinical":
                # Professional clinical trace steps
                trace = [
                    TraceStep(step=1, action="Clinical Intent Analysis", detail=f"Contextualizing query for {role.value} perspective"),
                    TraceStep(step=2, action="PageIndex Tree Navigation", detail="Retrieving institutional orthopaedic protocols"),
                    TraceStep(step=3, action="Evidence Mapping", detail=f"Extracted {len(citations)} relevant guideline segments"),
                ]
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
        is_mcq = self._is_mcq_query(query)
        if is_mcq:
            system_prompt += (
                "\n\nMCQ guardrail:\n"
                "- This appears to be a multiple-choice question.\n"
                "- If options cannot be validated from retrieved context, do NOT pick a definitive option.\n"
                "- State that available guideline context is insufficient and request the exact source/chapter."
            )
        
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
            confidence = self._estimate_confidence(intent, citations, answer_full)
            yield {"type": "confidence", "data": str(confidence)}
            final_payload = {
                "answer": answer_full,
                "citations": citations,
                "confidence": confidence,
                "trace": [t.model_dump() for t in trace],
                "model": GROQ_MODEL if self.groq_client else "mock",
                "intent": intent
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

        # 5. Emit Post-Gen Details
        confidence = self._estimate_confidence(intent, citations, answer_full)
        yield {"type": "confidence", "data": str(confidence)}
        
        # 6. Yield Final Package for DB Saving in `chat.py`
        final_payload = {
            "answer": answer_full,
            "citations": citations,
            "confidence": confidence,
            "trace": [t.model_dump() for t in trace],
            "model": GROQ_MODEL if self.groq_client else "mock",
            "intent": intent
        }
        yield {"type": "final_payload", "data": final_payload}
        yield {"type": "done", "data": "[DONE]"}
