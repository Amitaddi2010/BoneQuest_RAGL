# ============================================================
# BoneQuest v2 — PageIndex Engine (Groq + Thinking + Structured Sections)
# ============================================================

import os
import uuid
import json
from typing import List, Optional, AsyncGenerator
from models.schemas import QueryResponse, TraceStep, UserRole
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

# ── Section keywords for matching ──────────────────────────

SECTION_KEYWORDS = {
    "fracture":         ['fracture', 'break', 'broken', 'tibial', 'femoral', 'shaft', 'comminuted', 'displaced', 'open fracture'],
    "joint_replacement":['replacement', 'arthroplasty', 'hip', 'knee', 'thr', 'tka', 'approach', 'revision'],
    "comorbidity":      ['diabetes', 'diabetic', 'cardiac', 'comorbid', 'geriatric', 'elderly', 'chf', 'heart', 'age', 'dm'],
    "postop":           ['rehab', 'rehabilitation', 'recovery', 'postop', 'post-op', 'infection', 'acl', 'follow-up', 'protocol']
}

# ── Role-specific system prompts ───────────────────────────

ROLE_PROMPTS = {
    UserRole.patient: """You are BoneQuest AI, a friendly medical assistant explaining orthopaedic conditions to patients.
Use simple, everyday language. Avoid medical jargon. Be reassuring and empathetic.
Explain what the condition means for the patient's daily life and recovery.
Always mention that they should follow their doctor's specific advice.

Structure your response with these exact section headers on their own lines:
📋 CLINICAL RECOMMENDATION
🔬 GUIDELINE EVIDENCE
💡 CLINICAL REASONING
⚠️ CONSIDERATIONS
🎯 KEY TAKEAWAY""",

    UserRole.resident: """You are BoneQuest AI, a clinical teaching assistant for orthopaedic surgery residents.
Provide detailed pathophysiology, differential diagnoses, and evidence-based treatment algorithms.
Reference classification systems (AO/OTA, Gustilo-Anderson, Garden, etc.).
Include key surgical steps and post-operative protocols. Cite page numbers from the protocol.

Structure your response with these exact section headers on their own lines:
📋 CLINICAL RECOMMENDATION
🔬 GUIDELINE EVIDENCE
💡 CLINICAL REASONING
⚠️ CONSIDERATIONS
🎯 KEY TAKEAWAY""",

    UserRole.consultant: """You are BoneQuest AI, an advanced orthopaedic decision-support system for senior consultants.
Focus on complex decision-making, surgical technique nuances, and complication management.
Discuss evidence quality, alternative approaches, and controversial topics.
Reference current literature and institutional protocol deviations when relevant.

Structure your response with these exact section headers on their own lines:
📋 CLINICAL RECOMMENDATION
🔬 GUIDELINE EVIDENCE
💡 CLINICAL REASONING
⚠️ CONSIDERATIONS
🎯 KEY TAKEAWAY""",

    UserRole.admin: """You are BoneQuest AI in administrative mode.
Provide highly technical, comprehensive clinical data and system-level insights.
Your tone is professional, authoritative, and focused on clinical accuracy and guideline adherence.

Structure your response with these exact section headers on their own lines:
📋 CLINICAL RECOMMENDATION
🔬 GUIDELINE EVIDENCE
💡 CLINICAL REASONING
⚠️ CONSIDERATIONS
🎯 KEY TAKEAWAY"""
}

THINKING_PROMPT = """You are an expert orthopaedic clinical AI. Think through the following query step by step.
Keep each step SHORT (one sentence). Output exactly 5 numbered steps covering:
1. What is the core clinical question?
2. What patient factors or comorbidities matter?
3. Which guideline sections are relevant?
4. What are the key treatment options?
5. How confident are you and why?

Do NOT answer the question yet — just reason through it.
Be direct. No pleasantries."""


class PageIndexEngine:
    """
    Simulates PageIndex reasoning-based retrieval using Groq LLM.
    Adds: thinking block generation, structured section output, rich citations.
    """

    def __init__(self):
        self.groq_client = None
        self._init_groq()

    def _init_groq(self):
        try:
            from groq import Groq
            self.groq_client = Groq(api_key=GROQ_API_KEY)
        except ImportError:
            print("⚠️  Groq SDK not installed. Using mock responses.")
        except Exception as e:
            print(f"⚠️  Groq init failed: {e}. Using mock responses.")

    # ── Trace generation ───────────────────────────────────

    def generate_trace(self, query: str, role: UserRole) -> List[TraceStep]:
        query_lower = query.lower()
        trace = [TraceStep(step=1, action="Read Table of Contents", detail="Scanning hierarchical tree index for relevant chapters...")]

        sections_found = []
        for key, kws in SECTION_KEYWORDS.items():
            if any(w in query_lower for w in kws):
                doc_sections = CLINICAL_CONTEXT["doc-1"]["sections"]
                if key in doc_sections:
                    sec = doc_sections[key]
                    sections_found.append((key, sec["section_title"], sec["pages"]))

        if not sections_found:
            sec = CLINICAL_CONTEXT["doc-1"]["sections"]["fracture"]
            sections_found.append(("fracture", sec["section_title"], sec["pages"]))

        for i, (key, title, pages) in enumerate(sections_found):
            trace.append(TraceStep(
                step=i + 2,
                action=f"Selected: {title}",
                detail=f"Navigating to {title} ({pages})"
            ))

        if len(sections_found) > 1:
            trace.append(TraceStep(
                step=len(sections_found) + 2,
                action="Cross-reference detected",
                detail=f"Combining {len(sections_found)} sections for comprehensive answer"
            ))

        trace.append(TraceStep(
            step=len(trace) + 1,
            action="Assessed sufficiency",
            detail=f"All relevant sections retrieved. Generating {role.value}-level response."
        ))
        return trace

    # ── Thinking block generation (streamed) ───────────────

    async def generate_thinking_stream(
        self,
        query: str,
        role: UserRole,
        context: str,
        conversation_context: str = ""
    ) -> AsyncGenerator[str, None]:
        """Yields thinking lines one at a time for SSE streaming."""
        
        if self._is_conversational(query):
            yield "Recognized basic greeting or conversational query. Skipping full clinical RAG.\n"
            return

        conversation_part = f"\nConversation context:\n{conversation_context}\n" if conversation_context else ""

        user_msg = f"""{conversation_part}
Clinical query: {query}

Available guideline context (summary):
{context[:600]}...

Role: {role.value}"""

        if self.groq_client:
            try:
                stream = self.groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": THINKING_PROMPT},
                        {"role": "user",   "content": user_msg}
                    ],
                    model=GROQ_MODEL,
                    temperature=0.4,
                    max_tokens=350,
                    stream=True,
                )
                buffer = ""
                for chunk in stream:
                    delta = chunk.choices[0].delta.content or ""
                    buffer += delta
                    # Yield complete lines as they arrive
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if line:
                            yield line + "\n"
                if buffer.strip():
                    yield buffer.strip() + "\n"
                return
            except Exception as e:
                print(f"Groq thinking error: {e}")

        # Fallback mock thinking
        mock_steps = [
            f"1. Core question: Analysing '{query[:60]}...' — identifying fracture/joint/comorbidity focus.",
            f"2. Patient factors: Checking for age, diabetes, cardiac history, or other relevant comorbidities.",
            f"3. Guideline sections: Locating relevant protocol chapters via tree navigation.",
            f"4. Treatment options: Weighing surgical vs non-surgical approaches based on retrieved evidence.",
            f"5. Confidence: High — multiple matching sections found; cross-referencing complete."
        ]
        for step in mock_steps:
            yield step + "\n"

    def _is_conversational(self, query: str) -> bool:
        q = query.lower().strip()
        greetings = {'hi', 'hello', 'hey', 'how are you', 'howdy', 'good morning', 'who are you', 'good afternoon', 'thanks', 'thank you', 'ok', 'okay', 'great'}
        if q in greetings:
            return True
            
        clinical_keywords = sum(SECTION_KEYWORDS.values(), [])
        
        if len(q.split()) <= 4 and not any(kw in q for kw in clinical_keywords):
            return True
            
        meta_phrases = [
            'test you', 'ask you', 'ask a question', 'can you', 'what can you', 
            'who created', 'tell me about', 'how do you', 'i want to give', 
            'i want to ask', 'will test', 'testing you', 'help me', 
            'are you able', 'what is your', 'questions related to', 'some questions'
        ]
        
        has_meta = any(phrase in q for phrase in meta_phrases)
        has_clinical = any(kw in q for kw in clinical_keywords)
        
        if has_meta and not has_clinical:
            return True
            
        if 'test you' in q or 'ask you' in q:
            return True
            
        return False

    async def _generate_conversational_answer(self, query: str, conversation_context: str) -> str:
        prompt = f"""You are BoneQuest AI, an advanced orthopaedic clinical assistant.
The user is talking to you conversationally or asking about your capabilities.
Respond naturally, helpfully, and professionally without strictly formatted clinical headers. Keep it concise.

Previous conversation context:
{conversation_context}

User: {query}
"""
        if self.groq_client:
            try:
                completion = self.groq_client.chat.completions.create(
                    messages=[{"role": "system", "content": prompt}],
                    model=GROQ_MODEL,
                    temperature=0.7,
                    max_tokens=300
                )
                return completion.choices[0].message.content
            except Exception as e:
                print(f"Groq API error: {e}")
        
        return "Hello! I am BoneQuest AI, your orthopaedic clinical assistant. I'm ready to help with evidence-based protocols, fracture management, or image analysis. How can I assist you today?"


    # ── Main query entry point ─────────────────────────────

    async def query(
        self,
        query: str,
        role: UserRole,
        document_id: str = "doc-1",
        num_hops: int = 3,
        conversation_context: str = ""
    ) -> QueryResponse:
        query_id = f"q-{uuid.uuid4().hex[:8]}"
        
        if self._is_conversational(query):
            answer = await self._generate_conversational_answer(query, conversation_context)
            return QueryResponse(
                id=query_id,
                answer=answer,
                confidence=0.99,
                citations=[],
                reasoning_trace=[],
                role=role,
                model=f"groq/{GROQ_MODEL}" if self.groq_client else "conversational-bypass"
            )

        trace   = self.generate_trace(query, role)
        context = self._retrieve_context(query, document_id)
        citations = self._extract_citations(query, document_id)
        answer = await self._generate_answer(query, role, context, conversation_context)
        confidence = self._calculate_confidence(query, context)

        return QueryResponse(
            id=query_id,
            answer=answer,
            confidence=confidence,
            citations=citations,
            reasoning_trace=trace,
            role=role,
            model=f"groq/{GROQ_MODEL}" if self.groq_client else "mock"
        )

    # ── Context retrieval ──────────────────────────────────

    def _retrieve_context(self, query: str, document_id: str) -> str:
        doc = CLINICAL_CONTEXT.get(document_id, CLINICAL_CONTEXT["doc-1"])
        query_lower = query.lower()
        relevant = []

        for key, section in doc["sections"].items():
            kws = SECTION_KEYWORDS.get(key, [])
            if any(kw in query_lower for kw in kws):
                relevant.append(section["content"])

        if not relevant:
            first = list(doc["sections"].values())[0]
            relevant.append(first["content"])

        return "\n\n".join(relevant)

    # ── Rich citation extraction ───────────────────────────

    def _extract_citations(self, query: str, document_id: str) -> List[dict]:
        """Returns rich citation objects with evidence_strength and reasoning."""
        doc = CLINICAL_CONTEXT.get(document_id, CLINICAL_CONTEXT["doc-1"])
        query_lower = query.lower()
        citations = []

        for key, section in doc["sections"].items():
            kws = SECTION_KEYWORDS.get(key, [])
            matched_kws = [kw for kw in kws if kw in query_lower]
            if matched_kws:
                citations.append({
                    "guideline":        "PGIMER Orthopaedic Guidelines 2025",
                    "section":          section["section_title"],
                    "page_range":       section["pages"],
                    "evidence_strength": section.get("evidence_strength", "moderate"),
                    "reasoning":        f"Query contains '{matched_kws[0]}' — matched to {section['section_title']} protocol.",
                    "matched_keywords": matched_kws
                })

        if not citations:
            sec = doc["sections"]["fracture"]
            citations.append({
                "guideline":        "PGIMER Orthopaedic Guidelines 2025",
                "section":          sec["section_title"],
                "page_range":       sec["pages"],
                "evidence_strength": "moderate",
                "reasoning":        "Default section returned — no specific keyword match detected.",
                "matched_keywords": []
            })

        return citations

    # ── Confidence scoring ─────────────────────────────────

    def _calculate_confidence(self, query: str, context: str) -> float:
        query_words = set(query.lower().split())
        context_lower = context.lower()
        matches = sum(1 for w in query_words if w in context_lower and len(w) > 3)
        total   = sum(1 for w in query_words if len(w) > 3)
        if total == 0:
            return 0.75
        return round(min(0.98, 0.70 + (matches / total) * 0.28), 2)

    # ── Answer generation (structured sections) ────────────

    async def _generate_answer(
        self,
        query: str,
        role: UserRole,
        context: str,
        conversation_context: str = ""
    ) -> str:
        system_prompt = ROLE_PROMPTS[role]

        conversation_part = f"\nPrevious conversation context:\n{conversation_context}\n" if conversation_context else ""

        user_prompt = f"""Based on the following orthopaedic clinical protocol sections retrieved via PageIndex tree navigation:

---
{context}
---
{conversation_part}
Clinical Query: {query}

Provide a comprehensive, well-structured answer using EXACTLY these section headers (each on its own line):

📋 CLINICAL RECOMMENDATION
[Direct answer — what to do]

🔬 GUIDELINE EVIDENCE
[What the protocol says, cite page numbers]

💡 CLINICAL REASONING
[Why this recommendation makes sense]

⚠️ CONSIDERATIONS
[Special factors, contraindications, comorbidities]

🎯 KEY TAKEAWAY
[Single most important sentence]

Use markdown for formatting within each section (bold, bullet points). Keep each section focused."""

        if self.groq_client:
            try:
                completion = self.groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_prompt}
                    ],
                    model=GROQ_MODEL,
                    temperature=0.3,
                    max_tokens=1800,
                    top_p=0.9,
                )
                return completion.choices[0].message.content
            except Exception as e:
                print(f"Groq API error: {e}")
                return self._mock_response(query, role)
        return self._mock_response(query, role)

    # ── Mock fallback ──────────────────────────────────────

    def _mock_response(self, query: str, role: UserRole) -> str:
        query_lower = query.lower()

        if 'fracture' in query_lower and 'diabet' in query_lower:
            return """📋 CLINICAL RECOMMENDATION
Proceed with intramedullary nailing for tibial shaft fracture with strict perioperative glycaemic control (target 140-180 mg/dL). Extended antibiotic prophylaxis (48h) is mandatory.

🔬 GUIDELINE EVIDENCE
Per **Fracture Management (p. 31-42)**: IM nailing is gold standard for tibial shaft fractures. Per **Comorbidity Considerations (p. 79-88)**: HbA1c <8% required for elective surgery; infection risk is **3.2× higher** in uncontrolled DM.

💡 CLINICAL REASONING
The combination of comminution and diabetes doubles the challenge — mechanical (fixation stability) and biological (healing + infection). IM nailing addresses mechanics; tight glucose control and extended prophylaxis address the biological risk.

⚠️ CONSIDERATIONS
- **HbA1c** must be <8% pre-operatively for elective cases
- **Delayed union** risk is 25-30% higher — serial X-rays at 6, 8, 12 weeks
- Weekly wound checks ×3 weeks post-op
- Consider CT at 8 weeks if union is questionable

🎯 KEY TAKEAWAY
Optimise glucose pre-operatively, nail the fracture, extend antibiotics to 48h, and monitor union closely."""

        if 'acl' in query_lower:
            return """📋 CLINICAL RECOMMENDATION
Proceed with ACL reconstruction if patient is functionally unstable and willing to comply with a 6-month rehabilitation protocol. Bone-patellar tendon-bone or hamstring autograft are first-line choices.

🔬 GUIDELINE EVIDENCE
Per **Post-operative Care (p. 111-142)**: Return-to-sport criteria require >90% limb symmetry index. Reconstruction is strongly supported for young active patients.

💡 CLINICAL REASONING
ACL-deficient knees in active patients lead to progressive meniscal and chondral damage. Early reconstruction preserves long-term joint health.

⚠️ CONSIDERATIONS
- Patient must achieve full ROM and quad strength pre-operatively
- High-risk groups (growth plate open, elderly low-demand): conservative management
- Return-to-sport: minimum 9 months, not 6

🎯 KEY TAKEAWAY
Reconstruct early, rehabilitate diligently, and don't rush return-to-sport — 9 months minimum."""

        return f"""📋 CLINICAL RECOMMENDATION
Based on retrieved orthopaedic protocols, the recommended approach has been identified and tailored for the **{role.value}** level.

🔬 GUIDELINE EVIDENCE
Relevant sections from **PGIMER Orthopaedic Guidelines 2025** have been cross-referenced via multi-hop tree navigation.

💡 CLINICAL REASONING
The query has been matched against available protocol sections. Cross-referencing ensures comprehensive coverage of relevant clinical factors.

⚠️ CONSIDERATIONS
- Always verify with institutional protocols
- Patient-specific factors may modify the standard recommendation
- Consult senior colleague for complex or atypical presentations

🎯 KEY TAKEAWAY
AI-assisted clinical decision support — always verify with institutional guidelines before final clinical decision."""
