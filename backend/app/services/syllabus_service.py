from typing import Dict, Any, List
from app.services.gemini_service import GeminiService
from app.prompts.prompts import SYLLABUS_MAPPING_PROMPT

class SyllabusMappingService:
    @classmethod
    def map_syllabus(cls, question_text: str, units: List[Any]) -> Dict[str, Any]:
        if not units:
            return {
                "unit_number": None,
                "unit_title": None,
                "topic_name": None,
                "confidence": None,
                "status": "NOT_EVALUATED",
                "reason": "Syllabus mapping unavailable. Units have not been configured.",
                "evidence": None,
                "analysis_mode": "offline_heuristic",
            }

        s_str = ""
        for u in units:
            s_str += f"Unit {u.unit_number}: {u.unit_title}\n"
            for t in u.topics:
                s_str += f"  - Topic: {t.topic_name}\n"

        prompt = SYLLABUS_MAPPING_PROMPT.format(question_text=question_text, syllabus_list=s_str)
        result = GeminiService.generate_json_completion(prompt)

        if result and "unit_title" in result:
            return result

        # Offline mapping is a suggestion only. Do not default to the first unit.
        selected_unit = None
        selected_topic = None
        best_overlap = 0
        matched_terms = []
        for u in units:
            for t in u.topics:
                words = {w for w in t.topic_name.lower().split() if len(w) > 3}
                overlap = words & set(question_text.lower().split())
                if len(overlap) > best_overlap:
                    best_overlap = len(overlap)
                    selected_unit = u
                    selected_topic = t
                    matched_terms = sorted(overlap)

        return {
            "unit_number": selected_unit.unit_number if selected_unit and best_overlap > 0 else None,
            "unit_title": selected_unit.unit_title if selected_unit and best_overlap > 0 else None,
            "topic_name": selected_topic.topic_name if selected_topic and best_overlap > 0 else None,
            "confidence": None,
            "status": "SUGGESTED" if best_overlap > 0 else "NOT_EVALUATED",
            "reason": "Offline keyword overlap suggestion; verify the syllabus mapping manually." if best_overlap > 0 else "No distinctive syllabus terms matched this question.",
            "evidence": matched_terms or None,
            "analysis_mode": "offline_heuristic",
        }
