"""Keep Mongo-backed integration tests inside a temporary local test database."""

from __future__ import annotations

import os
import secrets
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pymongo import MongoClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
TESTS_DIR = Path(__file__).resolve().parent
TEST_DB_NAME = f"question_paper_scrutiny_test_{uuid.uuid4().hex}"
TEST_UPLOAD_DIR = TESTS_DIR / f".pytest_uploads_{uuid.uuid4().hex}"
TEST_PASSWORD = secrets.token_urlsafe(18)
MONGODB_AVAILABLE = False
mongo_client = None


def pytest_sessionstart(session):
    """Force integration tests to localhost and a unique, disposable database."""
    global MONGODB_AVAILABLE, mongo_client
    sys.path.insert(0, str(BACKEND_DIR))
    os.environ["MONGODB_URI"] = "mongodb://127.0.0.1:27017"
    os.environ["MONGODB_DB_NAME"] = TEST_DB_NAME
    os.environ["JWT_SECRET"] = secrets.token_urlsafe(48)
    os.environ["AI_PROVIDER"] = "mock"
    os.environ["UPLOAD_DIR"] = str(TEST_UPLOAD_DIR)
    os.environ["TEST_USER_PASSWORD"] = TEST_PASSWORD

    TEST_UPLOAD_DIR.mkdir(parents=True, exist_ok=False)
    mongo_client = MongoClient(os.environ["MONGODB_URI"], serverSelectionTimeoutMS=1000)
    try:
        mongo_client.admin.command("ping")
    except Exception:
        return

    MONGODB_AVAILABLE = True
    from app.core.security import get_password_hash
    from app.db.mongo import init_mongo_indexes

    db = mongo_client[TEST_DB_NAME]
    init_mongo_indexes()
    now = datetime.now(timezone.utc).isoformat()
    db.users.insert_many([
        {
            "id": 1, "email": "faculty@college.edu", "full_name": "Test Faculty",
            "role": "FACULTY", "department": "Test Department", "is_active": True,
            "hashed_password": get_password_hash(TEST_PASSWORD), "created_at": now,
        },
        {
            "id": 2, "email": "moderator@college.edu", "full_name": "Test Moderator",
            "role": "MODERATOR", "department": "Test Department", "is_active": True,
            "hashed_password": get_password_hash(TEST_PASSWORD), "created_at": now,
        },
        {
            "id": 3, "email": "admin@college.edu", "full_name": "Test Administrator",
            "role": "ADMIN", "department": "Test Department", "is_active": True,
            "hashed_password": get_password_hash(TEST_PASSWORD), "created_at": now,
        },
    ])
    db.subjects.insert_one({
        "id": 1, "code": "TEST_BASE", "name": "Test Subject",
        "department": "Test Department", "branch": "Test Branch", "semester": 1,
        "total_marks": 100, "duration_minutes": 180,
    })
    db.question_papers.insert_one({
        "id": 1, "title": "Isolated Test Paper", "subject_id": 1,
        "uploaded_by_id": 1, "filename": "isolated-test.txt", "file_type": "txt",
        "filepath": str(TEST_UPLOAD_DIR / "not-a-real-file.txt"),
        "file_path": str(TEST_UPLOAD_DIR / "not-a-real-file.txt"),
        "academic_year": "2026-2027", "exam_type": "Test", "status": "PENDING_REVIEW",
        "validation_status": "VALID_MATCH", "overall_score": 75.0, "version": 1,
        "uploaded_at": now,
    })
    db.scrutiny_reports.insert_one({
        "id": 1, "paper_id": 1, "version": 1, "overall_score": 75.0,
        "solving_time_minutes": None, "compliance_summary": "Isolated test report",
        "created_at": now,
    })
    db.counters.insert_many([
        {"_id": "users", "seq": 3},
        {"_id": "subjects", "seq": 1},
        {"_id": "question_papers", "seq": 1},
        {"_id": "scrutiny_reports", "seq": 1},
    ])


def pytest_collection_modifyitems(config, items):
    if MONGODB_AVAILABLE:
        return
    import pytest

    skip_mongo = pytest.mark.skip(reason="Local MongoDB is unavailable; Mongo integration tests were not run.")
    for item in items:
        if Path(str(item.path)).name in {"test_auth.py", "test_features_e2e.py"}:
            item.add_marker(skip_mongo)


def pytest_sessionfinish(session, exitstatus):
    if mongo_client is not None:
        if MONGODB_AVAILABLE:
            mongo_client.drop_database(TEST_DB_NAME)
        mongo_client.close()

    resolved_test_dir = TEST_UPLOAD_DIR.resolve()
    if resolved_test_dir.parent == TESTS_DIR.resolve() and resolved_test_dir.name.startswith(".pytest_uploads_"):
        if resolved_test_dir.exists():
            shutil.rmtree(resolved_test_dir)
