# ============================================================
# BoneQuest v2 — Groq Vision Analyzer
# ============================================================

import base64
import json
from typing import Optional
from config import settings


class GroqVisionAnalyzer:
    """
    Analyze orthopaedic medical images using Groq vision models.
    CRITICAL: All analyses flagged as PENDING_RADIOLOGIST_REVIEW.
    """

    def __init__(self):
        self.client = None
        self.model = settings.GROQ_VISION_MODEL
        self._init_client()

    def _init_client(self):
        try:
            from groq import Groq
            self.client = Groq(api_key=settings.GROQ_API_KEY)
        except Exception as e:
            print(f"⚠️  Groq vision init failed: {e}")
            self.client = None

    async def analyze_image(
        self,
        image_bytes: bytes,
        filename: str,
        content_type: str,
        specific_query: Optional[str] = None
    ) -> dict:
        """
        Analyze a medical image using Groq vision.
        Returns structured findings with mandatory radiologist review flag.
        """

        # Encode image
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        mime_type = content_type or "image/jpeg"

        # Build analysis prompt
        analysis_prompt = f"""You are analyzing an orthopaedic medical image ({filename}).

Please provide your analysis in the following JSON format:
{{
    "image_type": "X-ray|MRI|CT|Ultrasound|Unknown",
    "anatomical_region": "description of anatomical region shown",
    "findings": [
        {{
            "name": "finding name",
            "confidence": 0.0-1.0,
            "description": "detailed description"
        }}
    ],
    "differential_considerations": ["condition 1", "condition 2"],
    "recommendations": ["recommendation 1", "recommendation 2"],
    "image_quality": "good|fair|poor",
    "limitations": "any limitations in the analysis"
}}

{f'SPECIFIC QUESTION: {specific_query}' if specific_query else ''}

CRITICAL: This is AI feature extraction only. All findings must be validated
by a qualified radiologist before clinical use. Respond ONLY with valid JSON."""

        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": analysis_prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{mime_type};base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    temperature=0.3,
                    max_tokens=1500,
                )

                raw_text = response.choices[0].message.content
                parsed = self._parse_response(raw_text)

                return {
                    "raw_analysis": raw_text,
                    "image_type": parsed.get("image_type", "Unknown"),
                    "anatomical_region": parsed.get("anatomical_region", ""),
                    "findings": parsed.get("findings", []),
                    "recommendations": parsed.get("recommendations", []),
                    "confidence_score": 0.0,  # Zero until radiologist validates
                    "validation_status": "pending_review",
                    "ai_disclaimer": "This analysis is for educational purposes only. Clinical decisions must be based on radiologist interpretation.",
                }

            except Exception as e:
                print(f"Groq vision error: {e}")
                return self._mock_analysis(filename, specific_query)
        else:
            return self._mock_analysis(filename, specific_query)

    def _parse_response(self, text: str) -> dict:
        """Parse vision model JSON response."""
        try:
            # Try to extract JSON from response
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
        return {}

    def _mock_analysis(self, filename: str, query: Optional[str] = None) -> dict:
        """Fallback mock analysis when Groq is unavailable."""
        return {
            "raw_analysis": f"Mock analysis for {filename}. Groq vision model unavailable.",
            "image_type": "X-ray",
            "anatomical_region": "Lower extremity",
            "findings": [
                {"name": "Image received", "confidence": 1.0, "description": f"Image {filename} uploaded successfully. Vision model offline — analysis pending."}
            ],
            "recommendations": [
                "Resubmit when vision model is available",
                "Consult radiologist for immediate interpretation"
            ],
            "confidence_score": 0.0,
            "validation_status": "pending_review",
            "ai_disclaimer": "This analysis is for educational purposes only. Clinical decisions must be based on radiologist interpretation.",
        }


vision_analyzer = GroqVisionAnalyzer()
