import os
import sys
import io
import zipfile
import pytest
from fastapi.testclient import TestClient

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app
from app.db.mongo import get_mongo_db, get_next_sequence

client = TestClient(app)

@pytest.fixture
def auth_tokens():
    db = get_mongo_db()
    # Login faculty
    test_password = os.environ["TEST_USER_PASSWORD"]
    res_fac = client.post("/api/auth/login", json={"email": "faculty@college.edu", "password": test_password})
    assert res_fac.status_code == 200
    fac_token = res_fac.json()["access_token"]

    # Login moderator
    res_mod = client.post("/api/auth/login", json={"email": "moderator@college.edu", "password": test_password})
    assert res_mod.status_code == 200
    mod_token = res_mod.json()["access_token"]

    return {"faculty": fac_token, "moderator": mod_token}

def test_syllabus_upload_and_isolation(auth_tokens):
    db = get_mongo_db()
    fac_headers = {"Authorization": f"Bearer {auth_tokens['faculty']}"}
    mod_headers = {"Authorization": f"Bearer {auth_tokens['moderator']}"}
    
    # 1. Ensure a test subject exists
    subj = db.subjects.find_one({"code": "TEST_CS909"})
    if not subj:
        subj_id = get_next_sequence("subjects")
        subj = {
            "id": subj_id,
            "code": "TEST_CS909",
            "name": "Advanced Distributed Systems",
            "department": "Computer Science & Engineering",
            "branch": "B.Tech CSE",
            "semester": 7,
            "total_marks": 100,
            "duration_minutes": 180
        }
        db.subjects.insert_one(subj)
    else:
        subj_id = subj["id"]

    # 2. Upload syllabus
    sample_syl_text = """AUTONOMOUS ENGINEERING COLLEGE
SUBJECT CODE: TEST_CS909
COURSE OUTCOMES:
CO1: Understand consensus protocols in distributed systems.
CO2: Design fault-tolerant scalable architectures.

SYLLABUS UNITS:
Unit 1: Foundations of Distributed Computing
- Lamport Timestamps, Vector Clocks
- State Machine Replication

Unit 2: Consensus & Leader Election
- Paxos, Raft consensus algorithms
- Byzantine Fault Tolerance
"""
    file_bytes = io.BytesIO(sample_syl_text.encode("utf-8"))
    upload_res = client.post(
        f"/api/subjects/{subj_id}/syllabus/upload",
        headers=fac_headers,
        data={"academic_year": "2025-2026", "replace_existing": "true"},
        files={"file": ("TEST_CS909_Syllabus.txt", file_bytes, "text/plain")}
    )
    assert upload_res.status_code == 200
    data = upload_res.json()
    assert data["ok"] is True
    assert data["units_extracted"] >= 2
    assert data["course_outcomes_extracted"] >= 2

    # 3. Check syllabus status
    status_res = client.get(f"/api/subjects/{subj_id}/syllabus/status", headers=fac_headers)
    assert status_res.status_code == 200
    s_data = status_res.json()
    assert s_data["has_uploaded_syllabus"] is True
    assert s_data["unit_count"] >= 2

    # Moderator and admin library views can inspect and download faculty files.
    mod_status = client.get(f"/api/subjects/{subj_id}/syllabus/status", headers=mod_headers)
    assert mod_status.status_code == 200
    mod_doc = mod_status.json()["documents"][0]
    assert mod_doc["uploaded_by_name"] == "Test Faculty"
    assert "file_path" not in mod_doc
    syllabus_download = client.get(
        f"/api/subjects/{subj_id}/syllabus/documents/{mod_doc['id']}/download",
        headers=mod_headers,
    )
    assert syllabus_download.status_code == 200
    assert b"TEST_CS909" in syllabus_download.content

    # Only faculty can submit official syllabus documents.
    rejected_upload = client.post(
        f"/api/subjects/{subj_id}/syllabus/upload",
        headers=mod_headers,
        data={"academic_year": "2025-2026", "replace_existing": "false"},
        files={"file": ("moderator-syllabus.txt", b"Unit 1: Not allowed", "text/plain")},
    )
    assert rejected_upload.status_code == 403


def test_faculty_ppt_is_visible_and_downloadable_by_moderator(auth_tokens):
    fac_headers = {"Authorization": f"Bearer {auth_tokens['faculty']}"}
    mod_headers = {"Authorization": f"Bearer {auth_tokens['moderator']}"}
    ppt_buffer = io.BytesIO()
    with zipfile.ZipFile(ppt_buffer, "w") as presentation:
        presentation.writestr("ppt/presentation.xml", "<presentation>faculty unit one</presentation>")
    ppt_bytes = ppt_buffer.getvalue()

    upload = client.post(
        "/api/subjects/1/documents",
        headers=fac_headers,
        data={"title": "Machine Learning Unit 1", "doc_type": "PPT", "academic_year": "2026-2027", "semester": "1"},
        files={"file": ("ml-unit-1.pptx", ppt_bytes, "application/vnd.openxmlformats-officedocument.presentationml.presentation")},
    )
    assert upload.status_code == 200
    uploaded_doc = upload.json()
    assert uploaded_doc["uploaded_by_name"] == "Test Faculty"
    assert "file_path" not in uploaded_doc

    listing = client.get("/api/subjects/1/documents", headers=mod_headers)
    assert listing.status_code == 200
    visible_doc = next(doc for doc in listing.json() if doc["id"] == uploaded_doc["id"])
    assert visible_doc["title"] == "Machine Learning Unit 1"
    assert visible_doc["uploaded_by_name"] == "Test Faculty"

    download = client.get(f"/api/subjects/1/documents/{uploaded_doc['id']}/download", headers=mod_headers)
    assert download.status_code == 200
    assert download.content == ppt_bytes

    rejected_upload = client.post(
        "/api/subjects/1/documents",
        headers=mod_headers,
        data={"title": "Moderator PPT", "doc_type": "PPT"},
        files={"file": ("moderator.pptx", b"not allowed", "application/octet-stream")},
    )
    assert rejected_upload.status_code == 403

def test_moderator_feedback_workflow(auth_tokens):
    db = get_mongo_db()
    fac_headers = {"Authorization": f"Bearer {auth_tokens['faculty']}"}
    mod_headers = {"Authorization": f"Bearer {auth_tokens['moderator']}"}

    # Find or create a question paper
    paper = db.question_papers.find_one({})
    assert paper is not None
    paper_id = paper["id"]
    previous_status = paper.get("status")

    # Moderator submits review
    review_res = client.post(
        f"/api/moderator/reviews/{paper_id}",
        headers=mod_headers,
        json={
            "decision": "APPROVED",
            "remarks": "Excellent question paper structure and Blooms taxonomy coverage.",
            "required_action": "Approved for final examination cell release.",
            "corrections": []
        }
    )
    assert review_res.status_code == 200
    r_data = review_res.json()
    assert r_data["decision"] == "APPROVED"
    assert r_data["previous_status"] == previous_status
    assert r_data["new_status"] == "APPROVED"
    assert "moderator_name" in r_data

    timeline = client.get(f"/api/history/{paper_id}", headers=mod_headers)
    assert timeline.status_code == 200
    decision_history = timeline.json()["moderator_reviews"]
    assert len(decision_history) == 1
    assert decision_history[0]["previous_status"] == previous_status
    assert decision_history[0]["new_status"] == "APPROVED"
    assert decision_history[0]["moderator"] == "Test Moderator"
    assert decision_history[0]["created_at"]

    # Faculty views review
    fac_view_res = client.get(f"/api/moderator/reviews/{paper_id}", headers=fac_headers)
    assert fac_view_res.status_code == 200
    fv_data = fac_view_res.json()
    assert fv_data["has_review"] is True
    assert fv_data["review"]["decision"] == "APPROVED"
    assert "Blooms taxonomy" in fv_data["review"]["remarks"]

    # Test Moderator submitting Changes Requested (MODIFICATION_REQUIRED)
    change_res = client.post(
        f"/api/moderator/reviews/{paper_id}",
        headers=mod_headers,
        json={
            "decision": "CHANGES_REQUESTED",
            "remarks": "Please revise Question 3 marks and replace K1 questions with higher-order K4 questions.",
            "required_action": "Update Q3 marks to 10 and re-upload revised paper.",
            "corrections": []
        }
    )
    assert change_res.status_code == 200
    c_data = change_res.json()
    assert c_data["decision"] == "MODIFICATION_REQUIRED"
    assert c_data["new_status"] == "MODIFICATION_REQUIRED"

    # Faculty views the requested changes and feedback message
    fac_change_res = client.get(f"/api/moderator/reviews/{paper_id}", headers=fac_headers)
    assert fac_change_res.status_code == 200
    fc_data = fac_change_res.json()
    assert fc_data["has_review"] is True
    assert fc_data["review"]["decision"] == "MODIFICATION_REQUIRED"
    assert "Question 3 marks" in fc_data["review"]["remarks"]
    assert "re-upload revised paper" in fc_data["review"]["required_action"]

    # Faculty views paper endpoint directly and sees feedback
    fac_paper_res = client.get(f"/api/papers/{paper_id}", headers=fac_headers)
    assert fac_paper_res.status_code == 200
    fp_data = fac_paper_res.json()
    assert fp_data["status"] == "MODIFICATION_REQUIRED"
    assert fp_data["moderator_feedback"] == "Please revise Question 3 marks and replace K1 questions with higher-order K4 questions."
    assert fp_data["moderator_decision"] == "MODIFICATION_REQUIRED"
    assert fp_data["moderator_required_action"] == "Update Q3 marks to 10 and re-upload revised paper."

    # Faculty list papers endpoint also includes feedback
    fac_list_res = client.get("/api/papers", headers=fac_headers)
    assert fac_list_res.status_code == 200
    matching_paper = next((p for p in fac_list_res.json() if p["id"] == paper_id), None)
    assert matching_paper is not None
    assert matching_paper["moderator_feedback"] == "Please revise Question 3 marks and replace K1 questions with higher-order K4 questions."
    assert matching_paper["moderator_decision"] == "MODIFICATION_REQUIRED"

def test_exports_endpoints(auth_tokens):
    db = get_mongo_db()
    fac_headers = {"Authorization": f"Bearer {auth_tokens['faculty']}"}

    paper = db.question_papers.find_one({"overall_score": {"$ne": None}})
    if not paper:
        paper = db.question_papers.find_one({})
    paper_id = paper["id"]

    # Test PDF export
    res_pdf = client.get(f"/api/scrutiny/reports/{paper_id}/export/pdf", headers=fac_headers)
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert len(res_pdf.content) > 500

    # Test CSV export
    res_csv = client.get(f"/api/scrutiny/reports/{paper_id}/export/csv", headers=fac_headers)
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert b"AUTONOMOUS ENGINEERING COLLEGE" in res_csv.content
    assert b"Scrutiny Score" in res_csv.content

    # Test JSON export
    res_json = client.get(f"/api/scrutiny/reports/{paper_id}/export/json", headers=fac_headers)
    assert res_json.status_code == 200
    assert res_json.headers["content-type"] == "application/json"
    data = res_json.json()
    assert "paper_id" in data
    assert "rule_results" in data

    # Bearer tokens in query strings are rejected to prevent accidental credential leaks.
    token = auth_tokens["faculty"]
    res_pdf_token = client.get(f"/api/scrutiny/reports/{paper_id}/export/pdf?token={token}")
    assert res_pdf_token.status_code == 401

def test_history_deletion(auth_tokens):
    db = get_mongo_db()
    mod_headers = {"Authorization": f"Bearer {auth_tokens['moderator']}"}

    # Create dummy paper for deletion test
    paper_id = get_next_sequence("question_papers")
    dummy_paper = {
        "id": paper_id,
        "title": "Temporary Paper for Deletion Test",
        "subject_id": 1,
        "uploaded_by_id": 1,
        "status": "SUBMITTED",
        "overall_score": 75.0,
        "filepath": os.path.join(os.environ["UPLOAD_DIR"], "temp_test.txt"),
        "file_path": os.path.join(os.environ["UPLOAD_DIR"], "temp_test.txt"),
    }
    db.question_papers.insert_one(dummy_paper)
    # Dummy questions & report
    db.extracted_questions.insert_one({"id": get_next_sequence("extracted_questions"), "paper_id": paper_id, "question_text": "Temp Q"})
    db.scrutiny_reports.insert_one({"id": get_next_sequence("scrutiny_reports"), "paper_id": paper_id, "overall_score": 75.0, "version": 1})

    # Delete via history endpoint
    del_res = client.delete(f"/api/history/{paper_id}", headers=mod_headers)
    assert del_res.status_code == 200
    assert del_res.json()["ok"] is True

    # Verify cascade deletion
    assert db.question_papers.find_one({"id": paper_id}) is None
    assert db.extracted_questions.find_one({"paper_id": paper_id}) is None
    assert db.scrutiny_reports.find_one({"paper_id": paper_id}) is None


def test_moderator_decline_and_reject_decisions(auth_tokens):
    db = get_mongo_db()
    mod_headers = {"Authorization": f"Bearer {auth_tokens['moderator']}"}
    fac_headers = {"Authorization": f"Bearer {auth_tokens['faculty']}"}

    paper_id = get_next_sequence("question_papers")
    dummy_paper = {
        "id": paper_id,
        "title": "Review Decision Testing Paper",
        "subject_id": 1,
        "uploaded_by_id": 1,
        "status": "SUBMITTED",
        "validation_status": "VALID_MATCH",
        "overall_score": 82.0,
        "filepath": os.path.join(os.environ["UPLOAD_DIR"], "test_decision.txt"),
        "file_path": os.path.join(os.environ["UPLOAD_DIR"], "test_decision.txt"),
    }
    db.question_papers.insert_one(dummy_paper)
    rep_id = get_next_sequence("scrutiny_reports")
    db.scrutiny_reports.insert_one({"id": rep_id, "paper_id": paper_id, "overall_score": 82.0, "version": 1})

    # 1. Test REVIEW_DECLINED decision
    decline_res = client.post(
        f"/api/moderator/reviews/{paper_id}",
        headers=mod_headers,
        json={
            "decision": "REVIEW_DECLINED",
            "remarks": "Assigned moderator has a conflict of interest for this course.",
            "required_action": "Reassign to secondary department moderator.",
            "corrections": []
        }
    )
    assert decline_res.status_code == 200
    d_data = decline_res.json()
    assert d_data["decision"] == "REVIEW_DECLINED"
    assert d_data["new_status"] == "REVIEW_DECLINED"

    # Faculty sees the decision and remarks
    fac_check = client.get(f"/api/moderator/reviews/{paper_id}", headers=fac_headers)
    assert fac_check.status_code == 200
    assert fac_check.json()["review"]["decision"] == "REVIEW_DECLINED"
    assert "conflict of interest" in fac_check.json()["review"]["remarks"]

    # 2. Test REJECTED decision
    reject_res = client.post(
        f"/api/moderator/reviews/{paper_id}",
        headers=mod_headers,
        json={
            "decision": "REJECTED",
            "remarks": "Paper fails minimum Bloom higher-order cognitive threshold.",
            "required_action": "Redraft Section B with higher-order analytical questions.",
            "corrections": []
        }
    )
    assert reject_res.status_code == 200
    r_data = reject_res.json()
    assert r_data["decision"] == "REJECTED"
    assert r_data["new_status"] == "REJECTED"

    # Verify paper status updated
    updated_paper = db.question_papers.find_one({"id": paper_id})
    assert updated_paper["status"] == "REJECTED"
    assert updated_paper["moderator_decision"] == "REJECTED"
    assert "fails minimum Bloom" in updated_paper["moderator_feedback"]
    assert "Redraft Section B" in updated_paper.get("moderator_required_action", "")

    # Clean up test paper
    db.question_papers.delete_one({"id": paper_id})
    db.scrutiny_reports.delete_many({"paper_id": paper_id})
    db.moderator_reviews.delete_many({"paper_id": paper_id})


def test_faculty_co_edit_endpoint(auth_tokens):
    db = get_mongo_db()
    fac_headers = {"Authorization": f"Bearer {auth_tokens['faculty']}"}

    # Create a test CO
    co_id = get_next_sequence("course_outcomes")
    db.course_outcomes.insert_one({
        "id": co_id,
        "subject_id": 1,
        "co_code": "CO99",
        "description": "Original CO description before editing"
    })

    # Faculty edits CO
    edit_res = client.put(
        f"/api/subjects/1/cos/{co_id}",
        headers=fac_headers,
        json={
            "co_code": "CO99_REVISED",
            "description": "Updated CO description verified by course coordinator"
        }
    )
    assert edit_res.status_code == 200
    ed_data = edit_res.json()
    assert ed_data["co_code"] == "CO99_REVISED"
    assert ed_data["description"] == "Updated CO description verified by course coordinator"

    # Verify persisted in database
    db_co = db.course_outcomes.find_one({"id": co_id})
    assert db_co["co_code"] == "CO99_REVISED"
    assert db_co["description"] == "Updated CO description verified by course coordinator"

    # Clean up
    db.course_outcomes.delete_one({"id": co_id})


