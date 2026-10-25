import os
import sys
import uuid
import io
import zipfile
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.api import papers as papers_api, reports as reports_api, subjects as subjects_api, syllabus as syllabus_api
from app.core.dependencies import MongoUser, get_current_user
from app.db.mongo import get_db
from app.main import app


@pytest.fixture
def upload_dir():
    # Keep pytest's temporary upload directory inside the permitted workspace.
    path = Path(__file__).parent / f".subject-validation-upload-{uuid.uuid4().hex}"
    path.mkdir()
    yield path
    for child in sorted(path.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if child.is_file():
            child.unlink()
        else:
            child.rmdir()
    path.rmdir()


class FakeCursor(list):
    def sort(self, key, direction=1):
        return FakeCursor(sorted(self, key=lambda doc: doc.get(key, 0), reverse=direction < 0))


class FakeCollection:
    def __init__(self, documents=None):
        self.documents = deepcopy(documents or [])

    def find_one(self, query=None, **kwargs):
        query = query or {}
        return next((doc for doc in self.documents if self._matches(doc, query)), None)

    def find(self, query=None, *args, **kwargs):
        query = query or {}
        return FakeCursor(doc for doc in self.documents if self._matches(doc, query))

    @staticmethod
    def _matches(document, query):
        for key, value in query.items():
            actual = document.get(key)
            if isinstance(value, dict) and "$in" in value:
                if actual not in value["$in"]:
                    return False
            elif actual != value:
                return False
        return True

    def insert_one(self, document):
        self.documents.append(deepcopy(document))

    def update_one(self, query, update, upsert=False):
        document = self.find_one(query)
        if document and "$set" in update:
            document.update(deepcopy(update["$set"]))

    def delete_one(self, query):
        document = self.find_one(query)
        if document:
            self.documents.remove(document)
            return SimpleNamespace(deleted_count=1)
        return SimpleNamespace(deleted_count=0)

    def delete_many(self, query):
        matches = list(self.find(query))
        for document in matches:
            self.documents.remove(document)
        return SimpleNamespace(deleted_count=len(matches))


class FakeDatabase:
    def __init__(self):
        self.subjects = FakeCollection([
            {"id": 1, "code": "CS401", "name": "Machine Learning", "department": "CSE", "branch": "CSE", "semester": 7, "total_marks": 100, "duration_minutes": 180},
            {"id": 2, "code": "CS404", "name": "Computer Networks", "department": "CSE", "branch": "CSE", "semester": 7, "total_marks": 100, "duration_minutes": 180},
        ])
        self.syllabus_units = FakeCollection([
            {"id": 11, "subject_id": 1, "unit_number": 1, "title": "Machine Learning Methods", "topics": [{"id": 111, "unit_id": 11, "topic_name": "supervised regression"}, {"id": 112, "unit_id": 11, "topic_name": "decision trees"}, {"id": 113, "unit_id": 11, "topic_name": "unsupervised clustering"}]},
            {"id": 12, "subject_id": 2, "unit_number": 1, "title": "Computer Networks", "topics": [{"id": 121, "unit_id": 12, "topic_name": "packet switching subnetting"}, {"id": 122, "unit_id": 12, "topic_name": "routers DNS TCP congestion"}, {"id": 123, "unit_id": 12, "topic_name": "network protocols"}]},
        ])
        self.syllabus_topics = FakeCollection()
        self.subject_documents = FakeCollection()
        self.syllabus_documents = FakeCollection()
        self.course_outcomes = FakeCollection()
        self.examination_patterns = FakeCollection()
        self.question_papers = FakeCollection()
        self.scrutiny_reports = FakeCollection()
        self.extracted_questions = FakeCollection()
        self.audit_logs = FakeCollection()
        self.moderator_reviews = FakeCollection()
        self.previous_papers = FakeCollection()
        self.examinations = FakeCollection()
        self.users = FakeCollection()


def make_client(monkeypatch, upload_dir, db, extraction_text, pipeline_calls):
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: MongoUser({
        "id": 7, "email": "faculty@example.edu", "full_name": "Faculty", "role": "FACULTY"
    })
    monkeypatch.setattr(papers_api.settings, "UPLOAD_DIR", str(upload_dir))
    monkeypatch.setattr(papers_api, "get_next_sequence", lambda _name: 91)

    def fake_extract(database, paper):
        database.question_papers.update_one({"id": paper["id"]}, {"$set": {"raw_text": extraction_text}})
        return {"ok": True, "detailed": {"raw_text": extraction_text, "questions": [{"question_text": extraction_text}], "header_metadata": {}}}

    monkeypatch.setattr(papers_api, "extract_and_store_questions", fake_extract)
    def record_audit(database, **kwargs):
        database.audit_logs.insert_one(kwargs)

    monkeypatch.setattr(papers_api.AuditService, "log_action", staticmethod(record_audit))

    def fake_analysis(*args, **kwargs):
        pipeline_calls.append(True)
        return {"ok": True, "report_id": 1, "overall_score": 92}

    monkeypatch.setattr(papers_api, "run_scrutiny_analysis", fake_analysis)
    return TestClient(app)


def test_upload_rejects_cross_subject_document_and_preserves_validation_audit_record(monkeypatch, upload_dir):
    db = FakeDatabase()
    pipeline_calls = []
    network_text = (
        "Explain packet switching and subnetting. Describe routers, DNS, TCP congestion control, "
        "and the network protocols used between hosts."
    )
    client = make_client(monkeypatch, upload_dir, db, network_text, pipeline_calls)
    try:
        response = client.post(
            "/api/papers/upload",
            data={"title": "Network Final", "subject_id": "1", "academic_year": "2026-2027", "exam_type": "End-Sem", "auto_analyze": "true"},
            files={"file": ("networks.txt", network_text.encode(), "text/plain")},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "SUBJECT_MISMATCH"
    assert response.json()["detail"]["outcome"] == "mismatch"
    assert response.json()["detail"]["paper_id"] == 91
    assert len(db.question_papers.documents) == 1
    saved = db.question_papers.documents[0]
    assert saved["status"] == "SUBJECT_MISMATCH"
    assert saved["validation_status"] == "SUBJECT_MISMATCH"
    assert saved["validation_details"]["outcome"] == "mismatch"
    assert saved["overall_score"] is None
    assert db.audit_logs.documents[0]["action"] == "SUBJECT_MISMATCH"
    assert db.audit_logs.documents[0]["metadata"]["validation"]["check"] == "content_mismatch"
    assert pipeline_calls == []
    assert len(list(upload_dir.iterdir())) == 1


def test_upload_accepts_matching_content_and_runs_scrutiny(monkeypatch, upload_dir):
    db = FakeDatabase()
    pipeline_calls = []
    machine_learning_text = (
        "Use supervised regression to estimate model parameters. Compare decision trees "
        "with unsupervised clustering and explain how training data affects predictions."
    )
    client = make_client(monkeypatch, upload_dir, db, machine_learning_text, pipeline_calls)
    try:
        response = client.post(
            "/api/papers/upload",
            data={"title": "ML Final", "subject_id": "1", "academic_year": "2026-2027", "exam_type": "End-Sem", "auto_analyze": "true"},
            files={"file": ("machine-learning.txt", machine_learning_text.encode(), "text/plain")},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201, response.text
    assert response.json()["subject"]["id"] == 1
    assert len(db.question_papers.documents) == 1
    assert db.question_papers.documents[0]["validation_status"] == "VALID_MATCH"
    assert pipeline_calls == [True]


def test_direct_analysis_endpoint_cannot_bypass_subject_validation(monkeypatch):
    db = FakeDatabase()
    db.question_papers.insert_one({
        "id": 91, "uploaded_by_id": 7, "status": "SUBJECT_MISMATCH",
        "validation_status": "SUBJECT_MISMATCH", "overall_score": None,
    })
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: MongoUser({
        "id": 7, "email": "faculty@example.edu", "full_name": "Faculty", "role": "FACULTY"
    })
    try:
        response = TestClient(app).post("/api/papers/91/analyze")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "SCRUTINY_BLOCKED_BY_VALIDATION"
    assert db.question_papers.documents[0]["overall_score"] is None


def test_preflight_mismatch_records_audit_without_saving_document(monkeypatch, upload_dir):
    db = FakeDatabase()
    pipeline_calls = []
    network_text = (
        "Explain packet switching and subnetting. Describe routers, DNS, TCP congestion control, "
        "and network protocols used between hosts."
    )
    client = make_client(monkeypatch, upload_dir, db, network_text, pipeline_calls)
    try:
        response = client.post(
            "/api/papers/validate-subject",
            data={"subject_id": "1"},
            files={"file": ("network-paper.txt", network_text.encode(), "text/plain")},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["outcome"] == "mismatch"
    assert db.question_papers.documents == []
    assert db.audit_logs.documents[0]["entity"] == "SubjectValidation"
    assert db.audit_logs.documents[0]["action"] == "SUBJECT_MISMATCH"
    assert list(upload_dir.iterdir()) == []


def test_moderator_cannot_decide_on_unvalidated_paper():
    db = FakeDatabase()
    db.question_papers.insert_one({
        "id": 91, "uploaded_by_id": 7, "status": "SUBJECT_MISMATCH",
        "validation_status": "SUBJECT_MISMATCH", "overall_score": None,
    })
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: MongoUser({
        "id": 8, "email": "moderator@example.edu", "full_name": "Moderator", "role": "MODERATOR"
    })
    try:
        response = TestClient(app).post(
            "/api/moderator/reviews/91",
            json={"decision": "APPROVED", "remarks": "Reviewed"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    assert "VALID_MATCH" in response.json()["detail"]


def test_moderator_cannot_decide_on_legacy_paper_with_no_validation_status():
    db = FakeDatabase()
    db.question_papers.insert_one({"id": 91, "uploaded_by_id": 7, "status": "PENDING_REVIEW"})
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: MongoUser({
        "id": 8, "email": "moderator@example.edu", "full_name": "Moderator", "role": "MODERATOR"
    })
    try:
        review_response = TestClient(app).post(
            "/api/moderator/reviews/91",
            json={"decision": "APPROVED", "remarks": "Reviewed"},
        )
        legacy_route_response = TestClient(app).post(
            "/api/reports/91/decision",
            json={"decision": "APPROVED", "remarks": "Reviewed"},
        )
    finally:
        app.dependency_overrides.clear()

    assert review_response.status_code == 409
    assert legacy_route_response.status_code == 409
    assert db.moderator_reviews.documents == []


def test_legacy_report_decision_route_records_review_and_status_transition(monkeypatch):
    db = FakeDatabase()
    db.question_papers.insert_one({
        "id": 92,
        "uploaded_by_id": 7,
        "status": "PENDING_REVIEW",
        "validation_status": "VALID_MATCH",
    })
    db.scrutiny_reports.insert_one({"id": 12, "paper_id": 92, "version": 1})
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: MongoUser({
        "id": 8, "email": "moderator@example.edu", "full_name": "Moderator", "role": "MODERATOR"
    })
    monkeypatch.setattr(reports_api, "get_next_sequence", lambda _name: 93)
    monkeypatch.setattr(reports_api.AuditService, "log_action", staticmethod(lambda *args, **kwargs: None))
    try:
        response = TestClient(app).post(
            "/api/reports/92/decision",
            json={"decision": "APPROVED", "new_status": "REJECTED", "remarks": "Does not meet requirements"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert response.json()["new_status"] == "REJECTED"
    review = db.moderator_reviews.find_one({"paper_id": 92})
    assert review["report_id"] == 12
    assert review["moderator_name"] == "Moderator"
    assert review["previous_status"] == "PENDING_REVIEW"
    assert review["new_status"] == "REJECTED"
    assert db.question_papers.find_one({"id": 92})["status"] == "REJECTED"


def test_upload_rejects_unknown_selected_subject(monkeypatch, upload_dir):
    db = FakeDatabase()
    pipeline_calls = []
    client = make_client(monkeypatch, upload_dir, db, "irrelevant text", pipeline_calls)
    try:
        response = client.post(
            "/api/papers/upload",
            data={"title": "Unknown subject", "subject_id": "404", "academic_year": "2026-2027", "exam_type": "End-Sem"},
            files={"file": ("paper.txt", b"paper text", "text/plain")},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Selected subject not found"
    assert db.question_papers.documents == []
    assert pipeline_calls == []


def test_subject_academic_year_can_be_cleared_through_update_endpoint():
    db = FakeDatabase()
    db.subjects.find_one({"id": 1})["academic_year"] = "2025-2026"
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: MongoUser({
        "id": 8, "email": "moderator@example.edu", "full_name": "Moderator", "role": "MODERATOR"
    })
    try:
        response = TestClient(app).put("/api/subjects/1", json={"academic_year": None})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert response.json()["academic_year"] is None


def test_create_subject_keeps_only_user_supplied_curriculum(monkeypatch):
    db = FakeDatabase()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: MongoUser({
        "id": 8, "email": "moderator@example.edu", "full_name": "Moderator", "role": "MODERATOR"
    })
    sequence = iter(range(100, 110))
    monkeypatch.setattr(subjects_api, "get_next_sequence", lambda _name: next(sequence))
    payload = {
        "code": "CS499",
        "name": "Cloud Computing",
        "department": "Computer Science",
        "branch": "CSE",
        "semester": 7,
        "academic_year": "2026-2027",
        "total_marks": 100,
        "duration_minutes": 180,
        "course_outcomes": [{"co_code": "CO1", "description": "Deploy containerized services using Kubernetes."}],
        "syllabus_units": [{
            "unit_number": 1,
            "title": "Container Orchestration",
            "topics": [{"topic_name": "Kubernetes scheduling"}],
        }],
    }
    try:
        response = TestClient(app).post("/api/subjects", json=payload)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["code"] == "CS499"
    assert [co["co_code"] for co in result["course_outcomes"]] == ["CO1"]
    assert [(unit["unit_number"], unit["title"]) for unit in result["syllabus_units"]] == [(1, "Container Orchestration")]
    assert [topic["topic_name"] for topic in result["syllabus_units"][0]["topics"]] == ["Kubernetes scheduling"]


def test_faculty_can_edit_subject_and_manage_curriculum():
    db = FakeDatabase()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: MongoUser({
        "id": 7, "email": "faculty@example.edu", "full_name": "Faculty", "role": "FACULTY"
    })
    try:
        client = TestClient(app)
        update_subject = client.put("/api/subjects/1", json={"name": "Faculty updated name"})
        add_unit = client.post("/api/subjects/1/syllabus", json={"unit_number": 9, "title": "Faculty added unit"})
        add_cos = client.post("/api/subjects/1/cos/batch", json={"cos": [{"co_code": "CO9", "description": "Faculty added outcome"}]})
    finally:
        app.dependency_overrides.clear()

    assert update_subject.status_code == 200, update_subject.text
    assert add_unit.status_code == 200, add_unit.text
    assert add_cos.status_code == 200, add_cos.text
    assert db.subjects.find_one({"id": 1})["name"] == "Faculty updated name"
    assert len(db.syllabus_units.documents) == 3
    assert db.course_outcomes.find_one({"co_code": "CO9"})["description"] == "Faculty added outcome"


def test_faculty_can_create_and_delete_unreferenced_subject(monkeypatch):
    db = FakeDatabase()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: MongoUser({
        "id": 7, "email": "faculty@example.edu", "full_name": "Faculty", "role": "FACULTY"
    })
    sequence = iter([500, 501])
    monkeypatch.setattr(subjects_api, "get_next_sequence", lambda _name: next(sequence))
    payload = {
        "code": "CS808", "name": "Data Systems", "department": "Computer Science",
        "branch": "B.Tech CSE", "semester": 6, "total_marks": 80, "duration_minutes": 150,
    }
    try:
        client = TestClient(app)
        created = client.post("/api/subjects", json=payload)
        deleted = client.delete("/api/subjects/500") if created.status_code == 200 else None
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 200, created.text
    assert deleted.status_code == 200, deleted.text
    assert db.subjects.find_one({"id": 500}) is None


def test_syllabus_parser_extracts_only_detected_details_and_never_fabricates_units():
    parsed = syllabus_api.parse_syllabus_text("""SUBJECT CODE: 3CSPC201
SUBJECT NAME: MACHINE LEARNING
DEPARTMENT: Computer Engineering
PROGRAM: B.Tech Computer Engineering
SEMESTER: VI
ACADEMIC YEAR: 2026-2027
COURSE OUTCOMES:
CO1: Apply supervised learning methods.
Unit I: Introduction to Machine Learning
- Regression and classification
Unit II: Neural Networks
- Perceptrons and backpropagation
""")
    assert parsed["metadata"] == {
        "code": "3CSPC201",
        "name": "MACHINE LEARNING",
        "department": "Computer Engineering",
        "branch": "B.Tech Computer Engineering",
        "semester": 6,
        "academic_year": "2026-2027",
    }
    assert [unit["unit_number"] for unit in parsed["units"]] == [1, 2]
    assert parsed["course_outcomes"] == [{"co_code": "CO1", "description": "Apply supervised learning methods"}]

    unstructured = syllabus_api.parse_syllabus_text("This document contains prose but no identifiable syllabus unit or course outcome headings.")
    assert unstructured["units"] == []
    assert unstructured["course_outcomes"] == []


def test_faculty_syllabus_preview_returns_extracted_metadata_without_saving(monkeypatch, upload_dir):
    db = FakeDatabase()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: MongoUser({
        "id": 7, "email": "faculty@example.edu", "full_name": "Faculty", "role": "FACULTY"
    })
    monkeypatch.setattr(syllabus_api, "SYLLABUS_UPLOAD_DIR", str(upload_dir))
    sequence = iter(range(800, 820))
    monkeypatch.setattr(syllabus_api, "get_next_sequence", lambda _name: next(sequence))
    monkeypatch.setattr(syllabus_api.AuditService, "log_action", staticmethod(lambda *args, **kwargs: None))
    syllabus_bytes = b"COURSE CODE: CS808\nCOURSE NAME: Data Systems\nUnit 1: Storage\n- Indexing\nCO1: Analyze storage systems"
    try:
        client = TestClient(app)
        response = client.post("/api/subjects/syllabus/preview", files={
            "file": ("course-syllabus.txt", syllabus_bytes, "text/plain")
        })
        upload = client.post("/api/subjects/1/syllabus/upload", data={"replace_existing": "true"}, files={
            "file": ("course-syllabus.txt", syllabus_bytes, "text/plain")
        })
        units = client.get("/api/subjects/1/syllabus")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert response.json()["metadata"]["code"] == "CS808"
    assert response.json()["metadata"]["name"] == "Data Systems"
    assert response.json()["units_extracted"] == 1
    assert response.json()["course_outcomes_extracted"] == 1
    assert upload.status_code == 200, upload.text
    assert units.status_code == 200, units.text
    assert units.json()[-1]["topics"][0]["topic_name"] == "Indexing"
    assert len(db.syllabus_documents.documents) == 1


def test_subject_ppt_upload_supports_multiple_files_rejects_duplicates_and_non_ppt(monkeypatch, upload_dir):
    db = FakeDatabase()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: MongoUser({
        "id": 7, "email": "faculty@example.edu", "full_name": "Faculty", "role": "FACULTY"
    })
    monkeypatch.setattr(subjects_api, "UPLOAD_DIR", str(upload_dir))
    sequence = iter([701, 702])
    monkeypatch.setattr(subjects_api, "get_next_sequence", lambda _name: next(sequence))

    def valid_pptx(label):
        content = io.BytesIO()
        with zipfile.ZipFile(content, "w") as presentation:
            presentation.writestr("ppt/presentation.xml", f"<presentation>{label}</presentation>")
        return content.getvalue()

    first_ppt = valid_pptx("unit one")
    second_ppt = valid_pptx("unit two")
    try:
        client = TestClient(app)
        first = client.post("/api/subjects/1/documents", data={"title": "Unit One"}, files={
            "file": ("unit-one.pptx", first_ppt, "application/vnd.openxmlformats-officedocument.presentationml.presentation")
        })
        second = client.post("/api/subjects/1/documents", data={"title": "Unit Two"}, files={
            "file": ("unit-two.pptx", second_ppt, "application/vnd.openxmlformats-officedocument.presentationml.presentation")
        })
        duplicate = client.post("/api/subjects/1/documents", data={"title": "Repeated Unit One"}, files={
            "file": ("unit-one-copy.pptx", first_ppt, "application/vnd.openxmlformats-officedocument.presentationml.presentation")
        })
        wrong_type = client.post("/api/subjects/1/documents", data={"title": "Not a presentation"}, files={
            "file": ("notes.pdf", b"not a presentation", "application/pdf")
        })
        listing = client.get("/api/subjects/1/documents")
    finally:
        app.dependency_overrides.clear()

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert duplicate.status_code == 409
    assert wrong_type.status_code == 400
    assert len(listing.json()) == 2


def test_faculty_can_remove_only_their_own_ppt_and_syllabus(monkeypatch):
    db = FakeDatabase()
    db.subject_documents.insert_one({"id": 301, "subject_id": 1, "uploaded_by_id": 7, "file_path": None})
    db.subject_documents.insert_one({"id": 302, "subject_id": 1, "uploaded_by_id": 9, "file_path": None})
    db.syllabus_documents.insert_one({"id": 401, "subject_id": 1, "uploaded_by_id": 7, "file_path": None})
    db.syllabus_documents.insert_one({"id": 402, "subject_id": 1, "uploaded_by_id": 9, "file_path": None})
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: MongoUser({
        "id": 7, "email": "faculty@example.edu", "full_name": "Faculty", "role": "FACULTY"
    })
    monkeypatch.setattr(syllabus_api.AuditService, "log_action", staticmethod(lambda *args, **kwargs: None))
    try:
        client = TestClient(app)
        own_ppt = client.delete("/api/subjects/1/documents/301")
        other_ppt = client.delete("/api/subjects/1/documents/302")
        own_syllabus = client.delete("/api/subjects/1/syllabus/documents/401")
        other_syllabus = client.delete("/api/subjects/1/syllabus/documents/402")
    finally:
        app.dependency_overrides.clear()

    assert own_ppt.status_code == 200
    assert other_ppt.status_code == 403
    assert own_syllabus.status_code == 200
    assert other_syllabus.status_code == 403
    assert db.subject_documents.find_one({"id": 301}) is None
    assert db.subject_documents.find_one({"id": 302}) is not None
    assert db.syllabus_documents.find_one({"id": 401}) is None
    assert db.syllabus_documents.find_one({"id": 402}) is not None


def test_removing_unit_also_removes_its_uploaded_ppt_metadata():
    db = FakeDatabase()
    db.subject_documents.insert_one({"id": 301, "subject_id": 1, "unit_id": 11, "file_path": None})
    db.subject_documents.insert_one({"id": 302, "subject_id": 1, "unit_id": 12, "file_path": None})
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: MongoUser({
        "id": 8, "email": "moderator@example.edu", "full_name": "Moderator", "role": "MODERATOR"
    })
    try:
        response = TestClient(app).delete("/api/subjects/1/syllabus/11")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert db.syllabus_units.find_one({"id": 11}) is None
    assert db.subject_documents.find_one({"id": 301}) is None
    assert db.subject_documents.find_one({"id": 302}) is not None
