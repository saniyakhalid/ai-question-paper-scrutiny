import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.services.subject_validation_service import validate_paper_subject


class FakeCollection:
    def __init__(self, documents):
        self.documents = documents

    def find_one(self, query):
        return next(
            (doc for doc in self.documents if all(doc.get(key) == value for key, value in query.items())),
            None,
        )

    def find(self, query=None):
        query = query or {}
        return [
            doc for doc in self.documents
            if all(doc.get(key) == value for key, value in query.items())
        ]


class FakeDatabase:
    def __init__(self):
        self.subjects = FakeCollection([
            {"id": 1, "code": "CS401", "name": "Machine Learning"},
            {"id": 2, "code": "CS402", "name": "Deep Learning"},
            {"id": 3, "code": "CS403", "name": "Data Science"},
            {"id": 4, "code": "CS404", "name": "Computer Networks"},
            {"id": 5, "code": "CS405", "name": "Cloud Computing"},
        ])
        self.syllabus_units = FakeCollection([
            {
                "id": 11,
                "subject_id": 1,
                "title": "Machine Learning Methods",
                "topics": [
                    {"topic_name": "supervised regression"},
                    {"topic_name": "unsupervised clustering"},
                    {"topic_name": "decision trees"},
                ],
            },
            {
                "id": 12,
                "subject_id": 2,
                "title": "Deep Neural Networks",
                "topics": [
                    {"topic_name": "neural networks"},
                    {"topic_name": "backpropagation"},
                    {"topic_name": "activation functions"},
                    {"topic_name": "convolutional recurrent architectures"},
                ],
            },
            {
                "id": 13,
                "subject_id": 3,
                "title": "Data Science Practice",
                "topics": [
                    {"topic_name": "pandas dataframe visualization"},
                    {"topic_name": "feature engineering data preparation"},
                    {"topic_name": "statistical inference"},
                ],
            },
            {
                "id": 14,
                "subject_id": 4,
                "title": "Computer Networks",
                "topics": [
                    {"topic_name": "packet switching subnetting"},
                    {"topic_name": "routers DNS TCP congestion"},
                    {"topic_name": "network protocols"},
                ],
            },
            {
                "id": 15,
                "subject_id": 5,
                "title": "Cloud Infrastructure",
                "topics": [
                    {"topic_name": "Kubernetes container orchestration"},
                    {"topic_name": "virtual machines cloud deployment"},
                ],
            },
        ])
        self.syllabus_topics = FakeCollection([])
        self.course_outcomes = FakeCollection([])


def test_rejects_other_subject_with_shared_course_name_word():
    db = FakeDatabase()
    paper_text = (
        "Explain learning rate schedules while training a neural network. "
        "Describe backpropagation, activation functions, convolutional layers, "
        "and recurrent architectures."
    )

    result = validate_paper_subject(
        db,
        subject_id=1,
        raw_text=paper_text,
        questions=[{"question_text": paper_text}],
    )

    assert result["valid"] is False
    assert result["check"] == "content_mismatch"
    assert "CS402 - Deep Learning" in result["message"]


def test_rejects_header_title_that_matches_another_shared_family_subject():
    result = validate_paper_subject(
        FakeDatabase(),
        subject_id=1,
        raw_text=(
            "Subject: Deep Learning\n"
            "Explain neural networks and activation functions using the supplied data."
        ),
        questions=[{"question_text": "Explain neural networks and activation functions."}],
    )

    assert result["valid"] is False
    assert result["check"] == "header_course_title"
    assert "CS402 - Deep Learning" in result["message"]


def test_accepts_machine_learning_paper_with_multiple_selected_syllabus_terms():
    text = (
        "Use supervised regression to estimate the model parameters. "
        "Compare decision trees with unsupervised clustering and explain "
        "how the training data changes the prediction accuracy."
    )
    result = validate_paper_subject(FakeDatabase(), 1, text, [{"question_text": text}])

    assert result["valid"] is True
    assert result["outcome"] == "accepted"
    assert result["matched_keywords_count"] >= 2


def test_rejects_computer_networks_paper_when_machine_learning_is_selected():
    text = (
        "Explain packet switching and subnetting. Describe routers, DNS, "
        "TCP congestion control, and the network protocols used between hosts."
    )
    result = validate_paper_subject(FakeDatabase(), 1, text, [{"question_text": text}])

    assert result["valid"] is False
    assert result["outcome"] == "mismatch"
    assert "CS404 - Computer Networks" in result["message"]


def test_rejects_data_science_paper_when_machine_learning_is_selected():
    text = (
        "Prepare a pandas dataframe for visualization. Discuss feature engineering, "
        "data preparation, and statistical inference for the reporting workflow."
    )
    result = validate_paper_subject(FakeDatabase(), 1, text, [{"question_text": text}])

    assert result["valid"] is False
    assert result["outcome"] == "mismatch"
    assert "CS403 - Data Science" in result["message"]


def test_filename_hint_does_not_reject_matching_document_content():
    text = (
        "Explain supervised regression and decision trees. Compare clustering "
        "with prediction models and discuss the training data used for evaluation."
    )
    result = validate_paper_subject(
        FakeDatabase(), 1, text, [{"question_text": text}], filename="CS402-deep-learning.pdf"
    )

    assert result["valid"] is True
    assert result["outcome"] == "accepted"


def test_single_shared_keyword_is_inconclusive_instead_of_a_false_mismatch():
    text = "Discuss learning alongside broad principles, general theory, and other academic subjects."
    result = validate_paper_subject(FakeDatabase(), 1, text, [{"question_text": text}])

    assert result["valid"] is False
    assert result["outcome"] == "inconclusive"
    assert result["check"] == "insufficient_subject_evidence"


def test_same_document_is_checked_against_the_currently_selected_subject():
    text = (
        "Explain Kubernetes container orchestration. Compare virtual machines "
        "and cloud deployment for scalable infrastructure management."
    )
    db = FakeDatabase()

    as_machine_learning = validate_paper_subject(db, 1, text, [{"question_text": text}])
    as_cloud_computing = validate_paper_subject(db, 5, text, [{"question_text": text}])

    assert as_machine_learning["valid"] is False
    assert as_machine_learning["outcome"] == "mismatch"
    assert as_cloud_computing["valid"] is True
    assert as_cloud_computing["outcome"] == "accepted"


def test_insufficient_extracted_content_fails_closed_as_inconclusive():
    result = validate_paper_subject(FakeDatabase(), 1, "Q1. (a) Explain?", [])

    assert result["valid"] is False
    assert result["outcome"] == "inconclusive"
    assert result["check"] == "insufficient_text"
