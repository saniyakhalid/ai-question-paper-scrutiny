from typing import Dict, Any, List
from pymongo.database import Database
from pymongo import ASCENDING, DESCENDING

from app.db.mongo import serialize_doc, serialize_docs

class HistoryService:
    @staticmethod
    def get_full_paper_history(db: Database, paper_id: int) -> Dict[str, Any]:
        """Fetches full paper timeline from MongoDB collections."""
        paper = db.question_papers.find_one({"id": paper_id})
        if not paper:
            return {}

        reports = list(db.scrutiny_reports.find({"paper_id": paper_id}).sort("version", DESCENDING))
        reviews = list(db.moderator_reviews.find({"paper_id": paper_id}).sort("created_at", DESCENDING))
        audits = list(db.audit_logs.find({"entity_id": paper_id}).sort("timestamp", ASCENDING))

        return {
            "paper_id": paper.get("id"),
            "title": paper.get("title"),
            "status": paper.get("status"),
            "version": paper.get("version", 1),
            "reports_count": len(reports),
            "reports": serialize_docs(reports),
            "reviews": serialize_docs(reviews),
            "audit_timeline": serialize_docs(audits)
        }
