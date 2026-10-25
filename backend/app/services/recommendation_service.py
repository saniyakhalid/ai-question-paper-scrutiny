from typing import List, Dict, Any

class ActionableRecommendationService:
    @classmethod
    def generate_recommendations(
        cls, rule_results: List[Dict[str, Any]], bloom_counts: Dict[str, int], total_questions: int
    ) -> List[Dict[str, Any]]:
        recs = []
        
        # Check syllabus / CO rule results
        for r in rule_results:
            if r.get("status") in ["FAIL", "WARNING"]:
                recs.append({
                    "finding": f"Rule Defect: {r['rule_name']}",
                    "evidence": f"Expected {r['expected']}, got {r['actual']}.",
                    "recommendation": f"Review paper composition to resolve {r['rule_name'].lower()} violation.",
                    "confidence": None
                })

        if not recs:
            evaluated = [r for r in rule_results if r.get("status") in {"PASS", "WARNING", "FAIL"}]
            if evaluated and all(r.get("status") == "PASS" for r in evaluated):
                recs.append({
                    "finding": "No warnings were produced by evaluated checks.",
                    "evidence": f"{len(evaluated)} configured check(s) were evaluated; unavailable checks are not included.",
                    "recommendation": "Review the report and retain moderator oversight before finalizing the paper.",
                    "confidence": None,
                })
            else:
                recs.append({
                    "finding": "No evidence-based recommendation is available.",
                    "evidence": "Relevant checks may be unconfigured or not evaluated.",
                    "recommendation": "Review unavailable checks and configure the required subject or examination data.",
                    "confidence": None,
                })

        return recs
