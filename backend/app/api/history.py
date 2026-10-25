from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.database import Database
from pymongo import ASCENDING, DESCENDING

from app.db.mongo import get_db, serialize_doc, serialize_docs
from app.core.dependencies import get_current_user, MongoUser
from app.services.audit_service import AuditService

router = APIRouter(prefix="/history", tags=["Scrutiny History & Audit"])


@router.get("", response_model=List[Dict[str, Any]])
def list_paper_history(
    subject_id: Optional[int] = Query(None, description="Filter history by subject ID"),
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user)
):
    query: Dict[str, Any] = {}
    if current_user.role == "FACULTY":
        query["uploaded_by_id"] = current_user.id
    if subject_id:
        query["subject_id"] = subject_id

    papers = list(db.question_papers.find(query).sort("id", DESCENDING))

    results = []
    for p in papers:
        paper_id = p.get("id")
        latest_report = db.scrutiny_reports.find_one({"paper_id": paper_id}, sort=[("version", DESCENDING)])
        latest_review = db.moderator_reviews.find_one({"paper_id": paper_id}, sort=[("id", DESCENDING)])

        score = p.get("overall_score")
        if score is None and latest_report and latest_report.get("overall_score") is not None:
            score = latest_report["overall_score"]
            db.question_papers.update_one({"id": paper_id}, {"$set": {"overall_score": score}})

        subject = db.subjects.find_one({"id": p.get("subject_id")}) or {}
        uploader = db.users.find_one({"id": p.get("uploaded_by_id")}) or {}

        results.append({
            "paper_id": paper_id,
            "title": p.get("title"),
            "subject_id": p.get("subject_id"),
            "subject_code": subject.get("code", "N/A"),
            "subject_name": subject.get("name", "N/A"),
            "academic_year": p.get("academic_year", "2025-2026"),
            "exam_type": p.get("exam_type", "End-Semester"),
            "uploaded_by": uploader.get("full_name", "Faculty"),
            "uploaded_by_id": p.get("uploaded_by_id"),
            "status": p.get("status", "SUBMITTED"),
            "validation_status": p.get("validation_status"),
            "validation_details": p.get("validation_details"),
            "version": p.get("version", 1),
            "uploaded_at": p.get("uploaded_at") or "",
            "overall_score": score,
            "moderator_decision": (latest_review.get("decision") if latest_review else None) or p.get("moderator_decision"),
            "moderator_name": (latest_review.get("moderator_name") if latest_review else None) or p.get("moderator_name"),
            "moderator_remarks": (latest_review.get("remarks") if latest_review else None) or p.get("moderator_feedback"),
            "moderator_required_action": (latest_review.get("required_action") if latest_review else None) or p.get("moderator_required_action"),
            "moderated_at": (latest_review.get("created_at") if latest_review else None) or p.get("moderated_at"),
        })
    return results


@router.get("/{paper_id}", response_model=Dict[str, Any])
def get_paper_full_timeline(
    paper_id: int,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user)
):
    paper = db.question_papers.find_one({"id": paper_id})
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    if current_user.role == "FACULTY" and paper.get("uploaded_by_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    subject = db.subjects.find_one({"id": paper.get("subject_id")}) or {}
    uploader = db.users.find_one({"id": paper.get("uploaded_by_id")}) or {}

    reports = list(db.scrutiny_reports.find({"paper_id": paper_id}).sort("version", ASCENDING))
    reviews = list(db.moderator_reviews.find({"paper_id": paper_id}).sort("id", ASCENDING))
    audits = list(db.audit_logs.find({"entity_type": "QuestionPaper", "entity_id": paper_id}).sort("id", ASCENDING))

    reports_data = [
        {
            "version": r.get("version"),
            "score": r.get("overall_score"),
            "solving_time_minutes": r.get("solving_time_minutes"),
            "created_at": r.get("created_at", "")
        }
        for r in reports
    ]

    reviews_data = [
        {
            "id": rw.get("id"),
            "moderator": rw.get("moderator_name", "Moderator"),
            "moderator_id": rw.get("moderator_id"),
            "decision": rw.get("decision"),
            "previous_status": rw.get("previous_status"),
            "new_status": rw.get("new_status") or rw.get("decision"),
            "remarks": rw.get("remarks"),
            "required_action": rw.get("required_action"),
            "created_at": rw.get("created_at") or rw.get("reviewed_at", ""),
            "corrections": rw.get("corrections", [])
        }
        for rw in reviews
    ]

    audits_data = [
        {
            "id": a.get("id"),
            "user_id": a.get("user_id"),
            "action": a.get("action"),
            "details": a.get("details"),
            "timestamp": a.get("timestamp", "")
        }
        for a in audits
    ]

    return {
        "paper_info": {
            "id": paper.get("id"),
            "title": paper.get("title"),
            "subject_code": subject.get("code", "N/A"),
            "subject_name": subject.get("name", "N/A"),
            "uploaded_by": uploader.get("full_name", "Faculty"),
            "status": paper.get("status"),
            "overall_score": paper.get("overall_score"),
            "uploaded_at": paper.get("uploaded_at", "")
        },
        "reports_history": reports_data,
        "moderator_reviews": reviews_data,
        "audit_timeline": audits_data
    }


@router.delete("/{paper_id}")
def delete_paper_history(
    paper_id: int,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user)
):
    """
    Deletes paper and all associated scrutiny history records.
    RBAC: ADMIN, MODERATOR, or owning FACULTY.
    """
    from app.api.papers import delete_paper
    return delete_paper(paper_id, db, current_user)
