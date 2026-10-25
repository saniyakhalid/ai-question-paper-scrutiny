import json
import csv
import io
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from pymongo.database import Database
from pymongo import ASCENDING, DESCENDING

from app.db.mongo import get_db, serialize_doc, serialize_docs, get_next_sequence
from app.schemas.schemas import ModeratorReviewCreate, ModeratorReviewResponse
from app.core.dependencies import get_current_user, require_role, MongoUser
from app.services.audit_service import AuditService

router = APIRouter(prefix="/moderator", tags=["Moderator Supervision"])
@router.post("/reviews/{paper_id}", response_model=Dict[str, Any])
def submit_moderator_review(
    paper_id: int,
    review_in: ModeratorReviewCreate,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(require_role(["MODERATOR", "ADMIN"]))
):
    paper = db.question_papers.find_one({"id": paper_id})
    if not paper:
        raise HTTPException(status_code=404, detail="Question paper not found")
    if paper.get("validation_status") != "VALID_MATCH":
        raise HTTPException(
            status_code=409,
            detail="Moderator decisions are blocked until subject and document validation returns VALID_MATCH.",
        )

    report = db.scrutiny_reports.find_one({"paper_id": paper_id}, sort=[("version", DESCENDING)])
    if not report:
        raise HTTPException(status_code=409, detail="Moderator decisions are blocked until a scrutiny report is available.")
    report_id = report.get("id")

    # Map decision string
    dec_upper = (review_in.new_status or review_in.decision).upper()
    if dec_upper in ("APPROVED", "APPROVE"):
        status_str = "APPROVED"
    elif dec_upper in ("REJECTED", "REJECT"):
        status_str = "REJECTED"
    elif dec_upper in ("DECLINED", "DECLINE", "REVIEW_DECLINED"):
        status_str = "REVIEW_DECLINED"
    elif dec_upper in ("MODIFY", "MODIFICATION_REQUIRED", "NEEDS_MODIFICATION", "CHANGES_REQUESTED", "CHANGE", "CHANGES", "REQUEST_CHANGES", "CHANGE_REQUESTED"):
        status_str = "MODIFICATION_REQUIRED"
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid decision option. Use APPROVED, REJECTED, REVIEW_DECLINED, or MODIFICATION_REQUIRED."
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    review_id = get_next_sequence("moderator_reviews")
    previous_status = paper.get("status") or "SUBMITTED"

    corrections_list = [c.model_dump() if hasattr(c, "model_dump") else dict(c) for c in (review_in.corrections or [])]

    faculty_id = paper.get("uploaded_by_id")
    faculty_user = db.users.find_one({"id": faculty_id}) if faculty_id else None
    faculty_name = faculty_user.get("full_name") if faculty_user else None

    default_action = (
        "Paper approved for examination cell" if status_str == "APPROVED"
        else "Moderator declined review; paper requires reassignment" if status_str == "REVIEW_DECLINED"
        else "Paper rejected; please review moderator remarks" if status_str == "REJECTED"
        else "Please review and update question paper according to moderator remarks"
    )

    review_doc = {
        "id": review_id,
        "paper_id": paper_id,
        "report_id": report_id,
        "moderator_id": current_user.id,
        "moderator_name": current_user.full_name or current_user.email,
        "moderator_role": current_user.role,
        "faculty_id": faculty_id,
        "faculty_name": faculty_name,
        "decision": status_str,
        "previous_status": previous_status,
        "new_status": status_str,
        "remarks": review_in.remarks or "",
        "required_action": getattr(review_in, "required_action", None) or default_action,
        "corrections": corrections_list,
        "created_at": now_iso,
        "updated_at": now_iso,
    }
    db.moderator_reviews.insert_one(review_doc)

    # Update paper status and cache moderator feedback in question_papers
    db.question_papers.update_one(
        {"id": paper_id},
        {"$set": {
            "status": status_str,
            "moderator_decision": status_str,
            "moderator_feedback": review_in.remarks,
            "moderator_required_action": getattr(review_in, "required_action", None) or default_action,
            "moderator_name": current_user.full_name,
            "moderated_at": now_iso
        }}
    )

    # Apply corrections to active scrutiny findings in MongoDB
    for corr in corrections_list:
        if report_id:
            db.scrutiny_findings.update_one(
                {
                    "report_id": report_id,
                    "question_id": corr.get("question_id"),
                    "finding_type": corr.get("finding_type")
                },
                {"$set": {
                    "ai_value": corr.get("corrected_value"),
                    "reasoning": f"Updated by moderator: {corr.get('reason', 'Corrected by moderator')}"
                }}
            )

    AuditService.log_action(
        db,
        action=f"MODERATOR_{status_str}",
        entity="QuestionPaper",
        entity_id=paper_id,
        user_id=current_user.id,
        user_role=current_user.role,
        metadata={
            "decision": status_str,
            "previous_status": previous_status,
            "new_status": status_str,
            "corrections_count": len(corrections_list),
        },
        details=f"Moderator {current_user.full_name} issued decision '{status_str}' for paper #{paper_id}. Remarks: {review_in.remarks[:100]}"
    )

    return serialize_doc(review_doc)


@router.get("/reviews/{paper_id}", response_model=Dict[str, Any])
def get_moderator_review(
    paper_id: int,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user)
):
    """Retrieves the latest moderator review and feedback for a paper."""
    paper = db.question_papers.find_one({"id": paper_id})
    if not paper:
        raise HTTPException(status_code=404, detail="Question paper not found")

    if current_user.role == "FACULTY" and paper.get("uploaded_by_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    review = db.moderator_reviews.find_one({"paper_id": paper_id}, sort=[("id", DESCENDING)])
    if not review:
        if paper.get("moderator_feedback") or paper.get("moderator_decision"):
            fallback_rev = {
                "id": 0,
                "paper_id": paper_id,
                "moderator_name": paper.get("moderator_name") or "Chief Examination Moderator",
                "decision": paper.get("moderator_decision") or paper.get("status"),
                "remarks": paper.get("moderator_feedback") or "",
                "required_action": paper.get("moderator_required_action") or "",
                "created_at": paper.get("moderated_at") or "",
                "corrections": []
            }
            return {"has_review": True, "review": fallback_rev}
        return {"has_review": False, "review": None}

    ser_review = serialize_doc(review)
    if not ser_review.get("remarks") and paper.get("moderator_feedback"):
        ser_review["remarks"] = paper.get("moderator_feedback")
    if not ser_review.get("required_action") and paper.get("moderator_required_action"):
        ser_review["required_action"] = paper.get("moderator_required_action")
    return {"has_review": True, "review": ser_review}


@router.get("/feedback/export")
def export_feedback_dataset(
    format: str = "csv",
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(require_role(["MODERATOR", "ADMIN"]))
):
    reviews = list(db.moderator_reviews.find().sort("id", DESCENDING))
    data = []
    for r in reviews:
        for c in r.get("corrections", []):
            data.append({
                "review_id": r.get("id"),
                "paper_id": r.get("paper_id"),
                "moderator_name": r.get("moderator_name"),
                "decision": r.get("decision"),
                "question_id": c.get("question_id"),
                "finding_type": c.get("finding_type"),
                "original_ai_value": c.get("original_ai_value"),
                "corrected_value": c.get("corrected_value"),
                "reason": c.get("reason"),
                "remarks": r.get("remarks"),
                "created_at": r.get("created_at", "")
            })

    if format == "json":
        return Response(
            content=json.dumps(data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=moderator_feedback_dataset.json"}
        )

    output = io.StringIO()
    fields = ["review_id", "paper_id", "moderator_name", "decision", "question_id", "finding_type", "original_ai_value", "corrected_value", "reason", "remarks", "created_at"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows(data)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=moderator_feedback_dataset.csv"}
    )
