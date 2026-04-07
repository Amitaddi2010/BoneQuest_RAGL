# ============================================================
# BoneQuest v2 — Conversation Context Manager
# ============================================================

import re
from typing import Optional
from sqlalchemy.orm import Session
from models.db_models import ChatSession, ChatMessage


class ConversationManager:
    """
    Extracts and formats conversation context for multi-turn awareness.
    Passes history into the prompt so the AI remembers what was discussed.
    """

    def get_conversation_context(
        self,
        db: Session,
        session_id: str,
        max_messages: int = 8
    ) -> dict:
        """
        Returns structured context from this session's history.
        Includes: formatted history, extracted patient facts.
        """
        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(max_messages)
            .all()
        )
        messages = list(reversed(messages))

        patient_context = self._extract_patient_context(messages)
        formatted = self._format_history(messages)

        return {
            "session_id":        session_id,
            "message_count":     len(messages),
            "formatted_history": formatted,
            "patient_context":   patient_context,
        }

    def build_context_string(self, context: dict) -> str:
        """
        Builds a concise context string to inject into the LLM prompt.
        """
        parts = []

        pc = context.get("patient_context", {})
        if pc.get("age"):
            parts.append(f"Patient age mentioned: {pc['age']}")
        if pc.get("conditions"):
            parts.append(f"Conditions discussed: {', '.join(pc['conditions'])}")
        if pc.get("treatments"):
            parts.append(f"Treatments considered: {', '.join(pc['treatments'])}")

        history = context.get("formatted_history", "")
        if history:
            parts.append(f"\nPrevious exchange (last {context.get('message_count', 0)} messages):\n{history}")

        return "\n".join(parts) if parts else ""

    # ── Private helpers ────────────────────────────────────

    def _format_history(self, messages: list) -> str:
        lines = []
        for m in messages:
            role_label = "Clinician" if m.role == "user" else "BoneQuest"
            # Truncate long messages to keep prompt size manageable
            content = m.content[:300] + "..." if len(m.content) > 300 else m.content
            lines.append(f"{role_label}: {content}")
        return "\n".join(lines)

    def _extract_patient_context(self, messages: list) -> dict:
        """
        Lightweight keyword/regex extraction for patient facts.
        """
        all_text = " ".join(m.content for m in messages if m.role == "user").lower()

        # Age extraction — "65 year", "65yo", "65-year-old", "65 y/o"
        age = None
        age_match = re.search(r'\b(\d{1,3})\s*(?:year[s]?\s*old|yo|y/o|-year-old)\b', all_text)
        if age_match:
            candidate = int(age_match.group(1))
            if 1 <= candidate <= 120:
                age = candidate

        # Condition keywords
        condition_keywords = [
            "diabetes", "diabetic", "dm", "hypertension", "htn",
            "cardiac", "heart failure", "chf", "copd", "renal failure",
            "obesity", "osteoporosis", "rheumatoid", "immunosuppressed",
            "smoker", "smoking", "alcoholic", "malnutrition"
        ]
        conditions = [kw for kw in condition_keywords if kw in all_text]

        # Treatment keywords
        treatment_keywords = [
            "intramedullary nail", "im nail", "plate", "screw", "arthroplasty",
            "total hip", "total knee", "acl", "debridement", "amputation",
            "hemiarthroplasty", "thr", "tka", "fixation", "cast", "splint"
        ]
        treatments = [kw for kw in treatment_keywords if kw in all_text]

        return {
            "age":        age,
            "conditions": list(dict.fromkeys(conditions)),   # deduplicate, preserve order
            "treatments": list(dict.fromkeys(treatments)),
        }


# ── Module-level singleton ─────────────────────────────────
conversation_manager = ConversationManager()
