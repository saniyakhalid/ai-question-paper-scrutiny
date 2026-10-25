from typing import Dict, Any
from app.services.gemini_service import GeminiService
from app.prompts.prompts import BLOOM_PROMPT

class BloomClassificationService:
    @classmethod
    def classify_question(cls, question_text: str, marks: int) -> Dict[str, Any]:
        prompt = BLOOM_PROMPT.format(question_text=question_text, marks=marks)
        result = GeminiService.generate_json_completion(prompt)
        
        if result and "bloom_level" in result:
            return result

        # Offline action-verb suggestion; do not infer factual recall by default.
        lower_q = question_text.lower()
        if any(w in lower_q for w in ["design", "develop", "create", "construct"]):
            level = "Create"
        elif any(w in lower_q for w in ["evaluate", "compare", "assess", "justify"]):
            level = "Evaluate"
        elif any(w in lower_q for w in ["analyze", "differentiate", "examine", "classify"]):
            level = "Analyze"
        elif any(w in lower_q for w in ["apply", "solve", "calculate", "implement"]):
            level = "Apply"
        elif any(w in lower_q for w in ["explain", "describe", "discuss", "interpret"]):
            level = "Understand"
        else:
            level = None

        return {
            "bloom_level": level,
            "confidence": None,
            "status": "SUGGESTED" if level else "NOT_EVALUATED",
            "reason": f"Offline action-verb suggestion: {level}. Verify the cognitive demand manually." if level else "No supported Bloom action verb was detected; manual classification is required.",
            "evidence": [w for w in ["design", "develop", "create", "construct", "evaluate", "compare", "assess", "justify", "analyze", "differentiate", "examine", "classify", "apply", "solve", "calculate", "implement", "explain", "describe", "discuss", "interpret"] if w in lower_q],
            "analysis_mode": "offline_heuristic",
        }
