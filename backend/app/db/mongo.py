"""
MongoDB database connection, collection references, index setup, and sequence management.
Replaces SQLAlchemy with a native, robust PyMongo layer.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from bson import ObjectId
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.database import Database

from app.core.config import settings

logger = logging.getLogger(__name__)

_mongo_client: Optional[MongoClient] = None
_mongo_db: Optional[Database] = None


def get_mongo_client() -> MongoClient:
    global _mongo_client
    if _mongo_client is None:
        logger.info("Connecting to the configured MongoDB service.")
        _mongo_client = MongoClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=5000,
            maxPoolSize=50,
            minPoolSize=5,
        )
    return _mongo_client


def get_mongo_db() -> Database:
    global _mongo_db
    if _mongo_db is None:
        client = get_mongo_client()
        _mongo_db = client[settings.MONGODB_DB_NAME]
    return _mongo_db


def get_db() -> Database:
    """FastAPI dependency for accessing the MongoDB database instance."""
    return get_mongo_db()


def get_next_sequence(sequence_name: str) -> int:
    """
    Generates auto-incrementing integer IDs for collections (users, subjects, papers, questions)
    so existing frontend routing and relations (e.g. /papers/3) work seamlessly.
    """
    db = get_mongo_db()
    ret = db.counters.find_one_and_update(
        {"_id": sequence_name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    return int(ret["seq"])


def serialize_doc(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Converts MongoDB BSON document to JSON-friendly dictionary."""
    if doc is None:
        return None
    d = dict(doc)
    if "_id" in d:
        if "id" not in d or d["id"] is None:
            d["id"] = str(d["_id"])
        d["_id"] = str(d["_id"])
    for k, v in list(d.items()):
        if isinstance(v, datetime):
            d[k] = v.isoformat()
        elif isinstance(v, ObjectId):
            d[k] = str(v)
        elif isinstance(v, list):
            d[k] = [serialize_doc(item) if isinstance(item, dict) else item for item in v]
        elif isinstance(v, dict):
            d[k] = serialize_doc(v)
    return d


def serialize_docs(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [serialize_doc(doc) for doc in docs if doc is not None]


def init_mongo_indexes() -> None:
    """Creates performance and integrity indexes for MongoDB collections."""
    db = get_mongo_db()
    try:
        # Users
        db.users.create_index([("email", ASCENDING)], unique=True)
        db.users.create_index([("id", ASCENDING)], unique=True, sparse=True)

        # Subjects
        db.subjects.create_index([("code", ASCENDING)], unique=True)
        db.subjects.create_index([("id", ASCENDING)], unique=True, sparse=True)

        # Syllabus
        db.syllabus_units.create_index([("subject_id", ASCENDING), ("unit_number", ASCENDING)])
        db.syllabus_documents.create_index([("subject_id", ASCENDING)])

        # Question Papers
        db.question_papers.create_index([("id", ASCENDING)], unique=True, sparse=True)
        db.question_papers.create_index([("subject_id", ASCENDING)])
        db.question_papers.create_index([("uploaded_by_id", ASCENDING)])
        db.question_papers.create_index([("status", ASCENDING)])

        # Extracted Questions
        db.extracted_questions.create_index([("id", ASCENDING)], unique=True, sparse=True)
        db.extracted_questions.create_index([("paper_id", ASCENDING)])
        db.extracted_questions.create_index([("sequence_order", ASCENDING)])

        # Scrutiny Reports & Findings
        db.scrutiny_reports.create_index([("id", ASCENDING)], unique=True, sparse=True)
        db.scrutiny_reports.create_index([("paper_id", ASCENDING), ("version", DESCENDING)])
        db.rule_results.create_index([("report_id", ASCENDING)])
        db.scrutiny_findings.create_index([("report_id", ASCENDING), ("question_id", ASCENDING)])
        db.similarity_results.create_index([("report_id", ASCENDING)])

        # Moderator Reviews & Audit Logs
        db.moderator_reviews.create_index([("paper_id", ASCENDING)])
        db.audit_logs.create_index([("entity_type", ASCENDING), ("entity_id", ASCENDING)])
        db.audit_logs.create_index([("timestamp", DESCENDING)])

        logger.info("MongoDB indexes successfully initialized.")
    except Exception as e:
        logger.warning(f"Notice while initializing MongoDB indexes: {e}")
