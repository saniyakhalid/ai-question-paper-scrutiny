from typing import Dict, Any
from app.services.gemini_service import GeminiService
from app.prompts.prompts import QUALITY_PROMPT

class QuestionQualityService:
    @classmethod
    def evaluate_quality(cls, question_text: str, marks: int) -> Dict[str, Any]:
        prompt = QUALITY_PROMPT.format(question_text=question_text, marks=marks)
        result = GeminiService.generate_json_completion(prompt)

        if result and "quality_score" in result:
            return result

        return {
            "quality_score": None,
            "confidence": None,
            "status": "NOT_EVALUATED",
            "reason": "Question-quality evaluation requires a configured AI provider response.",
            "issues": [],
            "recommendation": None,
            "analysis_mode": "offline_heuristic",
        }
