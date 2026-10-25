import os
import hashlib
import zipfile
import io
from datetime import datetime, timezone
from mimetypes import guess_type
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from pymongo.database import Database
from pymongo import ASCENDING, DESCENDING

from app.db.mongo import get_db, serialize_doc, serialize_docs, get_next_sequence
from app.core.config import settings
from app.schemas.schemas import (
    SubjectCreate, SubjectUpdate, SubjectResponse, CourseOutcomeBase, CourseOutcomeResponse,
    CourseOutcomeBatchCreate,
    SyllabusUnitBase, SyllabusUnitCreate, SyllabusUnitResponse,
    SubjectDocumentResponse, SyllabusTopicBase, SyllabusTopicResponse
)
from app.core.dependencies import get_current_user, require_role, MongoUser
from app.services.document_service import document_service

router = APIRouter(prefix="/subjects", tags=["Subjects & Curriculum"])

UPLOAD_DIR = os.path.abspath(os.path.join(settings.UPLOAD_DIR, "subject_documents"))
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("", response_model=List[SubjectResponse])
def list_subjects(db: Database = Depends(get_db), current_user: MongoUser = Depends(get_current_user)):
    subjects = list(db.subjects.find().sort("id", ASCENDING))
    return [SubjectResponse.model_validate(serialize_doc(s)) for s in subjects]


@router.post("", response_model=SubjectResponse)
def create_subject(
    subject_in: SubjectCreate,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(require_role(["FACULTY", "ADMIN", "MODERATOR"]))
):
    subject_code = subject_in.code.strip().upper()
    if not subject_code or not subject_in.name.strip():
        raise HTTPException(status_code=422, detail="Subject code and name are required.")
    existing = next(
        (s for s in db.subjects.find() if (s.get("code") or "").strip().upper() == subject_code),
        None,
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"Subject code '{subject_code}' already exists.")

    unit_numbers = [unit.unit_number for unit in subject_in.syllabus_units]
    if any(number < 1 for number in unit_numbers) or len(unit_numbers) != len(set(unit_numbers)):
        raise HTTPException(status_code=422, detail="Syllabus unit numbers must be positive and unique.")
    if any(not unit.title.strip() or unit.title.strip() == "Unit Title" for unit in subject_in.syllabus_units):
        raise HTTPException(status_code=422, detail="Each syllabus unit needs a descriptive title.")

    sub_id = get_next_sequence("subjects")
    data = subject_in.model_dump(exclude={"course_outcomes", "syllabus_units"})
    data["code"] = subject_code
    data["name"] = subject_in.name.strip()
    data["department"] = subject_in.department.strip()
    data["branch"] = subject_in.branch.strip()
    data["id"] = sub_id
    db.subjects.insert_one(data)

    # Insert any initial Course Outcomes provided with the subject
    for co_in in subject_in.course_outcomes:
        co_code = co_in.co_code.strip()
        co_desc = co_in.description.strip()
        if co_code and co_desc:
            co_id = get_next_sequence("course_outcomes")
            db.course_outcomes.insert_one({
                "id": co_id,
                "subject_id": sub_id,
                "co_code": co_code,
                "description": co_desc
            })

    # Create only the curriculum details explicitly supplied by the user.
    for unit_in in subject_in.syllabus_units:
        unit_id = get_next_sequence("syllabus_units")
        topics = []
        for topic_in in unit_in.topics:
            topic_name = topic_in.topic_name.strip()
            if not topic_name:
                continue
            topic = {
                "id": get_next_sequence("syllabus_topics"),
                "unit_id": unit_id,
                "topic_name": topic_name,
                "description": topic_in.description or "",
                "co_id": topic_in.co_id,
            }
            db.syllabus_topics.insert_one(topic)
            topics.append(topic)
        db.syllabus_units.insert_one({
            "id": unit_id,
            "subject_id": sub_id,
            "unit_number": unit_in.unit_number,
            "title": unit_in.title.strip(),
            "description": unit_in.description or "",
            "topics": topics,
        })

    # Default exam pattern
    pat_id = get_next_sequence("examination_patterns")
    db.examination_patterns.update_one(
        {"subject_id": sub_id},
        {"$setOnInsert": {
            "id": pat_id,
            "subject_id": sub_id,
            "total_marks": data.get("total_marks", 100),
            "duration_minutes": data.get("duration_minutes", 180)
        }},
        upsert=True
    )

    created = serialize_doc(db.subjects.find_one({"id": sub_id}))
    created["course_outcomes"] = serialize_docs(list(db.course_outcomes.find({"subject_id": sub_id})))
    created["syllabus_units"] = serialize_docs(list(db.syllabus_units.find({"subject_id": sub_id}).sort("unit_number", ASCENDING)))
    return SubjectResponse.model_validate(created)


@router.get("/{subject_id}", response_model=SubjectResponse)
def get_subject(subject_id: int, db: Database = Depends(get_db), current_user: MongoUser = Depends(get_current_user)):
    subject = db.subjects.find_one({"id": subject_id})
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    return SubjectResponse.model_validate(serialize_doc(subject))


@router.put("/{subject_id}", response_model=SubjectResponse)
def update_subject(
    subject_id: int,
    subject_in: SubjectUpdate,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(require_role(["FACULTY", "ADMIN", "MODERATOR"])),
):
    subject = db.subjects.find_one({"id": subject_id})
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    updates = {
        key: value
        for key, value in subject_in.model_dump(exclude_unset=True).items()
        if value is not None or key == "academic_year"
    }
    for key in ("code", "name", "department", "branch", "academic_year"):
        if key in updates:
            if key == "academic_year" and updates[key] is None:
                continue
            updates[key] = updates[key].strip()
            if key == "academic_year" and not updates[key]:
                updates[key] = None
            elif not updates[key]:
                raise HTTPException(status_code=422, detail=f"{key.replace('_', ' ').title()} cannot be empty.")
    if "code" in updates:
        updates["code"] = updates["code"].upper()
        duplicate = next(
            (s for s in db.subjects.find() if s.get("id") != subject_id and (s.get("code") or "").strip().upper() == updates["code"]),
            None,
        )
        if duplicate:
            raise HTTPException(status_code=400, detail=f"Subject code '{updates['code']}' already exists.")

    if updates:
        db.subjects.update_one({"id": subject_id}, {"$set": updates})
        pattern_updates = {}
        if "total_marks" in updates:
            pattern_updates["total_marks"] = updates["total_marks"]
        if "duration_minutes" in updates:
            pattern_updates["duration_minutes"] = updates["duration_minutes"]
            pattern_updates["exam_duration_mins"] = updates["duration_minutes"]
        if "exam_duration" in updates:
            pattern_updates["duration_minutes"] = updates["exam_duration"]
            pattern_updates["exam_duration_mins"] = updates["exam_duration"]
        if pattern_updates:
            db.examination_patterns.update_one({"subject_id": subject_id}, {"$set": pattern_updates})

    result = serialize_doc(db.subjects.find_one({"id": subject_id}))
    result["course_outcomes"] = serialize_docs(list(db.course_outcomes.find({"subject_id": subject_id})))
    result["syllabus_units"] = serialize_docs(list(db.syllabus_units.find({"subject_id": subject_id}).sort("unit_number", ASCENDING)))
    return SubjectResponse.model_validate(result)


@router.delete("/{subject_id}")
def delete_subject(
    subject_id: int,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(require_role(["FACULTY", "ADMIN", "MODERATOR"])),
):
    subject = db.subjects.find_one({"id": subject_id})
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    # Cascade delete all linked records:
    # 1. Question papers and their sub-documents
    papers = list(db.question_papers.find({"subject_id": subject_id}))
    paper_ids = [p["id"] for p in papers if p.get("id") is not None]
    if paper_ids:
        db.extracted_questions.delete_many({"paper_id": {"$in": paper_ids}})
        db.scrutiny_reports.delete_many({"paper_id": {"$in": paper_ids}})
        db.scrutiny_findings.delete_many({"paper_id": {"$in": paper_ids}})
        db.rule_results.delete_many({"paper_id": {"$in": paper_ids}})
        db.moderator_reviews.delete_many({"paper_id": {"$in": paper_ids}})
        for p in papers:
            file_path = p.get("file_path") or p.get("pdf_path")
            if file_path and os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass
        db.question_papers.delete_many({"subject_id": subject_id})

    # 2. Previous papers and their questions
    prev_papers = list(db.previous_papers.find({"subject_id": subject_id}))
    prev_ids = [pp["id"] for pp in prev_papers if pp.get("id") is not None]
    if prev_ids:
        db.previous_questions.delete_many({"previous_paper_id": {"$in": prev_ids}})
        for pp in prev_papers:
            file_path = pp.get("file_path")
            if file_path and os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass
        db.previous_papers.delete_many({"subject_id": subject_id})

    # 3. Examinations
    db.examinations.delete_many({"subject_id": subject_id})

    # 4. Units & Topics
    unit_ids = [unit.get("id") for unit in db.syllabus_units.find({"subject_id": subject_id})]
    if unit_ids:
        db.syllabus_topics.delete_many({"unit_id": {"$in": unit_ids}})
    db.syllabus_units.delete_many({"subject_id": subject_id})

    # 5. Course outcomes & examination patterns
    db.course_outcomes.delete_many({"subject_id": subject_id})
    db.examination_patterns.delete_many({"subject_id": subject_id})

    # 6. PPTs and Syllabus Documents
    subject_docs = list(db.subject_documents.find({"subject_id": subject_id}))
    syllabus_docs = list(db.syllabus_documents.find({"subject_id": subject_id}))
    for document in subject_docs + syllabus_docs:
        file_path = document.get("file_path") or document.get("filepath")
        if file_path and os.path.isfile(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
    db.subject_documents.delete_many({"subject_id": subject_id})
    db.syllabus_documents.delete_many({"subject_id": subject_id})

    # 7. Delete the subject
    db.subjects.delete_one({"id": subject_id})

    # Clean up subject directories
    for sub_dir in [
        os.path.join(UPLOAD_DIR, f"subject_{subject_id}"),
        os.path.join(settings.UPLOAD_DIR, "syllabus", f"subject_{subject_id}")
    ]:
        if os.path.isdir(sub_dir):
            try:
                import shutil
                shutil.rmtree(sub_dir, ignore_errors=True)
            except Exception:
                pass

    return {"ok": True, "message": f"Subject {subject.get('code')} — {subject.get('name')} and all associated data deleted successfully."}


# Subject Document Upload & Management
@router.get("/{subject_id}/documents", response_model=List[SubjectDocumentResponse])
def list_subject_documents(subject_id: int, db: Database = Depends(get_db), current_user: MongoUser = Depends(get_current_user)):
    docs = list(db.subject_documents.find({"subject_id": subject_id, "doc_type": "PPT"}).sort("id", DESCENDING))
    uploader_ids = {doc.get("uploaded_by_id") for doc in docs if doc.get("uploaded_by_id") is not None}
    uploaders = {
        user.get("id"): user.get("full_name")
        for user in db.users.find({"id": {"$in": list(uploader_ids)}}, {"id": 1, "full_name": 1})
    }
    for doc in docs:
        doc["uploaded_by_name"] = doc.get("uploaded_by_name") or uploaders.get(doc.get("uploaded_by_id"), "Faculty")
    return [SubjectDocumentResponse.model_validate(serialize_doc(d)) for d in docs]


@router.post("/{subject_id}/documents", response_model=SubjectDocumentResponse)
async def upload_subject_document(
    subject_id: int,
    title: str = Form(""),
    unit_id: Optional[int] = Form(None),
    academic_year: Optional[str] = Form(None),
    semester: Optional[int] = Form(None),
    file: UploadFile = File(...),
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(require_role(["FACULTY", "ADMIN"]))
):
    subject = db.subjects.find_one({"id": subject_id})
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in {".pptx", ".ppt"}:
        raise HTTPException(status_code=400, detail="Only PowerPoint files (.ppt or .pptx) can be uploaded here.")
    if unit_id is not None and not db.syllabus_units.find_one({"id": unit_id, "subject_id": subject_id}):
        raise HTTPException(status_code=400, detail="The selected unit does not belong to this subject")

    subj_dir = os.path.join(UPLOAD_DIR, f"subject_{subject_id}")
    os.makedirs(subj_dir, exist_ok=True)

    safe_filename = os.path.basename((file.filename or "study-material").replace("\\", "/")) or "study-material"
    content = await file.read(settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024 + 1)
    if not content:
        raise HTTPException(status_code=400, detail="The selected PowerPoint file is empty.")
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"PowerPoint files must be {settings.MAX_UPLOAD_SIZE_MB} MB or smaller.")

    if ext == ".pptx":
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as presentation:
                valid_pptx = any(name.startswith("ppt/") or name == "[Content_Types].xml" for name in presentation.namelist())
        except (zipfile.BadZipFile, OSError):
            valid_pptx = False
        if not valid_pptx:
            raise HTTPException(status_code=400, detail="This file is not a valid .pptx presentation.")
    elif not (content.startswith(bytes.fromhex("D0CF11E0A1B11AE1")) or len(content) > 512):
        raise HTTPException(status_code=400, detail="This file is not a valid legacy .ppt presentation.")

    content_hash = hashlib.sha256(content).hexdigest()
    existing_documents = list(db.subject_documents.find({"subject_id": subject_id}))
    for existing_doc in existing_documents:
        existing_hash = existing_doc.get("content_sha256")
        existing_path = os.path.realpath(existing_doc.get("file_path") or existing_doc.get("filepath") or "")
        try:
            existing_path_is_safe = os.path.commonpath([os.path.realpath(UPLOAD_DIR), existing_path]) == os.path.realpath(UPLOAD_DIR)
        except ValueError:
            existing_path_is_safe = False
        if not existing_hash and existing_path_is_safe and os.path.isfile(existing_path):
            try:
                with open(existing_path, "rb") as existing_file:
                    existing_hash = hashlib.sha256(existing_file.read()).hexdigest()
            except OSError:
                existing_hash = None
        if existing_hash == content_hash:
            raise HTTPException(status_code=409, detail="This exact PowerPoint is already uploaded for this subject.")

    doc_id = get_next_sequence("subject_documents")
    file_location = os.path.join(subj_dir, f"{doc_id}_{safe_filename}")
    with open(file_location, "wb") as buffer:
        buffer.write(content)

    try:
        extracted_text = document_service.extract_text_from_file(file_location) if ext == ".pptx" else ""
    except Exception:
        extracted_text = ""
    doc_payload = {
        "id": doc_id,
        "subject_id": subject_id,
        "unit_id": unit_id,
        "doc_type": "PPT",
        "title": title.strip() or os.path.splitext(safe_filename)[0],
        "filename": safe_filename,
        "file_path": file_location,
        "academic_year": (academic_year or subject.get("academic_year") or "").strip() or None,
        "semester": semester or subject.get("semester"),
        "uploaded_by_id": current_user.id,
        "uploaded_by_name": current_user.full_name,
        "created_at": datetime.now(timezone.utc),
        "extracted_text": extracted_text,
        "content_sha256": content_hash,
    }
    db.subject_documents.insert_one(doc_payload)
    return SubjectDocumentResponse.model_validate(serialize_doc(doc_payload))


@router.put("/{subject_id}/documents/{doc_id}", response_model=SubjectDocumentResponse)
async def update_subject_document(
    subject_id: int,
    doc_id: int,
    title: Optional[str] = Form(None),
    unit_id: Optional[int] = Form(None),
    clear_unit: bool = Form(False),
    file: Optional[UploadFile] = File(None),
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(require_role(["FACULTY", "MODERATOR", "ADMIN"])),
):
    """Update PPT metadata and optionally replace the PowerPoint file. Multiple PPTs per subject are supported."""
    doc = db.subject_documents.find_one({"id": doc_id, "subject_id": subject_id, "doc_type": "PPT"})
    if not doc:
        raise HTTPException(status_code=404, detail="Subject document not found")

    updates: Dict[str, Any] = {}
    if title is not None:
        cleaned_title = title.strip()
        if not cleaned_title:
            raise HTTPException(status_code=422, detail="PPT title cannot be empty.")
        updates["title"] = cleaned_title

    if clear_unit:
        updates["unit_id"] = None
    elif unit_id is not None:
        if not db.syllabus_units.find_one({"id": unit_id, "subject_id": subject_id}):
            raise HTTPException(status_code=400, detail="The selected unit does not belong to this subject")
        updates["unit_id"] = unit_id

    if file is not None and (file.filename or "").strip():
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in {".pptx", ".ppt"}:
            raise HTTPException(status_code=400, detail="Only PowerPoint files (.ppt or .pptx) can be uploaded here.")

        content = await file.read(settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024 + 1)
        if not content:
            raise HTTPException(status_code=400, detail="The selected PowerPoint file is empty.")
        if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"PowerPoint files must be {settings.MAX_UPLOAD_SIZE_MB} MB or smaller.")

        if ext == ".pptx":
            try:
                with zipfile.ZipFile(io.BytesIO(content)) as presentation:
                    valid_pptx = any(name.startswith("ppt/") or name == "[Content_Types].xml" for name in presentation.namelist())
            except (zipfile.BadZipFile, OSError):
                valid_pptx = False
            if not valid_pptx:
                raise HTTPException(status_code=400, detail="This file is not a valid .pptx presentation.")
        elif not (content.startswith(bytes.fromhex("D0CF11E0A1B11AE1")) or len(content) > 512):
            raise HTTPException(status_code=400, detail="This file is not a valid legacy .ppt presentation.")

        content_hash = hashlib.sha256(content).hexdigest()
        for existing_doc in db.subject_documents.find({"subject_id": subject_id, "id": {"$ne": doc_id}}):
            if existing_doc.get("content_sha256") == content_hash:
                raise HTTPException(status_code=409, detail="This exact PowerPoint is already uploaded for this subject.")

        subj_dir = os.path.join(UPLOAD_DIR, f"subject_{subject_id}")
        os.makedirs(subj_dir, exist_ok=True)
        safe_filename = os.path.basename((file.filename or "study-material").replace("\\", "/")) or "study-material"
        file_location = os.path.join(subj_dir, f"{doc_id}_{safe_filename}")
        with open(file_location, "wb") as buffer:
            buffer.write(content)

        old_path = os.path.realpath(doc.get("file_path") or "")
        upload_root = os.path.realpath(UPLOAD_DIR)
        try:
            old_is_safe = os.path.commonpath([upload_root, old_path]) == upload_root
        except ValueError:
            old_is_safe = False
        if old_is_safe and old_path != os.path.realpath(file_location) and os.path.isfile(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass

        try:
            extracted_text = document_service.extract_text_from_file(file_location) if ext == ".pptx" else ""
        except Exception:
            extracted_text = ""

        updates.update({
            "filename": safe_filename,
            "file_path": file_location,
            "content_sha256": content_hash,
            "extracted_text": extracted_text,
        })
        if "title" not in updates:
            updates["title"] = doc.get("title") or os.path.splitext(safe_filename)[0]

    if not updates:
        raise HTTPException(status_code=422, detail="No PPT changes were provided.")

    db.subject_documents.update_one({"id": doc_id, "subject_id": subject_id}, {"$set": updates})
    updated = db.subject_documents.find_one({"id": doc_id, "subject_id": subject_id})
    updated["uploaded_by_name"] = updated.get("uploaded_by_name") or current_user.full_name
    return SubjectDocumentResponse.model_validate(serialize_doc(updated))


@router.get("/{subject_id}/documents/{doc_id}/download")
def download_subject_document(
    subject_id: int,
    doc_id: int,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user),
):
    doc = db.subject_documents.find_one({"id": doc_id, "subject_id": subject_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Subject document not found")

    file_path = os.path.realpath(doc.get("file_path", ""))
    upload_root = os.path.realpath(UPLOAD_DIR)
    try:
        is_within_upload_dir = os.path.commonpath([upload_root, file_path]) == upload_root
    except ValueError:
        is_within_upload_dir = False
    if not is_within_upload_dir or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Document file is unavailable")

    filename = doc.get("filename") or os.path.basename(file_path)
    return FileResponse(file_path, filename=filename, media_type=guess_type(filename)[0] or "application/octet-stream")


@router.delete("/{subject_id}/documents/{doc_id}")
def delete_subject_document(
    subject_id: int,
    doc_id: int,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(require_role(["FACULTY", "MODERATOR", "ADMIN"]))
):
    doc = db.subject_documents.find_one({"id": doc_id, "subject_id": subject_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Subject document not found")
    if current_user.role == "FACULTY" and doc.get("uploaded_by_id") is not None and doc.get("uploaded_by_id") != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete documents that you uploaded")

    file_path = os.path.realpath(doc.get("file_path") or "")
    upload_root = os.path.realpath(UPLOAD_DIR)
    try:
        is_within_upload_dir = os.path.commonpath([upload_root, file_path]) == upload_root
    except ValueError:
        is_within_upload_dir = False
    if is_within_upload_dir and os.path.isfile(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass

    db.subject_documents.delete_one({"id": doc_id, "subject_id": subject_id})
    return {"message": "Document deleted successfully"}


# Subject Dashboard API
@router.get("/{subject_id}/dashboard", response_model=Dict[str, Any])
def get_subject_dashboard(subject_id: int, db: Database = Depends(get_db), current_user: MongoUser = Depends(get_current_user)):
    subject = db.subjects.find_one({"id": subject_id})
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    documents_count = db.subject_documents.count_documents({"subject_id": subject_id})
    previous_papers_count = db.previous_papers.count_documents({"subject_id": subject_id})
    question_papers_count = db.question_papers.count_documents({"subject_id": subject_id})

    doc_breakdown = {
        "syllabus": db.subject_documents.count_documents({"subject_id": subject_id, "doc_type": "SYLLABUS"}),
        "co_docs": db.subject_documents.count_documents({"subject_id": subject_id, "doc_type": "CO_DOC"}),
        "ppts": db.subject_documents.count_documents({"subject_id": subject_id, "doc_type": "PPT"}),
        "notes": db.subject_documents.count_documents({"subject_id": subject_id, "doc_type": "NOTES"}),
        "rules": db.subject_documents.count_documents({"subject_id": subject_id, "doc_type": "RULES"}),
    }

    units = list(db.syllabus_units.find({"subject_id": subject_id}).sort("unit_number", ASCENDING))
    unit_list = [
        {
            "unit_number": u.get("unit_number"),
            "title": u.get("title", ""),
            "topic_count": len(u.get("topics", [])) if isinstance(u.get("topics"), list) else db.syllabus_topics.count_documents({"unit_id": u.get("id")})
        }
        for u in units
    ]

    cos = list(db.course_outcomes.find({"subject_id": subject_id}))
    co_list = [{"co_code": c.get("co_code"), "description": c.get("description", "")} for c in cos]

    recent_papers = list(
        db.question_papers.find({"subject_id": subject_id})
        .sort("id", DESCENDING)
        .limit(5)
    )
    recent_list = [
        {
            "id": p.get("id"),
            "title": p.get("title"),
            "exam_type": p.get("exam_type"),
            "status": p.get("status"),
            "overall_score": p.get("overall_score"),
            "uploaded_at": p.get("uploaded_at") or ""
        }
        for p in recent_papers
    ]

    return {
        "subject": {
            "id": subject.get("id"),
            "code": subject.get("code"),
            "name": subject.get("name"),
            "branch": subject.get("branch"),
            "semester": subject.get("semester"),
            "department": subject.get("department")
        },
        "stats": {
            "total_documents": documents_count,
            "previous_papers": previous_papers_count,
            "question_papers": question_papers_count,
            "unit_count": len(units),
            "co_count": len(cos)
        },
        "doc_breakdown": doc_breakdown,
        "units": unit_list,
        "cos": co_list,
        "recent_papers": recent_list
    }


# Course Outcomes
@router.get("/{subject_id}/cos", response_model=List[CourseOutcomeResponse])
def list_cos(subject_id: int, db: Database = Depends(get_db), current_user: MongoUser = Depends(get_current_user)):
    cos = list(db.course_outcomes.find({"subject_id": subject_id}))
    return [CourseOutcomeResponse.model_validate(serialize_doc(c)) for c in cos]


@router.post("/{subject_id}/cos", response_model=CourseOutcomeResponse)
def create_co(
    subject_id: int,
    co_in: CourseOutcomeBase,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(require_role(["FACULTY", "ADMIN", "MODERATOR"]))
):
    code_str = co_in.co_code.strip()
    desc_str = co_in.description.strip()
    existing = db.course_outcomes.find_one({"subject_id": subject_id, "co_code": code_str})
    if existing:
        db.course_outcomes.update_one(
            {"id": existing["id"]},
            {"$set": {"description": desc_str}}
        )
        return CourseOutcomeResponse.model_validate(serialize_doc({**existing, "description": desc_str}))

    co_id = get_next_sequence("course_outcomes")
    co_payload = {
        "id": co_id,
        "subject_id": subject_id,
        "co_code": code_str,
        "description": desc_str
    }
    db.course_outcomes.insert_one(co_payload)
    return CourseOutcomeResponse.model_validate(serialize_doc(co_payload))


@router.post("/{subject_id}/cos/batch", response_model=List[CourseOutcomeResponse])
def create_cos_batch(
    subject_id: int,
    batch_in: CourseOutcomeBatchCreate,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(require_role(["FACULTY", "ADMIN", "MODERATOR"]))
):
    subject = db.subjects.find_one({"id": subject_id})
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    results = []
    for co_in in batch_in.cos:
        code_str = co_in.co_code.strip()
        desc_str = co_in.description.strip()
        if not code_str or not desc_str:
            continue
        existing = db.course_outcomes.find_one({"subject_id": subject_id, "co_code": code_str})
        if existing:
            db.course_outcomes.update_one(
                {"id": existing["id"]},
                {"$set": {"description": desc_str}}
            )
            results.append({**existing, "description": desc_str})
        else:
            co_id = get_next_sequence("course_outcomes")
            co_payload = {
                "id": co_id,
                "subject_id": subject_id,
                "co_code": code_str,
                "description": desc_str
            }
            db.course_outcomes.insert_one(co_payload)
            results.append(co_payload)

    return [CourseOutcomeResponse.model_validate(serialize_doc(c)) for c in results]


@router.delete("/{subject_id}/cos/{co_id}")
def delete_co(
    subject_id: int,
    co_id: int,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(require_role(["FACULTY", "ADMIN", "MODERATOR"]))
):
    res = db.course_outcomes.delete_one({"id": co_id, "subject_id": subject_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Course Outcome not found")
    return {"message": "Course Outcome deleted"}


# Syllabus Units
@router.get("/{subject_id}/syllabus", response_model=List[SyllabusUnitResponse])
def list_syllabus(subject_id: int, db: Database = Depends(get_db), current_user: MongoUser = Depends(get_current_user)):
    units = list(db.syllabus_units.find({"subject_id": subject_id}).sort("unit_number", ASCENDING))
    results = []
    for u in units:
        ser = serialize_doc(u)
        # The topic collection is canonical. Older imported units can contain
        # display-only topic dictionaries that do not satisfy the API schema.
        top_docs = list(db.syllabus_topics.find({"unit_id": u.get("id")}))
        embedded_topics = ser.get("topics") or []
        valid_embedded_topics = [
            topic for topic in embedded_topics
            if isinstance(topic, dict) and topic.get("id") is not None and topic.get("unit_id") is not None
        ]
        ser["topics"] = serialize_docs(top_docs) if top_docs else valid_embedded_topics
        results.append(SyllabusUnitResponse.model_validate(ser))
    return results


@router.post("/{subject_id}/syllabus", response_model=SyllabusUnitResponse)
def create_unit(
    subject_id: int,
    unit_in: SyllabusUnitBase,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(require_role(["FACULTY", "ADMIN", "MODERATOR"]))
):
    existing_units = list(db.syllabus_units.find({"subject_id": subject_id}))
    next_u_num = unit_in.unit_number
    if not next_u_num or next_u_num <= 0:
        next_u_num = max([u.get("unit_number", 0) for u in existing_units] + [0]) + 1

    unit_id = get_next_sequence("syllabus_units")
    unit_payload = {
        "id": unit_id,
        "subject_id": subject_id,
        "unit_number": next_u_num,
        "title": unit_in.title or f"Unit {next_u_num}",
        "description": unit_in.description or "",
        "topics": []
    }
    db.syllabus_units.insert_one(unit_payload)
    return SyllabusUnitResponse.model_validate(serialize_doc(unit_payload))


@router.put("/{subject_id}/syllabus/{unit_id}", response_model=SyllabusUnitResponse)
def update_unit(
    subject_id: int,
    unit_id: int,
    unit_in: SyllabusUnitBase,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(require_role(["FACULTY", "ADMIN", "MODERATOR"]))
):
    unit = db.syllabus_units.find_one({"id": unit_id, "subject_id": subject_id})
    if not unit:
        raise HTTPException(status_code=404, detail="Syllabus unit not found")

    upd = {}
    if unit_in.title is not None:
        upd["title"] = unit_in.title
    if unit_in.description is not None:
        upd["description"] = unit_in.description
    if unit_in.unit_number is not None:
        upd["unit_number"] = unit_in.unit_number

    if upd:
        db.syllabus_units.update_one({"id": unit_id}, {"$set": upd})

    updated = db.syllabus_units.find_one({"id": unit_id})
    return SyllabusUnitResponse.model_validate(serialize_doc(updated))


@router.delete("/{subject_id}/syllabus/{unit_id}")
def delete_unit(
    subject_id: int,
    unit_id: int,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(require_role(["FACULTY", "ADMIN", "MODERATOR"]))
):
    res = db.syllabus_units.delete_one({"id": unit_id, "subject_id": subject_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Syllabus unit not found")
    db.syllabus_topics.delete_many({"unit_id": unit_id})
    unit_documents = list(db.subject_documents.find({"subject_id": subject_id, "unit_id": unit_id}))
    upload_root = os.path.realpath(UPLOAD_DIR)
    for document in unit_documents:
        file_path = os.path.realpath(document.get("file_path") or "")
        try:
            is_within_upload_dir = os.path.commonpath([upload_root, file_path]) == upload_root
        except ValueError:
            is_within_upload_dir = False
        if is_within_upload_dir and os.path.isfile(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
        db.subject_documents.delete_one({"id": document.get("id"), "subject_id": subject_id})
    return {"message": "Syllabus unit removed successfully"}


# Topics
@router.post("/{subject_id}/syllabus/{unit_id}/topics", response_model=SyllabusTopicResponse)
def add_topic(
    subject_id: int,
    unit_id: int,
    topic_in: SyllabusTopicBase,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(require_role(["FACULTY", "ADMIN", "MODERATOR"]))
):
    unit = db.syllabus_units.find_one({"id": unit_id, "subject_id": subject_id})
    if not unit:
        raise HTTPException(status_code=404, detail="Syllabus unit not found")

    top_id = get_next_sequence("syllabus_topics")
    top_payload = {
        "id": top_id,
        "unit_id": unit_id,
        "topic_name": topic_in.topic_name,
        "description": topic_in.description or "",
        "co_id": topic_in.co_id
    }
    db.syllabus_topics.insert_one(top_payload)
    db.syllabus_units.update_one({"id": unit_id}, {"$push": {"topics": top_payload}})
    return SyllabusTopicResponse.model_validate(serialize_doc(top_payload))


@router.delete("/{subject_id}/syllabus/{unit_id}/topics/{topic_id}")
def delete_topic(
    subject_id: int,
    unit_id: int,
    topic_id: int,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(require_role(["FACULTY", "ADMIN", "MODERATOR"]))
):
    res = db.syllabus_topics.delete_one({"id": topic_id, "unit_id": unit_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Syllabus topic not found")
    db.syllabus_units.update_one({"id": unit_id}, {"$pull": {"topics": {"id": topic_id}}})
    return {"message": "Topic deleted successfully"}


