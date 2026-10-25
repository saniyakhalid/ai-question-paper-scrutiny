import os
import sys
import pytest

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__))))

from app.services.question_parser import QuestionParserService
from app.rules.rule_engine import rule_engine
from app.services.report_service import report_service
from app.schemas.schemas import ExamPatternBase
from app.services.similarity_service import SimilarityService

def test_question_parser():
    sample_text = """
    Q1(a) Explain Decision Tree algorithm and Information Gain. [10 Marks]
    Q1(b) Describe Gradient Descent for Linear Regression. [10 Marks]
    Q2(a) Explain Random Forest algorithm. [10 Marks]
    -- OR --
    Q2(b) Explain Support Vector Machines. [10 Marks]
    """
    questions = QuestionParserService.parse_paper(sample_text)
    assert len(questions) >= 3
    assert questions[0]["question_number"] == "Q.1(a)"
    assert questions[0]["marks"] == 10
    assert "Decision Tree" in questions[0]["question_text"]

def test_rule_engine_marks_and_coverage():
    questions = [
        {"question_number": "Q1", "marks": 20, "internal_choice": False},
        {"question_number": "Q2", "marks": 20, "internal_choice": False},
        {"question_number": "Q3", "marks": 20, "internal_choice": False},
        {"question_number": "Q4", "marks": 20, "internal_choice": False},
        {"question_number": "Q5", "marks": 20, "internal_choice": False}
    ]
    subject_config = {
        "total_marks": 100,
        "duration_minutes": 180,
        "min_co_coverage_pct": 80.0,
        "min_unit_coverage_pct": 80.0,
        "course_outcomes": [{"co_code": "CO1"}, {"co_code": "CO2"}, {"co_code": "CO3"}, {"co_code": "CO4"}, {"co_code": "CO5"}],
        "syllabus_units": [{"unit_number": 1}, {"unit_number": 2}, {"unit_number": 3}, {"unit_number": 4}, {"unit_number": 5}]
    }

    bloom_findings = [{"bloom_level": "Apply"}, {"bloom_level": "Analyze"}, {"bloom_level": "Understand"}, {"bloom_level": "Evaluate"}, {"bloom_level": "Create"}]
    co_findings = [{"co_code": "CO1"}, {"co_code": "CO2"}, {"co_code": "CO3"}, {"co_code": "CO4"}, {"co_code": "CO5"}]
    syllabus_findings = [{"unit_number": 1}, {"unit_number": 2}, {"unit_number": 3}, {"unit_number": 4}, {"unit_number": 5}]

    rules = rule_engine.validate_paper(
        questions=questions,
        subject_config=subject_config,
        bloom_findings=bloom_findings,
        co_findings=co_findings,
        syllabus_findings=syllabus_findings,
        estimated_solving_time_minutes=150.0
    )

    total_marks_rule = next(r for r in rules if r["rule_name"] == "Total Marks Verification")
    assert total_marks_rule["status"] == "PASS"
    
    time_rule = next(r for r in rules if r["rule_name"] == "Solving Time Estimation Check")
    assert time_rule["status"] == "PASS"

def test_report_score_calculator():
    rules = [
        {"rule_name": "Total Marks Verification", "status": "PASS"},
        {"rule_name": "Question Numbering Consistency", "status": "PASS"},
        {"rule_name": "Course Outcome (CO) Coverage", "status": "PASS"},
        {"rule_name": "Selected Unit Syllabus Coverage", "status": "PASS"},
        {"rule_name": "Exam Unit Selection Compliance", "status": "PASS"},
    ]
    findings = [
        {"finding_type": "GRAMMAR", "ai_value": "None", "question_id": 1},
        {"finding_type": "GRAMMAR", "ai_value": "None", "question_id": 2}
    ]
    result = report_service.calculate_score_breakdown(rules, findings)
    assert result["overall_score"] == 100.0
    assert result["evidence_coverage_pct"] == 55.0
    assert result["rating"] == "Partial evaluation"
    assert result["categories"]["bloom_distribution"]["score"] is None
    assert result["categories"]["similarity"]["score"] is None


def test_missing_core_evidence_does_not_produce_an_overall_score():
    result = report_service.calculate_score_breakdown([], [])
    assert result["overall_score"] is None
    assert result["rating"] == "Insufficient evidence"
    assert result["evidence_coverage_pct"] == 0
    assert all(category["score"] is None for category in result["categories"].values())


def test_institutional_policy_thresholds_are_not_invented_by_schema_defaults():
    rules = ExamPatternBase()
    assert rules.min_co_coverage_pct is None
    assert rules.min_unit_coverage_pct is None
    assert rules.min_higher_order_bloom_pct is None
    assert rules.internal_choice_required is None


def test_configured_exam_marks_are_authoritative_over_paper_header():
    rules = rule_engine.validate_paper(
        questions=[{"question_number": "Q1", "marks": 100}],
        subject_config={"total_marks": 80, "declared_total_marks": 100},
        bloom_findings=[], co_findings=[], syllabus_findings=[],
        estimated_solving_time_minutes=None,
    )
    marks_rule = next(rule for rule in rules if rule["rule_name"] == "Total Marks Verification")
    assert marks_rule["expected"] == "80 Marks"
    assert marks_rule["status"] == "FAIL"


def test_historical_similarity_respects_configured_threshold():
    service = SimilarityService()
    question = "Explain decision tree entropy and information gain"
    previous = [{"id": 1, "question_text": "Explain decision tree entropy and information gain", "paper_title": "Mid Term 2024"}]
    res = service.find_similar_questions(question, previous, threshold=0.95)
    assert res
    assert res[0]["matched_paper_title"] == "Mid Term 2024"
    assert "Mid Term 2024" in res[0]["explanation"]
    assert service.find_similar_questions(question, previous, threshold=1.01) == []


def test_selected_units_co_coverage_and_unit_compliance():
    # Only units [1, 2] selected out of 4 units
    subject_config = {
        "total_marks": 50,
        "declared_total_marks": 50,
        "duration_minutes": 120,
        "min_co_coverage_pct": 80.0,
        "min_unit_coverage_pct": 80.0,
        "course_outcomes": [
            {"co_code": "CO1", "description": "Unit 1 outcome"},
            {"co_code": "CO2", "description": "Unit 2 outcome"},
            {"co_code": "CO3", "description": "Unit 3 outcome"},
            {"co_code": "CO4", "description": "Unit 4 outcome"},
        ],
        "syllabus_units": [
            {"unit_number": 1, "title": "Unit 1"},
            {"unit_number": 2, "title": "Unit 2"},
            {"unit_number": 3, "title": "Unit 3"},
            {"unit_number": 4, "title": "Unit 4"},
        ]
    }
    questions = [
        {"question_number": "Q.1", "question_type": "QUESTION_GROUP", "marks": 25},
        {"question_number": "Q.1(a)", "question_type": "SUBQUESTION", "marks": 25, "parent_number": "Q.1"},
        {"question_number": "Q.2", "question_type": "QUESTION_GROUP", "marks": 25},
        {"question_number": "Q.2(a)", "question_type": "SUBQUESTION", "marks": 25, "parent_number": "Q.2"},
    ]
    co_findings = [{"co_code": "CO1"}, {"co_code": "CO2"}]
    syllabus_findings = [{"unit_number": 1}, {"unit_number": 2}]

    rules = rule_engine.validate_paper(
        questions=questions,
        subject_config=subject_config,
        bloom_findings=[],
        co_findings=co_findings,
        syllabus_findings=syllabus_findings,
        estimated_solving_time_minutes=None,
        selected_units=[1, 2]
    )

    co_rule = next(r for r in rules if r["rule_name"] == "Course Outcome (CO) Coverage")
    # Both applicable COs (CO1, CO2) are covered -> 100% -> PASS
    assert co_rule["status"] == "PASS"
    assert "2 COs total" in co_rule["expected"]

    unit_rule = next(r for r in rules if r["rule_name"] == "Selected Unit Syllabus Coverage")
    assert unit_rule["status"] == "PASS"

    compliance_rule = next(r for r in rules if r["rule_name"] == "Exam Unit Selection Compliance")
    assert compliance_rule["status"] == "PASS"

    marks_rule = next(r for r in rules if r["rule_name"] == "Total Marks Verification")
    assert marks_rule["status"] == "PASS"
    assert marks_rule["expected"] == "50 Marks"

