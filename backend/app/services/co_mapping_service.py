from typing import Dict, Any, List
from app.services.gemini_service import GeminiService
from app.prompts.prompts import CO_MAPPING_PROMPT

class COMappingService:
    @classmethod
    def map_co(cls, question_text: str, course_outcomes: List[Any]) -> Dict[str, Any]:
        if not course_outcomes:
            return {
                "co_code": None,
                "confidence": None,
                "status": "NOT_EVALUATED",
                "reason": "CO mapping unavailable. Course Outcomes have not been configured.",
                "evidence": None,
                "analysis_mode": "offline_heuristic",
            }

        co_str = "\n".join([f"- {co.co_code}: {co.description}" for co in course_outcomes])
        prompt = CO_MAPPING_PROMPT.format(question_text=question_text, co_list=co_str)
        result = GeminiService.generate_json_completion(prompt)

        if result and "co_code" in result:
            return result

        # Offline keyword overlap is only a suggestion; no match stays unmapped.
        selected_co = None
        matched_terms = []
        best_overlap = 0
        for co in course_outcomes:
            words = {w for w in co.description.lower().split() if len(w) > 4}
            overlap = words & set(question_text.lower().split())
            if len(overlap) > best_overlap:
                best_overlap = len(overlap)
                selected_co = co
                matched_terms = sorted(overlap)

        return {
            "co_code": selected_co.co_code if selected_co and best_overlap > 0 else None,
            "confidence": None,
            "status": "SUGGESTED" if best_overlap > 0 else "NOT_EVALUATED",
            "reason": "Offline keyword overlap suggestion; verify this mapping manually." if best_overlap > 0 else "No distinctive CO terms matched this question.",
            "evidence": matched_terms or None,
            "analysis_mode": "offline_heuristic",
        }
