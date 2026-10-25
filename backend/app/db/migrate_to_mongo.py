"""
Migration script: SQLite (scrutiny.db) -> MongoDB (question_paper_scrutiny)
Safely migrates all existing users, subjects, syllabus, papers, questions,
reports, scores, findings, reviews, and audit logs to MongoDB.
"""

import os
import sys
import json
import sqlite3
from datetime import datetime, timezone

# Add backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.db.mongo import get_mongo_db, init_mongo_indexes

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def run_migration():
    sqlite_path = os.path.join(backend_dir, "scrutiny.db")
    if not os.path.exists(sqlite_path):
        print(f"SQLite database not found at {sqlite_path}. Nothing to migrate.")
        return

    print(f"Connecting to SQLite database: {sqlite_path}")
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = dict_factory
    cursor = sqlite_conn.cursor()

    mongo_db = get_mongo_db()
    init_mongo_indexes()

    tables_to_migrate = [
        "users",
        "subjects",
        "syllabus_units",
        "syllabus_topics",
        "course_outcomes",
        "examination_patterns",
        "question_papers",
        "extracted_questions",
        "scrutiny_reports",
        "rule_results",
        "scrutiny_findings",
        "similarity_results",
        "moderator_reviews",
        "moderator_corrections",
        "audit_logs",
        "previous_papers",
        "previous_questions",
    ]

    counters = {}

    for table in tables_to_migrate:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}';")
        if not cursor.fetchone():
            print(f"Skipping table '{table}' (not found in SQLite)")
            continue

        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        print(f"Migrating {len(rows)} records from '{table}'...")

        max_id = 0
        for r in rows:
            # Parse JSON columns
            for k, v in list(r.items()):
                if isinstance(v, str) and (k.endswith("_json") or k == "metadata" or k == "corrections"):
                    try:
                        r[k] = json.loads(v)
                    except Exception:
                        pass
                # Convert boolean columns
                if k in ("is_active", "internal_choice", "is_unit_selected"):
                    r[k] = bool(v) if v is not None else False

            record_id = r.get("id")
            if isinstance(record_id, int) and record_id > max_id:
                max_id = record_id

            # Upsert into MongoDB by id
            if record_id is not None:
                mongo_db[table].update_one({"id": record_id}, {"$set": r}, upsert=True)
            else:
                mongo_db[table].insert_one(r)

        if max_id > 0:
            counters[table] = max_id
            mongo_db.counters.update_one(
                {"_id": table},
                {"$set": {"seq": max_id}},
                upsert=True
            )

    print("\n--- Migration Complete ---")
    for table in tables_to_migrate:
        count = mongo_db[table].count_documents({})
        print(f"MongoDB collection '{table}': {count} documents (counter: {counters.get(table, 'N/A')})")

    sqlite_conn.close()

if __name__ == "__main__":
    run_migration()
