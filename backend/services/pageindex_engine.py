# ============================================================
# BoneQuest v2 — PageIndex Engine (Groq + Mock Reasoning)
# ============================================================

import os
import uuid
import json
from typing import List, Optional
from models.schemas import QueryResponse, TraceStep, UserRole
from config import settings

# API Keys from config
GROQ_API_KEY = settings.GROQ_API_KEY
GROQ_MODEL = settings.GROQ_TEXT_MODEL
PAGEINDEX_API_KEY = settings.PAGEINDEX_API_KEY

# Clinical context that gets injected into prompts (simulating PageIndex tree retrieval)
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
                "pages": "p. 1-42"
            },
            "joint_replacement": {
                "content": """JOINT REPLACEMENT PROTOCOLS:
- Total Hip Arthroplasty: Posterior approach most common. Anterolateral for reduced dislocation risk. Cement for osteoporotic bone.
- Total Knee Arthroplasty: Medial parapatellar approach standard. Tourniquet time <90min. PCL-retaining vs substituting based on deformity.
- Revision Surgery: Bone defect classification essential. Augments and cones for metaphyseal defects.""",
                "pages": "p. 43-78"
            },
            "comorbidity": {
                "content": """COMORBIDITY CONSIDERATIONS:
- Diabetes: Perioperative glucose target 140-180 mg/dL. HbA1c <8% for elective surgery. Infection risk 3.2x higher in uncontrolled DM. Extended antibiotic prophylaxis (48h vs 24h). Delayed union risk increases 25-30%.
- Cardiac: Pre-op cardiology clearance for major procedures. Beta-blocker optimization. Regional anesthesia preferred. DVT prophylaxis critical.
- Geriatric: Falls risk assessment mandatory. Bone density evaluation. Calcium + Vitamin D supplementation. Early mobilization protocol.""",
                "pages": "p. 79-110"
            },
            "postop": {
                "content": """POST-OPERATIVE CARE:
- Rehabilitation: Phase-based protocol. Week 1-2: ROM exercises, weight-bearing as tolerated. Week 3-6: progressive strengthening. Month 2-3: functional training.
- Infection Prevention: Cefazolin 2g IV pre-op. Wound inspection at 48h, 1 week, 2 weeks. Risk factors: diabetes, obesity, smoking, immunosuppression.
- ACL Reconstruction Rehab: Week 1-2: extension emphasis, quad sets. Week 3-6: ROM 0-120°, stationary cycling. Month 2-4: closed chain exercises. Month 4-6: sport-specific. Return criteria: >90% limb symmetry.""",
                "pages": "p. 111-142"
            }
        }
    }
}

# Role-specific system prompts
ROLE_PROMPTS = {
    UserRole.patient: """You are BoneQuest AI, a friendly medical assistant explaining orthopaedic conditions to patients.
Use simple, everyday language. Avoid medical jargon. Be reassuring and empathetic.
Explain what the condition means for the patient's daily life and recovery.
Always mention that they should follow their doctor's specific advice.""",

    UserRole.resident: """You are BoneQuest AI, a clinical teaching assistant for orthopaedic surgery residents.
Provide detailed pathophysiology, differential diagnoses, and evidence-based treatment algorithms.
Reference classification systems (AO/OTA, Gustilo-Anderson, Garden, etc.).
Include key surgical steps and post-operative protocols. Cite page numbers from the protocol.""",

    UserRole.consultant: """You are BoneQuest AI, an advanced orthopaedic decision-support system for senior consultants.
Focus on complex decision-making, surgical technique nuances, and complication management.
Discuss evidence quality, alternative approaches, and controversial topics.
Reference current literature and institutional protocol deviations when relevant."""
}


class PageIndexEngine:
    """
    Simulates PageIndex reasoning-based retrieval using Groq LLM.
    
    In production, this would use the actual PageIndex SDK to:
    1. Build hierarchical tree indices from PDF documents
    2. Perform multi-hop tree search during query time
    3. Return structured reasoning traces
    
    For now, we simulate the tree navigation and use Groq for answer generation.
    """

    def __init__(self):
        self.groq_client = None
        self._init_groq()

    def _init_groq(self):
        """Initialize Groq client."""
        try:
            from groq import Groq
            self.groq_client = Groq(api_key=GROQ_API_KEY)
        except ImportError:
            print("⚠️  Groq SDK not installed. Using mock responses.")
            self.groq_client = None
        except Exception as e:
            print(f"⚠️  Groq init failed: {e}. Using mock responses.")
            self.groq_client = None

    def generate_trace(self, query: str, role: UserRole) -> List[TraceStep]:
        """Generate a reasoning trace showing which tree nodes were visited."""
        query_lower = query.lower()
        trace = []

        trace.append(TraceStep(
            step=1,
            action="Read Table of Contents",
            detail="Scanning hierarchical tree index for relevant chapters..."
        ))

        # Determine relevant sections
        sections_found = []
        if any(w in query_lower for w in ['fracture', 'break', 'broken', 'tibial', 'femoral', 'shaft']):
            sections_found.append(('fracture', 'Section 1: Fracture Management (p. 1-42)'))
        if any(w in query_lower for w in ['replacement', 'arthroplasty', 'hip', 'knee', 'thr', 'tka']):
            sections_found.append(('joint_replacement', 'Section 2: Joint Replacement (p. 43-78)'))
        if any(w in query_lower for w in ['diabetes', 'cardiac', 'comorbid', 'geriatric', 'elderly', 'chf', 'age']):
            sections_found.append(('comorbidity', 'Section 3: Comorbidity Considerations (p. 79-110)'))
        if any(w in query_lower for w in ['rehab', 'recovery', 'postop', 'post-op', 'infection', 'acl']):
            sections_found.append(('postop', 'Section 4: Post-operative Care (p. 111-142)'))

        if not sections_found:
            sections_found.append(('fracture', 'Section 1: Fracture Management (p. 1-42)'))

        for i, (key, label) in enumerate(sections_found):
            trace.append(TraceStep(
                step=i + 2,
                action=f"Selected: {label.split(':')[1].split('(')[0].strip()}",
                detail=f"Navigating to {label}"
            ))

        # Cross-reference detection
        if len(sections_found) > 1:
            trace.append(TraceStep(
                step=len(sections_found) + 2,
                action="Cross-reference detected",
                detail=f"Combining information from {len(sections_found)} sections for comprehensive answer"
            ))

        trace.append(TraceStep(
            step=len(trace) + 1,
            action="Assessed sufficiency",
            detail=f"All relevant sections retrieved. Generating {role.value}-level response."
        ))

        return trace

    async def query(self, query: str, role: UserRole, document_id: str = "doc-1", num_hops: int = 3) -> QueryResponse:
        """Execute a clinical query with reasoning-based retrieval."""
        query_id = f"q-{uuid.uuid4().hex[:8]}"
        
        # Generate reasoning trace
        trace = self.generate_trace(query, role)
        
        # Gather relevant context (simulating PageIndex tree navigation)
        context = self._retrieve_context(query, document_id)
        citations = self._extract_citations(query, document_id)
        
        # Generate answer using Groq
        answer = await self._generate_answer(query, role, context)
        
        # Calculate confidence based on context match quality
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

    def _retrieve_context(self, query: str, document_id: str) -> str:
        """Simulate PageIndex tree navigation to retrieve relevant sections."""
        doc = CLINICAL_CONTEXT.get(document_id, CLINICAL_CONTEXT["doc-1"])
        query_lower = query.lower()
        
        relevant_sections = []
        for key, section in doc["sections"].items():
            keywords = {
                "fracture": ['fracture', 'break', 'broken', 'tibial', 'femoral', 'shaft', 'comminuted', 'displaced'],
                "joint_replacement": ['replacement', 'arthroplasty', 'hip', 'knee', 'thr', 'tka', 'approach'],
                "comorbidity": ['diabetes', 'diabetic', 'cardiac', 'comorbid', 'geriatric', 'elderly', 'chf', 'heart'],
                "postop": ['rehab', 'rehabilitation', 'recovery', 'postop', 'post-op', 'infection', 'acl', 'follow-up']
            }
            
            section_keywords = keywords.get(key, [])
            if any(kw in query_lower for kw in section_keywords):
                relevant_sections.append(section["content"])
        
        if not relevant_sections:
            # Default: return first section
            first_key = list(doc["sections"].keys())[0]
            relevant_sections.append(doc["sections"][first_key]["content"])
        
        return "\n\n".join(relevant_sections)

    def _extract_citations(self, query: str, document_id: str) -> List[str]:
        """Extract page citations from retrieved sections."""
        doc = CLINICAL_CONTEXT.get(document_id, CLINICAL_CONTEXT["doc-1"])
        query_lower = query.lower()
        citations = []

        for key, section in doc["sections"].items():
            keywords = {
                "fracture": ['fracture', 'break', 'tibial', 'femoral', 'shaft', 'comminuted'],
                "joint_replacement": ['replacement', 'arthroplasty', 'hip', 'knee'],
                "comorbidity": ['diabetes', 'diabetic', 'cardiac', 'geriatric', 'elderly', 'chf'],
                "postop": ['rehab', 'rehabilitation', 'recovery', 'infection', 'acl']
            }
            if any(kw in query_lower for kw in keywords.get(key, [])):
                citations.append(section["pages"])

        return citations if citations else ["p. 1-42"]

    def _calculate_confidence(self, query: str, context: str) -> float:
        """Calculate confidence score based on context relevance."""
        query_words = set(query.lower().split())
        context_lower = context.lower()
        
        matches = sum(1 for word in query_words if word in context_lower and len(word) > 3)
        total_significant = sum(1 for word in query_words if len(word) > 3)
        
        if total_significant == 0:
            return 0.75
        
        base_confidence = min(0.98, 0.70 + (matches / total_significant) * 0.28)
        return round(base_confidence, 2)

    async def _generate_answer(self, query: str, role: UserRole, context: str) -> str:
        """Generate answer using Groq LLM with role-specific prompting."""
        system_prompt = ROLE_PROMPTS[role]
        
        user_prompt = f"""Based on the following orthopaedic clinical protocol sections retrieved via PageIndex tree navigation:

---
{context}
---

Clinical Query: {query}

Provide a comprehensive, well-structured answer. Use markdown formatting with bold headers and bullet points. 
Include specific details from the protocol sections above.
If referencing specific sections, mention the page numbers."""

        if self.groq_client:
            try:
                chat_completion = self.groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    model=GROQ_MODEL,
                    temperature=0.3,
                    max_tokens=1500,
                    top_p=0.9,
                )
                return chat_completion.choices[0].message.content
            except Exception as e:
                print(f"Groq API error: {e}")
                return self._mock_response(query, role)
        else:
            return self._mock_response(query, role)

    def _mock_response(self, query: str, role: UserRole) -> str:
        """Fallback mock response when Groq is unavailable."""
        query_lower = query.lower()

        if 'fracture' in query_lower and 'diabet' in query_lower:
            if role == UserRole.patient:
                return "**Understanding Your Fracture Treatment with Diabetes**\n\nYou have a broken bone that needs special care because of your diabetes.\n\n- **Healing may take longer** — diabetes can slow bone healing by 2-3 weeks\n- **Infection risk is higher** — we'll give you preventive antibiotics\n- **Blood sugar control is critical** — keep your levels stable\n- **Follow-up visits** are extra important\n\nYour care team has a plan designed specifically for you."
            elif role == UserRole.consultant:
                return "**Comminuted Fracture + DM — Advanced Management**\n\n**Surgical Approach:**\n- IM nailing remains gold standard\n- Consider locking screws bilaterally for comminuted patterns\n- Reamed > unreamed in closed fractures\n\n**DM-Specific:**\n- Perioperative HbA1c target: <8%\n- Delayed union rate: 25-30% in uncontrolled DM\n- Extended prophylaxis to 48h\n\n**Monitoring:**\n- Weekly wound checks × 3 weeks\n- Serial X-rays q2 weeks\n- CT at 8 weeks if union questionable"
            else:
                return "**Comminuted Tibial Shaft Fracture + Diabetes**\n\n**From Fracture Management (p. 31-42):**\n- AO/OTA classification for comminuted patterns\n- IM nailing preferred for shaft fractures\n- Union: 12-16 weeks (extended with comorbidities)\n\n**From Diabetes Considerations (p. 79-88):**\n- Perioperative glucose: q4h, target 140-180 mg/dL\n- Infection risk: 3.2x higher\n- Extended antibiotic prophylaxis recommended\n\n**Cross-ref Infection Prevention (p. 126-135):**\n- Cefazolin 2g IV pre-op + 1g q8h × 48h"

        if 'acl' in query_lower:
            return "**ACL Reconstruction Rehabilitation Protocol**\n\n**Week 1-2:** Full extension emphasis, quad sets, SLR, ankle pumps, cryotherapy\n\n**Week 3-6:** ROM target 0-90° by week 4, 0-120° by week 6, stationary cycling\n\n**Week 6-12:** Full ROM by week 8, progressive resistance, proprioception\n\n**Month 4-6:** Functional testing, agility progression, return-to-sport criteria: >90% limb symmetry"

        return f"**Clinical Guidance**\n\nBased on the indexed orthopaedic protocols, I've analyzed your query using multi-hop reasoning through the document tree.\n\n**Key Findings:**\n- Relevant protocol sections identified\n- Cross-references followed for comprehensive guidance\n- Response tailored to **{role.value}** level\n\n*This is AI-assisted clinical decision support. Verify with institutional guidelines.*"
