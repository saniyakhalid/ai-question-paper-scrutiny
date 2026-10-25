"""
Automated regression tests for the deterministic question-paper parser.
"""
import os
import sys
import pytest

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__))))

from app.services.question_parser import QuestionParserService
from app.services.extraction_service import DocumentExtractionService, ScannedDocumentException
from app.rules.rule_engine import rule_engine


ADCET_SAMPLE = """
ANNASAHEB DANGE COLLEGE OF ENGINEERING AND TECHNOLOGY
Mid Semester Examination
Total Marks:- 32

Instructions:
1. All questions are compulsory.
2. Make suitable assumptions wherever necessary, and mention them clearly in the answer book.
3. Figures to the right indicate full marks and Course Outcome [CO] and Bloom's Taxonomy.
4. Draw neat diagrams whenever necessary.

Q.1 Solve the following questions [16]
a) With neat diagram explain different types of security attacks. 08 [1] K2
b) Apply play fair cipher for following example Keyword: MONARCHY Encrypt the Plaintext: INFORMATION AND NETWORK SECURITY 08 [1] K3

Q.2 Solve the following questions [16]
a) Explain OSI model layers. 08 [2] K2
OR
a) Differentiate between symmetric and asymmetric cryptography. 08 [2] K4
"""


def test_1_general_instructions_not_questions():
    detailed = QuestionParserService.parse_paper_detailed(ADCET_SAMPLE)
    texts = " ".join(q["question_text"].lower() for q in detailed["questions"])
    assert "all questions are compulsory" not in texts
    assert "make suitable assumptions" not in texts
    assert "figures to the right" not in texts
    assert "draw neat diagrams" not in texts
    assert len(detailed["instructions"]) >= 4


def test_2_q1a_with_marks():
    text = "Q.1(a) With neat diagram explain different types of security attacks. [08]"
    qs = QuestionParserService.parse_paper(text)
    assert len(qs) == 1
    assert qs[0]["question_number"] == "Q.1(a)"
    assert qs[0]["marks"] == 8
    assert "08" not in qs[0]["question_text"]
    assert "[08]" not in qs[0]["question_text"]


def test_3_q1a_with_co_and_bloom():
    text = "a) With neat diagram explain different types of security attacks. 08 [1] K2"
    # Need parent context
    paper = "Q.1 Solve the following questions [16]\n" + text
    qs = QuestionParserService.parse_paper(paper)
    assert len(qs) == 1
    assert qs[0]["question_number"] == "Q.1(a)"
    assert qs[0]["marks"] == 8
    assert qs[0]["co_code"] == "CO1"
    assert qs[0]["bloom_level"] == "K2"
    assert "K2" not in qs[0]["question_text"]
    assert "[1]" not in qs[0]["question_text"]


def test_4_question_group_with_total_marks():
    detailed = QuestionParserService.parse_paper_detailed(ADCET_SAMPLE)
    groups = detailed["question_groups"]
    assert any(g["group_number"] == "Q.1" and g["group_total_marks"] == 16 for g in groups)
    # Group total must not become a fake child question with marks=5
    for q in detailed["questions"]:
        assert q["marks"] != 5 or "compulsory" not in q["question_text"].lower()
        assert q["question_type"] in ("QUESTION", "SUBQUESTION")


def test_5_internal_choice():
    detailed = QuestionParserService.parse_paper_detailed(ADCET_SAMPLE)
    choices = [q for q in detailed["questions"] if q.get("internal_choice")]
    assert len(choices) >= 1
    assert choices[0].get("choice_group_id")


def test_6_different_numbering_styles():
    samples = [
        ("Q.1(a) Explain hashing. [5 Marks]", "Q.1(a)", 5),
        ("Q1(a) Explain hashing. [5 Marks]", "Q.1(a)", 5),
        ("Q. 1\na) Explain hashing. [5]\n", "Q.1(a)", 5),
        ("1(a) Explain hashing. 5M\n", "Q.1(a)", 5),
    ]
    for text, expected_num, expected_marks in samples:
        qs = QuestionParserService.parse_paper(text)
        assert qs, f"Failed to parse: {text}"
        assert qs[0]["question_number"] == expected_num
        assert qs[0]["marks"] == expected_marks


def test_7_missing_marks_is_null():
    text = "Q.1(a) Explain different types of firewalls without any trailing marks metadata."
    qs = QuestionParserService.parse_paper(text)
    assert len(qs) == 1
    assert qs[0]["marks"] is None


def test_8_marks_written_as_5m():
    text = "Q.1(a) Define cryptography. 5M"
    qs = QuestionParserService.parse_paper(text)
    assert qs[0]["marks"] == 5
    assert "5M" not in qs[0]["question_text"]


def test_9_marks_written_as_bracket_5():
    text = "Q.1(a) Define cryptography. [5]"
    qs = QuestionParserService.parse_paper(text)
    assert qs[0]["marks"] == 5


def test_10_marks_written_as_bracket_05():
    text = "Q.1(a) Define cryptography. [05]"
    qs = QuestionParserService.parse_paper(text)
    assert qs[0]["marks"] == 5


def test_11_co_bloom_metadata_not_confused_with_marks():
    text = "Q.1(a) Apply playfair cipher. 08 [1] K3"
    qs = QuestionParserService.parse_paper(text)
    assert qs[0]["marks"] == 8
    assert qs[0]["co_code"] == "CO1"
    assert qs[0]["bloom_level"] == "K3"
    # [1] must never be interpreted as 1 mark
    assert qs[0]["marks"] != 1


def test_12_empty_extraction_raises_or_returns_no_questions():
    detailed = QuestionParserService.parse_paper_detailed("")
    assert detailed["questions"] == []
    assert detailed["parse_warnings"]


def test_13_multiple_sections():
    text = """
SECTION A
Q.1(a) Explain TCP/IP model. [10 Marks]
SECTION B
Q.2(a) Explain UDP protocol. [10 Marks]
"""
    qs = QuestionParserService.parse_paper(text)
    assert len(qs) == 2
    assert qs[0]["section_name"].startswith("SECTION")
    assert qs[1]["section_name"].startswith("SECTION")


def test_14_subject_unit_mapping_null_when_weak():
    from app.services.gemini_service import GeminiService
    svc = GeminiService()
    results = svc._semantic_heuristic_analysis(
        "CS301",
        "Machine Learning",
        [{"co_code": "CO1", "description": "Understand supervised learning algorithms"}],
        [{"unit_number": 1, "title": "Supervised Learning", "topics": [{"topic_name": "Decision Trees"}]}],
        [{"question_number": "Q.1(a)", "question_text": "Explain decision tree entropy and information gain.", "marks": 10}],
        selected_units=[1],
    )
    assert results[0]["unit_number"] in (1, None)
    # Should not invent unrelated unit randomly when mapping is strong enough for trees
    assert results[0]["bloom_level"] in ("K2", "K1", "K4")


def test_15_no_default_five_marks_on_instructions():
    detailed = QuestionParserService.parse_paper_detailed(ADCET_SAMPLE)
    for q in detailed["questions"]:
        assert "compulsory" not in q["question_text"].lower()
        # Real ADCET subquestions should be 8, not fabricated 5
        if q["question_number"].startswith("Q.1"):
            assert q["marks"] == 8


def test_legacy_demo_paper_q1a_format():
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
        {"question_number": "Q1", "marks": 20, "internal_choice": False, "question_type": "QUESTION"},
        {"question_number": "Q2", "marks": 20, "internal_choice": False, "question_type": "QUESTION"},
        {"question_number": "Q3", "marks": 20, "internal_choice": False, "question_type": "QUESTION"},
        {"question_number": "Q4", "marks": 20, "internal_choice": False, "question_type": "QUESTION"},
        {"question_number": "Q5", "marks": 20, "internal_choice": False, "question_type": "QUESTION"},
    ]
    subject_config = {
        "total_marks": 100,
        "duration_minutes": 180,
        "min_co_coverage_pct": 80.0,
        "min_unit_coverage_pct": 80.0,
        "course_outcomes": [{"co_code": "CO1"}, {"co_code": "CO2"}, {"co_code": "CO3"}, {"co_code": "CO4"}, {"co_code": "CO5"}],
        "syllabus_units": [{"unit_number": 1}, {"unit_number": 2}, {"unit_number": 3}, {"unit_number": 4}, {"unit_number": 5}],
    }
    rules = rule_engine.validate_paper(
        questions=questions,
        subject_config=subject_config,
        bloom_findings=[{"bloom_level": "Apply"}] * 5,
        co_findings=[{"co_code": f"CO{i}"} for i in range(1, 6)],
        syllabus_findings=[{"unit_number": i} for i in range(1, 6)],
        estimated_solving_time_minutes=150.0,
    )
    total_marks_rule = next(r for r in rules if r["rule_name"] == "Total Marks Verification")
    assert total_marks_rule["status"] == "PASS"


def test_internal_choice_not_double_counted():
    questions = [
        {"question_number": "Q.2(a)", "marks": 10, "internal_choice": False, "choice_group_id": None, "question_type": "SUBQUESTION"},
        {"question_number": "Q.2(a)", "marks": 10, "internal_choice": True, "choice_group_id": "g1", "question_type": "SUBQUESTION"},
        {"question_number": "Q.2(a)", "marks": 10, "internal_choice": True, "choice_group_id": "g1", "question_type": "SUBQUESTION"},
    ]
    # First is compulsory 10, choice pair counts once -> 20
    rules = rule_engine.validate_paper(
        questions=questions,
        subject_config={"total_marks": 20, "duration_minutes": 60, "course_outcomes": [], "syllabus_units": []},
        bloom_findings=[],
        co_findings=[],
        syllabus_findings=[],
        estimated_solving_time_minutes=40,
    )
    total = next(r for r in rules if r["rule_name"] == "Total Marks Verification")
    assert total["status"] == "PASS"
