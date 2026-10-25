import os
import json
import csv
import io
from typing import Dict, Any, List, Optional
from app.models.models import RuleStatus

class ReportService:
    @staticmethod
    def calculate_score_breakdown(
        rule_results: List[Dict[str, Any]],
        findings: List[Dict[str, Any]],
        similarity_results: Optional[List[Dict[str, Any]]] = None,
        similarity_available: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Transparent deterministic scoring system based on actual scrutiny evidence:
        1. Marks & Pattern Compliance: 15 pts
        2. Question Numbering: 5 pts
        3. Bloom Cognitive Distribution: 15 pts
        4. CO Coverage: 15 pts
        5. Unit Coverage & Compliance: 20 pts
        6. Grammar & Question Quality: 10 pts
        7. Similarity / Duplicate Detection: 10 pts
        8. Time Feasibility: 5 pts
        9. Choice Pattern: 5 pts
        Total: 100 pts
        """
        rules_by_name = {r.get("rule_name", ""): r for r in rule_results}

        def rule_points(name: str, maximum: float, warning_fraction: float = 0.8):
            rule = rules_by_name.get(name)
            if not rule or rule.get("status") not in {"PASS", "WARNING", "FAIL"}:
                return {"score": None, "max": maximum, "status": "NOT_EVALUATED"}
            state = rule["status"]
            earned = maximum if state == "PASS" else maximum * warning_fraction if state == "WARNING" else 0.0
            return {"score": round(earned, 1), "max": maximum, "status": state}

        marks = rule_points("Total Marks Verification", 15)
        numbering = rule_points("Question Numbering Consistency", 5)
        bloom = rule_points("Bloom's Cognitive Distribution", 15)
        co = rule_points("Course Outcome (CO) Coverage", 15)

        unit_rules = [
            rules_by_name.get("Selected Unit Syllabus Coverage"),
            rules_by_name.get("Exam Unit Selection Compliance"),
        ]
        unit_rules = [r for r in unit_rules if r and r.get("status") in {"PASS", "WARNING", "FAIL"}]
        if unit_rules:
            unit_fraction = sum(
                1.0 if r["status"] == "PASS" else 0.8 if r["status"] == "WARNING" else 0.0
                for r in unit_rules
            ) / len(unit_rules)
            unit = {"score": round(20.0 * unit_fraction, 1), "max": 20, "status": "EVALUATED"}
        else:
            unit = {"score": None, "max": 20, "status": "NOT_EVALUATED"}

        quality_findings = [
            f for f in findings
            if f.get("finding_type") in ("GRAMMAR", "QUALITY")
            and str(f.get("ai_value", "")).upper() in {"PASS", "WARNING", "FAIL"}
        ]
        if quality_findings:
            quality_fraction = sum(
                1.0 if str(f["ai_value"]).upper() == "PASS"
                else 0.8 if str(f["ai_value"]).upper() == "WARNING" else 0.0
                for f in quality_findings
            ) / len(quality_findings)
            quality = {"score": round(10.0 * quality_fraction, 1), "max": 10, "status": "EVALUATED"}
        else:
            quality = {"score": None, "max": 10, "status": "NOT_EVALUATED"}

        # Similarity is evaluable only when the subject has historical papers to compare.
        sim_scores = [
            s.get("similarity_score", 0.0)
            for s in (similarity_results or [])
            if s.get("similarity_score") is not None
        ]
        max_sim = max(sim_scores) if sim_scores else 0.0
        if similarity_available is False:
            similarity = {"score": None, "max": 10, "status": "NOT_EVALUATED"}
        elif similarity_available is True and max_sim >= 0.85:
            similarity = {"score": 7.5, "max": 10, "status": "WARNING"}
        elif similarity_available is True and max_sim >= 0.60:
            similarity = {"score": 8.5, "max": 10, "status": "WARNING"}
        elif similarity_available is True:
            similarity = {"score": 10.0, "max": 10, "status": "PASS"}
        else:
            similarity = {"score": None, "max": 10, "status": "NOT_EVALUATED"}

        time_score = rule_points("Solving Time Estimation Check", 5)
        choice_score = rule_points("Internal Choice Validation", 5)

        categories = {
            "marks_compliance": marks,
            "numbering": numbering,
            "bloom_distribution": bloom,
            "co_coverage": co,
            "unit_coverage": unit,
            "grammar_quality": quality,
            "similarity": similarity,
            "time_feasibility": time_score,
            "choice_pattern": choice_score,
        }
        evaluated = [c for c in categories.values() if c["score"] is not None]
        available_weight = sum(c["max"] for c in evaluated)
        earned_weight = sum(c["score"] for c in evaluated)
        unit_coverage_rule = rules_by_name.get("Selected Unit Syllabus Coverage")
        core_evidence_available = all(
            categories[key]["score"] is not None
            for key in ("marks_compliance", "numbering", "co_coverage")
        ) and bool(unit_coverage_rule and unit_coverage_rule.get("status") in {"PASS", "WARNING", "FAIL"})
        total = round((earned_weight / available_weight) * 100.0, 1) if available_weight and core_evidence_available else None
        coverage_pct = round(available_weight, 1)  # Rubric weights sum to 100.

        if total is None:
            rating = "Insufficient evidence"
        elif coverage_pct < 100:
            rating = "Partial evaluation"
        elif total >= 90.0:
            rating = "Excellent"
        elif total >= 80.0:
            rating = "Good"
        elif total >= 70.0:
            rating = "Needs Review"
        elif total >= 60.0:
            rating = "Needs Modification"
        else:
            rating = "Poor / Major Issues"

        return {
            "overall_score": total,
            "rating": rating,
            "categories": categories,
            "available_weight": available_weight,
            "evidence_coverage_pct": coverage_pct,
            "core_evidence_available": core_evidence_available,
        }

    @staticmethod
    def calculate_scrutiny_score(
        rule_results: List[Dict[str, Any]],
        findings: List[Dict[str, Any]],
        similarity_results: Optional[List[Dict[str, Any]]] = None,
        similarity_available: Optional[bool] = None,
    ) -> Optional[float]:
        breakdown = ReportService.calculate_score_breakdown(
            rule_results, findings, similarity_results, similarity_available
        )
        return breakdown["overall_score"]

    @staticmethod
    def generate_csv_export(report_dict: Dict[str, Any]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 1. Header Information
        writer.writerow(["AUTONOMOUS ENGINEERING COLLEGE - QUESTION PAPER SCRUTINY REPORT"])
        writer.writerow(["Paper Title", report_dict.get("paper_title") or f"Paper #{report_dict.get('paper_id')}"])
        writer.writerow(["Subject Code", report_dict.get("subject_code")])
        writer.writerow(["Subject Name", report_dict.get("subject_name")])
        writer.writerow(["Academic Year", report_dict.get("academic_year", "2025-2026")])
        writer.writerow(["Exam Type", report_dict.get("exam_type", "Regular")])
        score = report_dict.get("overall_score")
        writer.writerow(["Scrutiny Score", f"{score:.1f}/100" if isinstance(score, (int, float)) else "N/A"])
        writer.writerow(["Evaluation Coverage", report_dict.get("evidence_coverage_pct", "N/A")])
        writer.writerow(["Analysis Mode", report_dict.get("analysis_mode", "N/A")])
        writer.writerow(["Analysis Notice", report_dict.get("analysis_notice", "N/A")])
        writer.writerow(["Paper Status", report_dict.get("status")])
        writer.writerow([])
        
        # 2. Moderator Review
        writer.writerow(["MODERATOR SUPERVISION & DECISION"])
        writer.writerow(["Decision", report_dict.get("decision", "PENDING REVIEW")])
        writer.writerow(["Moderator Remarks", report_dict.get("remarks", "N/A")])
        writer.writerow(["Required Action", report_dict.get("required_action", "N/A")])
        writer.writerow(["Reviewed By", report_dict.get("moderator_name", "N/A")])
        writer.writerow([])

        # 3. Question Breakdown
        if report_dict.get("questions_breakdown"):
            writer.writerow(["QUESTION BREAKDOWN & SYLLABUS MAPPING"])
            writer.writerow(["Q.No", "Marks", "Bloom Level", "CO Code", "Unit / Topic", "Question Text"])
            for q in report_dict.get("questions_breakdown", []):
                writer.writerow([
                    q.get("q_num"),
                    q.get("marks") if q.get("marks") is not None else "—",
                    q.get("bloom"),
                    q.get("co"),
                    q.get("unit_topic"),
                    q.get("question_text", "")
                ])
            writer.writerow([])

        # 4. Rule Validation Results
        writer.writerow(["RULE VALIDATION RESULTS"])
        writer.writerow(["Category", "Rule Name", "Expected", "Actual", "Status", "Message"])
        for r in report_dict.get("rule_results", []):
            writer.writerow([
                r.get("category"),
                r.get("rule_name"),
                r.get("expected_value"),
                r.get("actual_value"),
                r.get("status"),
                r.get("message")
            ])
        writer.writerow([])

        # 5. Question Analysis Findings
        if report_dict.get("findings"):
            writer.writerow(["QUESTION ANALYSIS FINDINGS"])
            writer.writerow(["Question Number", "Finding Type", "AI Value", "Confidence", "Reasoning"])
            for f in report_dict.get("findings", []):
                writer.writerow([
                    f.get("question_number"),
                    f.get("finding_type"),
                    f.get("ai_value"),
                    f.get("confidence"),
                    f.get("reasoning")
                ])

        return output.getvalue()

    @staticmethod
    def generate_json_export(report_dict: Optional[Dict[str, Any]] = None, **kwargs) -> str:
        data = dict(report_dict) if report_dict is not None else kwargs
        return json.dumps(data, indent=2, default=str)

report_service = ReportService()
ScrutinyReportService = ReportService

