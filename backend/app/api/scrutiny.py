from fastapi import APIRouter, Depends, HTTPException, Response
from pymongo.database import Database
from pymongo import ASCENDING, DESCENDING
from typing import Dict, Any, List

from app.db.mongo import get_db, serialize_doc, serialize_docs
from app.schemas.schemas import ScrutinyReportResponse
from app.core.dependencies import get_current_user, MongoUser
from app.services.report_service import report_service
from app.utils.pdf_export import PDFReportExporter

router = APIRouter(prefix="/scrutiny", tags=["Scrutiny & Reports"])


def _assert_paper_access(db: Database, paper_id: int, current_user: MongoUser) -> None:
    paper = db.question_papers.find_one({"id": paper_id})
    if not paper:
        raise HTTPException(status_code=404, detail="Question paper not found")
    if current_user.role == "FACULTY" and paper.get("uploaded_by_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")


def _build_full_report_payload(db: Database, paper_id: int) -> Dict[str, Any]:
    """Helper to assemble comprehensive scrutiny data from MongoDB for export & viewing."""
    paper = db.question_papers.find_one({"id": paper_id})
    if not paper:
        raise HTTPException(status_code=404, detail="Question paper not found")

    report = db.scrutiny_reports.find_one({"paper_id": paper_id}, sort=[("version", DESCENDING)])
    if not report:
        raise HTTPException(status_code=404, detail="Scrutiny report not generated yet for this paper")

    subject = db.subjects.find_one({"id": paper.get("subject_id")}) or {}
    report_id = report.get("id")

    questions = list(db.extracted_questions.find({"paper_id": paper_id}).sort("sequence_order", ASCENDING))
    q_breakdown = []
    for q in questions:
        f_bloom = db.scrutiny_findings.find_one({"report_id": report_id, "question_id": q.get("id"), "finding_type": "BLOOM"})
        f_co = db.scrutiny_findings.find_one({"report_id": report_id, "question_id": q.get("id"), "finding_type": "CO"})
        f_syl = db.scrutiny_findings.find_one({"report_id": report_id, "question_id": q.get("id"), "finding_type": "SYLLABUS"})
        f_gram = db.scrutiny_findings.find_one({"report_id": report_id, "question_id": q.get("id"), "finding_type": "GRAMMAR"})

        bloom_val = q.get("bloom_level") or (f_bloom.get("ai_value") if f_bloom else "—")
        co_val = q.get("co_code") or (f_co.get("ai_value") if f_co else "—")
        unit_str = f"Unit {q.get('detected_unit_number')}" if q.get("detected_unit_number") is not None else ""
        topic_str = q.get("topic_name") or ""
        unit_topic = f"{unit_str} - {topic_str}".strip(" -") or (f_syl.get("ai_value") if f_syl else "—")

        q_breakdown.append({
            "q_num": q.get("original_number") or q.get("question_number"),
            "question_text": q.get("question_text", ""),
            "marks": q.get("marks"),
            "bloom": bloom_val,
            "co": co_val,
            "unit_topic": unit_topic,
            "grammar": f_gram.get("ai_value", "PASS") if f_gram else "PASS"
        })

    rule_results = list(db.rule_results.find({"report_id": report_id}))
    findings = list(db.scrutiny_findings.find({"report_id": report_id}))
    q_map = {q.get("id"): (q.get("original_number") or q.get("question_number")) for q in questions}
    annotated_findings = []
    for f in findings:
        f_ser = serialize_doc(f)
        f_ser["question_number"] = q_map.get(f.get("question_id"), "General")
        annotated_findings.append(f_ser)

    latest_review = db.moderator_reviews.find_one({"paper_id": paper_id}, sort=[("id", DESCENDING)])

    return {
        "paper_id": paper_id,
        "paper_title": paper.get("title", ""),
        "subject_code": subject.get("code", "N/A"),
        "subject_name": subject.get("name", "N/A"),
        "academic_year": paper.get("academic_year", "2025-2026"),
        "exam_type": paper.get("exam_type", "Regular"),
        "overall_score": report.get("overall_score") if report.get("overall_score") is not None else paper.get("overall_score"),
        "score_breakdown": report.get("score_breakdown"),
        "analysis_mode": report.get("analysis_mode"),
        "analysis_notice": report.get("analysis_notice"),
        "evidence_coverage_pct": report.get("evidence_coverage_pct"),
        "status": paper.get("status", "PENDING_REVIEW"),
        "solving_time_minutes": report.get("solving_time_minutes"),
        "questions_breakdown": q_breakdown,
        "rule_results": serialize_docs(rule_results),
        "findings": annotated_findings,
        "decision": latest_review.get("decision") if latest_review else "PENDING REVIEW",
        "remarks": latest_review.get("remarks") if latest_review else "Awaiting Moderator Review.",
        "required_action": latest_review.get("required_action") if latest_review else "No action required.",
        "moderator_name": latest_review.get("moderator_name") if latest_review else "Chief Examination Moderator",
        "moderated_at": latest_review.get("created_at") or latest_review.get("reviewed_at") if latest_review else "",
    }



@router.get("/{paper_id}", response_model=ScrutinyReportResponse)
def get_paper_scrutiny(
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
        raise HTTPException(status_code=404, detail="Scrutiny report not found for this paper")

    ser = serialize_doc(report)
    ser["rule_results"] = serialize_docs(list(db.rule_results.find({"report_id": report["id"]})))
    ser["findings"] = serialize_docs(list(db.scrutiny_findings.find({"report_id": report["id"]})))
    ser["similarity_results"] = serialize_docs(list(db.similarity_results.find({"report_id": report["id"]})))
    return ScrutinyReportResponse.model_validate(ser)


@router.get("/reports/{paper_id}/export/pdf")
def export_pdf_report(
    paper_id: int,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user)
):
    _assert_paper_access(db, paper_id, current_user)
    payload = _build_full_report_payload(db, paper_id)
    pdf_bytes = PDFReportExporter.create_pdf_report(payload)
    filename = f"Scrutiny_Report_Paper_{paper_id}_{payload['subject_code']}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/reports/{paper_id}/export/csv")
def export_csv_report(
    paper_id: int,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user)
):
    _assert_paper_access(db, paper_id, current_user)
    payload = _build_full_report_payload(db, paper_id)
    csv_data = report_service.generate_csv_export(payload)
    filename = f"Scrutiny_Report_Paper_{paper_id}_{payload['subject_code']}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/reports/{paper_id}/export/json")
def export_json_report(
    paper_id: int,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user)
):
    _assert_paper_access(db, paper_id, current_user)
    payload = _build_full_report_payload(db, paper_id)
    json_data = report_service.generate_json_export(payload)
    filename = f"Scrutiny_Report_Paper_{paper_id}_{payload['subject_code']}.json"
    return Response(
        content=json_data,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
