import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pymongo.database import Database
from pymongo import DESCENDING

from app.core.config import settings
from app.db.mongo import get_db, serialize_doc, serialize_docs, get_next_sequence
from app.schemas.schemas import ScrutinyReportOut, ModeratorDecisionRequest
from app.core.dependencies import MongoUser, get_current_user, require_role
from app.services.report_service import ScrutinyReportService
from app.services.audit_service import AuditService
from app.utils.pdf_export import generate_reportlab_pdf

router = APIRouter(prefix="/reports", tags=["Scrutiny Reports & Decisions"])

@router.get("/{paper_id}", response_model=ScrutinyReportOut)
def get_latest_report(
    paper_id: int,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user)
):
    paper = db.question_papers.find_one({"id": paper_id})
    if not paper:
        raise HTTPException(status_code=404, detail="Question paper not found")
    if current_user.role == "FACULTY" and paper.get("uploaded_by_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    report = db.scrutiny_reports.find_one({"paper_id": paper_id}, sort=[("version", DESCENDING)])
    if not report:
        raise HTTPException(status_code=404, detail="Scrutiny report not generated yet for this paper")

    rep_id = report.get("id")
    rule_results = list(db.rule_results.find({"report_id": rep_id}))
    findings = list(db.scrutiny_findings.find({"report_id": rep_id}))
    similarities = list(db.similarity_results.find({"report_id": rep_id}))

    report["rule_results"] = serialize_docs(rule_results)
    report["findings"] = serialize_docs(findings)
    report["similarity_results"] = serialize_docs(similarities)

    return serialize_doc(report)

@router.post("/{paper_id}/decision")
def submit_moderator_decision(
    paper_id: int,
    decision: ModeratorDecisionRequest,
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

    old_status = paper.get("status") or "SUBMITTED"
    requested_decision = (decision.new_status or decision.decision or "").upper()
    if requested_decision in {"APPROVED", "APPROVE"}:
        new_status = "APPROVED"
    elif requested_decision in {"MODIFY", "MODIFICATION_REQUIRED", "NEEDS_MODIFICATION", "CHANGES_REQUESTED", "CHANGE", "CHANGES", "REQUEST_CHANGES", "CHANGE_REQUESTED"}:
        new_status = "MODIFICATION_REQUIRED"
    elif requested_decision in {"DECLINED", "DECLINE", "REVIEW_DECLINED"}:
        new_status = "REVIEW_DECLINED"
    elif requested_decision in {"REJECTED", "REJECT"}:
        new_status = "REJECTED"
    else:
        raise HTTPException(status_code=400, detail="Invalid decision option. Use APPROVED, MODIFICATION_REQUIRED, REVIEW_DECLINED, or REJECTED.")

    now = datetime.now(timezone.utc)

    db.question_papers.update_one(
        {"id": paper_id},
        {"$set": {
            "status": new_status,
            "moderator_decision": new_status,
            "moderator_feedback": decision.remarks,
            "moderator_name": current_user.full_name or current_user.email,
            "moderated_at": now.isoformat(),
        }}
    )

    rev_id = get_next_sequence("moderator_reviews")
    now = datetime.now(timezone.utc)
    review_doc = {
        "id": rev_id,
        "paper_id": paper_id,
        "moderator_id": current_user.id,
        "moderator_name": current_user.full_name or current_user.email,
        "moderator_role": current_user.role,
        "report_id": report.get("id"),
        "previous_status": old_status,
        "new_status": new_status,
        "decision": new_status,
        "remarks": decision.remarks,
        "feedback": decision.remarks,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "reviewed_at": now.isoformat(),
    }
    db.moderator_reviews.insert_one(review_doc)

    AuditService.log_action(
        db,
        action=new_status,
        entity="QuestionPaper",
        entity_id=paper_id,
        user_id=current_user.id,
        user_role=current_user.role,
        metadata={"remarks": decision.remarks, "previous_status": old_status, "new_status": new_status, "decision": new_status}
    )

    return {"message": "Moderator decision recorded successfully", "new_status": new_status}

@router.get("/{paper_id}/export/pdf")
def export_pdf_report(
    paper_id: int,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user)
):
    from app.api.scrutiny import export_pdf_report as scrutiny_export_pdf
    return scrutiny_export_pdf(paper_id=paper_id, db=db, current_user=current_user)

@router.get("/{paper_id}/export/csv")
def export_csv_report(
    paper_id: int,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user)
):
    from app.api.scrutiny import export_csv_report as scrutiny_export_csv
    return scrutiny_export_csv(paper_id=paper_id, db=db, current_user=current_user)

@router.get("/{paper_id}/export/json")
def export_json_report(
    paper_id: int,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user)
):
    from app.api.scrutiny import export_json_report as scrutiny_export_json
    return scrutiny_export_json(paper_id=paper_id, db=db, current_user=current_user)

