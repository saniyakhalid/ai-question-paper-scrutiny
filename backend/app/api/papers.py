import os
import json
import logging
import tempfile
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pymongo.database import Database
from pymongo import ASCENDING, DESCENDING

from app.core.config import settings
from app.db.mongo import get_db, serialize_doc, serialize_docs, get_next_sequence
from app.schemas.schemas import PaperOut
from app.core.dependencies import get_current_user, require_role, MongoUser
from app.services.extraction_service import ScannedDocumentException
from app.services.audit_service import AuditService
from app.services.scrutiny_pipeline import extract_and_store_questions, run_scrutiny_analysis
from app.services.extraction_service import DocumentExtractionService
from app.services.question_parser import QuestionParserService
from app.services.subject_validation_service import validate_paper_subject

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/papers", tags=["Question Papers"])


def _save_upload_file(upload: UploadFile, file_path: str) -> int:
    """Copy an uploaded document with the configured size limit enforced server-side."""
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    total = 0
    try:
        with open(file_path, "wb") as buffer:
            while True:
                chunk = upload.file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB upload limit.",
                    )
                buffer.write(chunk)
        return total
    except Exception:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise


@router.get("", response_model=List[PaperOut])
def list_papers(
    subject_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user)
):
    """
    List question papers with strict Role-Based Access Control:
    - FACULTY: Sees ONLY their own uploaded papers.
    - MODERATOR & ADMIN: Can view all papers.
    """
    query: Dict[str, Any] = {}
    if current_user.role == "FACULTY":
        query["uploaded_by_id"] = current_user.id
    if subject_id:
        query["subject_id"] = subject_id
    if status_filter:
        query["status"] = status_filter

    papers = list(db.question_papers.find(query).sort("id", DESCENDING))
    result = []
    for p in papers:
        ser = serialize_doc(p)
        # Populate subject details
        subj = db.subjects.find_one({"id": p.get("subject_id")})
        ser["subject"] = serialize_doc(subj) if subj else None

        # Populate moderator review/feedback if not already on the paper document
        rev = db.moderator_reviews.find_one({"paper_id": p.get("id")}, sort=[("id", DESCENDING)])
        if rev:
            ser["moderator_review"] = serialize_doc(rev)
            if not ser.get("moderator_feedback"):
                ser["moderator_feedback"] = rev.get("remarks")
            if not ser.get("moderator_decision"):
                ser["moderator_decision"] = rev.get("decision")
            if not ser.get("moderator_name"):
                ser["moderator_name"] = rev.get("moderator_name")
            if not ser.get("moderator_required_action"):
                ser["moderator_required_action"] = rev.get("required_action")
            if not ser.get("moderated_at"):
                ser["moderated_at"] = rev.get("created_at")

        result.append(PaperOut.model_validate(ser))
    return result


@router.get("/{id}", response_model=PaperOut)
def get_paper(
    id: int,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user)
):
    """
    Retrieves full question paper details with question breakdown, subject, and moderator review.
    Enforces RBAC: Faculty cannot view other faculty's papers.
    """
    paper = db.question_papers.find_one({"id": id})
    if not paper:
        raise HTTPException(status_code=404, detail="Question paper not found")

    if current_user.role == "FACULTY" and paper.get("uploaded_by_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied: You can only view your own question papers.")

    ser = serialize_doc(paper)

    # Populate subject
    subj = db.subjects.find_one({"id": paper.get("subject_id")})
    ser["subject"] = serialize_doc(subj) if subj else None

    # Populate questions sorted by sequence order
    questions = list(db.extracted_questions.find({"paper_id": id}).sort("sequence_order", ASCENDING))
    ser["questions"] = serialize_docs(questions)

    # Populate latest moderator review
    review = db.moderator_reviews.find_one({"paper_id": id}, sort=[("id", DESCENDING)])
    if review:
        ser["moderator_review"] = serialize_doc(review)
        ser["moderator_feedback"] = review.get("remarks") or ser.get("moderator_feedback")
        ser["moderator_decision"] = review.get("decision") or ser.get("moderator_decision")
        ser["moderator_required_action"] = review.get("required_action") or ser.get("moderator_required_action")
        ser["moderator_name"] = review.get("moderator_name") or ser.get("moderator_name")
        ser["moderated_at"] = review.get("created_at") or ser.get("moderated_at")

    return PaperOut.model_validate(ser)


@router.post("/validate-subject")
def validate_subject_before_upload(
    subject_id: int = Form(...),
    file: UploadFile = File(...),
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user),
):
    """
    Pre-upload subject isolation check. Extracts document text temporarily,
    validates against selected subject workspace, and returns pass/fail without persisting.
    """
    subject = db.subjects.find_one({"id": subject_id})
    if not subject:
        raise HTTPException(status_code=404, detail="Selected subject not found")

    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower().replace(".", "")
    if ext not in ["pdf", "docx", "txt"]:
        raise HTTPException(status_code=400, detail="Supported files: PDF, DOCX, TXT")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            prefix=f"_validate_{current_user.id}_{subject_id}_",
            suffix=f".{ext}",
            dir=settings.UPLOAD_DIR,
            delete=False,
        ) as temp_file:
            temp_path = temp_file.name
        _save_upload_file(file, temp_path)

        raw_text = DocumentExtractionService.extract_text(temp_path, ext)
        detailed = QuestionParserService.parse_paper_detailed(raw_text)
        header_meta = (detailed.get("header_metadata") or {})
        detected_code = header_meta.get("subject_code_detected")
        questions = detailed.get("questions") or []

        validation = validate_paper_subject(
            db,
            subject_id=subject_id,
            raw_text=detailed.get("raw_text") or raw_text,
            questions=questions,
            detected_subject_code=detected_code,
            filename=filename,
        )
        if not validation.get("valid"):
            outcome = validation.get("outcome", "inconclusive")
            AuditService.log_action(
                db,
                action="SUBJECT_MISMATCH" if outcome == "mismatch" else "SUBJECT_VALIDATION_INCONCLUSIVE",
                entity="SubjectValidation",
                entity_id=subject_id,
                user_id=current_user.id,
                user_role=current_user.role,
                metadata={"selected_subject_id": subject_id, "filename": filename, "validation": validation},
                details=f"Pre-upload subject validation returned {outcome} for the selected subject."
            )
        return validation
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning(f"Subject validation extraction failed: {exc}")
        validation = {
            "valid": False,
            "outcome": "inconclusive",
            "check": "document_extraction_failed",
            "message": "Could not read enough text to verify the document. Upload a readable PDF, DOCX, or TXT question paper.",
        }
        AuditService.log_action(
            db,
            action="SUBJECT_VALIDATION_INCONCLUSIVE",
            entity="SubjectValidation",
            entity_id=subject_id,
            user_id=current_user.id,
            user_role=current_user.role,
            metadata={"selected_subject_id": subject_id, "filename": filename, "validation": validation},
            details="Pre-upload subject validation could not read sufficient document evidence."
        )
        return validation
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


@router.post("/upload", response_model=PaperOut, status_code=status.HTTP_201_CREATED)
def upload_paper(
    title: str = Form(...),
    subject_id: int = Form(...),
    academic_year: str = Form(...),
    exam_type: str = Form(...),
    examination_id: Optional[int] = Form(None),
    selected_units: Optional[str] = Form(None),
    auto_analyze: bool = Form(True),
    file: UploadFile = File(...),
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(require_role(["FACULTY", "ADMIN", "MODERATOR"]))
):
    """
    Upload question paper, extract questions, and execute complete scrutiny pipeline.
    Persists cleanly to MongoDB and creates audit log entry.
    """
    subject = db.subjects.find_one({"id": subject_id})
    if not subject:
        raise HTTPException(status_code=404, detail="Selected subject not found")

    parsed_units = None
    if selected_units:
        try:
            if selected_units.startswith("["):
                parsed_units = json.loads(selected_units)
            else:
                parsed_units = [int(u.strip()) for u in selected_units.split(",") if u.strip().isdigit()]
        except Exception:
            parsed_units = None

    if not parsed_units:
        units = list(db.syllabus_units.find({"subject_id": subject_id}))
        parsed_units = [u["unit_number"] for u in units] if units else []

    ext = os.path.splitext(file.filename or "")[1].lower().replace(".", "")
    if ext not in ["pdf", "docx", "txt"]:
        raise HTTPException(status_code=400, detail="Supported files: PDF, DOCX, TXT")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    paper_id = get_next_sequence("question_papers")
    saved_filename = f"paper_{current_user.id}_{paper_id}.{ext}"
    saved_path = os.path.join(settings.UPLOAD_DIR, saved_filename)

    _save_upload_file(file, saved_path)

    paper_doc = {
        "id": paper_id,
        "title": title,
        "subject_id": subject_id,
        "examination_id": examination_id,
        "uploaded_by_id": current_user.id,
        "filename": file.filename,
        "filepath": saved_path,
        "file_path": saved_path,
        "file_type": ext,
        "academic_year": academic_year,
        "exam_type": exam_type,
        "selected_units_json": parsed_units,
        "status": "SUBMITTED",
        "validation_status": "PENDING",
        "validation_details": None,
        "overall_score": None,
        "version": 1,
        "raw_text": None,
        "normalized_text": None,
        "instructions_json": []
    }
    db.question_papers.insert_one(paper_doc)

    # Step 1: Extraction & question parsing
    ext_result = extract_and_store_questions(db, paper_doc)
    if not ext_result.get("ok"):
        message = ext_result.get("error") or "Document extraction failed."
        validation_details = {"outcome": "processing_error", "message": message}
        db.question_papers.update_one(
            {"id": paper_id},
            {"$set": {
                "status": "EXTRACTION_FAILED",
                "validation_status": "DOCUMENT_PROCESSING_FAILED",
                "validation_details": validation_details,
                "overall_score": None,
            }}
        )
        AuditService.log_action(
            db,
            action="DOCUMENT_PROCESSING_FAILED",
            entity="QuestionPaper",
            entity_id=paper_id,
            user_id=current_user.id,
            user_role=current_user.role,
            metadata={"validation_status": "DOCUMENT_PROCESSING_FAILED", "message": message},
            details=f"Document extraction failed for paper #{paper_id}; no scrutiny score was generated."
        )
        raise HTTPException(
            status_code=422,
            detail={"code": "DOCUMENT_PROCESSING_FAILED", "outcome": "processing_error", "message": message, "paper_id": paper_id},
        )

    # Step 1b: Subject isolation — reject cross-subject uploads
    detailed = ext_result.get("detailed") or {}
    header_meta = detailed.get("header_metadata") or {}
    detected_code = header_meta.get("subject_code_detected")
    questions = list(db.extracted_questions.find({"paper_id": paper_id}))
    updated_paper = db.question_papers.find_one({"id": paper_id}) or paper_doc
    raw_text = updated_paper.get("raw_text") or detailed.get("raw_text") or ""

    validation = validate_paper_subject(
        db,
        subject_id=subject_id,
        raw_text=raw_text,
        questions=questions,
        detected_subject_code=detected_code,
        filename=file.filename,
    )
    if not validation.get("valid"):
        outcome = validation.get("outcome", "inconclusive")
        validation_status = "SUBJECT_MISMATCH" if outcome == "mismatch" else "VALIDATION_INCONCLUSIVE"
        status_value = validation_status
        db.question_papers.update_one(
            {"id": paper_id},
            {"$set": {
                "status": status_value,
                "validation_status": validation_status,
                "validation_details": validation,
                "overall_score": None,
            }}
        )
        AuditService.log_action(
            db,
            action=f"{validation_status}",
            entity="QuestionPaper",
            entity_id=paper_id,
            user_id=current_user.id,
            user_role=current_user.role,
            metadata={"selected_subject_id": subject_id, "validation": validation, "filename": file.filename},
            details=f"Subject/document validation returned {outcome} for paper #{paper_id}; no scrutiny score was generated."
        )
        raise HTTPException(
            status_code=422,
            detail={
                "code": "SUBJECT_MISMATCH" if outcome == "mismatch" else "SUBJECT_VALIDATION_INCONCLUSIVE",
                "outcome": outcome,
                "message": validation.get("message") or "Could not verify the document subject.",
                "validation": validation,
                "paper_id": paper_id,
            },
        )

    db.question_papers.update_one(
        {"id": paper_id},
        {"$set": {"validation_status": "VALID_MATCH", "validation_details": validation}}
    )
    paper_doc["validation_status"] = "VALID_MATCH"
    paper_doc["validation_details"] = validation

    AuditService.log_action(
        db,
        action="UPLOAD",
        entity="QuestionPaper",
        entity_id=paper_id,
        user_id=current_user.id,
        user_role=current_user.role,
        metadata={"filename": file.filename, "selected_units": parsed_units, "auto_analyze": auto_analyze, "validation_status": "VALID_MATCH"},
        details=f"Uploaded question paper '{title}' for subject {subject.get('code')}"
    )

    # Step 2: Auto-analysis
    if auto_analyze:
        analysis = run_scrutiny_analysis(db, paper_doc)
        if not analysis.get("ok"):
            raise HTTPException(
                status_code=502,
                detail=analysis.get("error") or "Scrutiny analysis failed. You can resume from the paper page.",
            )
        AuditService.log_action(
            db,
            action="ANALYZE",
            entity="QuestionPaper",
            entity_id=paper_id,
            user_id=current_user.id,
            user_role=current_user.role,
            metadata={"report_id": analysis.get("report_id"), "score": analysis.get("overall_score")},
            details=f"Completed automated scrutiny for paper #{paper_id}. Score: {analysis.get('overall_score')}/100"
        )

    updated_paper = db.question_papers.find_one({"id": paper_id})
    ser = serialize_doc(updated_paper)
    ser["subject"] = serialize_doc(subject)
    questions = list(db.extracted_questions.find({"paper_id": paper_id}).sort("sequence_order", ASCENDING))
    ser["questions"] = serialize_docs(questions)
    return PaperOut.model_validate(ser)


@router.post("/{paper_id}/analyze")
def analyze_paper(
    paper_id: int,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user),
):
    paper = db.question_papers.find_one({"id": paper_id})
    if not paper:
        raise HTTPException(status_code=404, detail="Question paper not found")

    if current_user.role == "FACULTY" and paper.get("uploaded_by_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if paper.get("validation_status") != "VALID_MATCH":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "SCRUTINY_BLOCKED_BY_VALIDATION",
                "validation_status": paper.get("validation_status") or "NOT_VALIDATED",
                "message": "Scrutiny cannot run until subject and document validation passes.",
            },
        )

    q_count = db.extracted_questions.count_documents({"paper_id": paper_id})
    if q_count == 0 and paper.get("file_path") and os.path.exists(paper["file_path"]):
        res = extract_and_store_questions(db, paper)
        if not res.get("ok"):
            raise HTTPException(status_code=422, detail=res.get("error"))

    analysis = run_scrutiny_analysis(db, paper)
    if not analysis.get("ok"):
        raise HTTPException(status_code=422, detail=analysis.get("error") or "Analysis failed")

    AuditService.log_action(
        db,
        action="ANALYZE",
        entity="QuestionPaper",
        entity_id=paper_id,
        user_id=current_user.id,
        user_role=current_user.role,
        metadata={"report_id": analysis.get("report_id"), "score": analysis.get("overall_score")},
        details=f"Analyzed paper #{paper_id}. Overall score: {analysis.get('overall_score')}/100"
    )
    return analysis


@router.post("/{paper_id}/resume")
def resume_scrutiny(
    paper_id: int,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user),
):
    return analyze_paper(paper_id, db, current_user)


class UpdatePaperUnitsPayload(BaseModel):
    selected_units: List[int]


@router.put("/{paper_id}/units")
def update_paper_units(
    paper_id: int,
    payload: UpdatePaperUnitsPayload,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(require_role(["FACULTY", "ADMIN", "MODERATOR"])),
):
    paper = db.question_papers.find_one({"id": paper_id})
    if not paper:
        raise HTTPException(status_code=404, detail="Question paper not found")
    if current_user.role == "FACULTY" and paper.get("uploaded_by_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    db.question_papers.update_one(
        {"id": paper_id},
        {"$set": {"selected_units_json": payload.selected_units}}
    )
    return {"ok": True, "selected_units": payload.selected_units}


@router.delete("/{paper_id}")
def delete_paper(
    paper_id: int,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user)
):
    """
    Safely deletes a question paper with full cascade cleanup:
    - Removes questions, scrutiny reports, rule results, findings, similarity results, moderator reviews.
    - Removes the uploaded document file from disk.
    - Records audit log entry.
    - RBAC: Allowed for ADMIN, MODERATOR, or the FACULTY owner (if paper is not yet APPROVED).
    """
    paper = db.question_papers.find_one({"id": paper_id})
    if not paper:
        raise HTTPException(status_code=404, detail="Question paper not found")

    # RBAC validation
    is_owner = paper.get("uploaded_by_id") == current_user.id
    is_mod_or_admin = current_user.role in ("ADMIN", "MODERATOR")

    if not is_mod_or_admin and not is_owner:
        raise HTTPException(status_code=403, detail="You do not have permission to delete this question paper.")

    if not is_mod_or_admin and paper.get("status") == "APPROVED":
        raise HTTPException(status_code=400, detail="Approved question papers cannot be deleted by faculty. Contact moderator.")

    # 1. Cascading database cleanup
    db.extracted_questions.delete_many({"paper_id": paper_id})
    reports = list(db.scrutiny_reports.find({"paper_id": paper_id}))
    rep_ids = [r["id"] for r in reports]
    if rep_ids:
        db.rule_results.delete_many({"report_id": {"$in": rep_ids}})
        db.scrutiny_findings.delete_many({"report_id": {"$in": rep_ids}})
        db.similarity_results.delete_many({"report_id": {"$in": rep_ids}})
    db.scrutiny_reports.delete_many({"paper_id": paper_id})
    db.moderator_reviews.delete_many({"paper_id": paper_id})
    db.question_papers.delete_one({"id": paper_id})

    # 2. File cleanup
    file_path = paper.get("file_path") or paper.get("filepath")
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            logger.warning(f"Could not remove physical file {file_path}: {e}")

    # 3. Audit log
    AuditService.log_action(
        db,
        action="DELETE",
        entity="QuestionPaper",
        entity_id=paper_id,
        user_id=current_user.id,
        user_role=current_user.role,
        metadata={"title": paper.get("title"), "subject_id": paper.get("subject_id")},
        details=f"Permanently deleted question paper #{paper_id} ('{paper.get('title')}') and all associated scrutiny records"
    )

    return {
        "ok": True,
        "message": f"Question paper #{paper_id} ('{paper.get('title')}') and all related scrutiny records were permanently deleted.",
        "paper_id": paper_id
    }
