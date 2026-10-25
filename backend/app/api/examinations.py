from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.database import Database
from pymongo import DESCENDING
from app.db.mongo import get_db, serialize_doc, serialize_docs, get_next_sequence
from app.schemas.schemas import ExaminationCreate, ExaminationResponse
from app.core.dependencies import MongoUser, get_current_user, require_role

router = APIRouter(prefix="/examinations", tags=["Examinations & Unit Config"])

@router.get("", response_model=List[ExaminationResponse])
def list_examinations(
    subject_id: Optional[int] = Query(None),
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user)
):
    query = {}
    if subject_id:
        query["subject_id"] = subject_id
    exams = list(db.examinations.find(query).sort("created_at", DESCENDING))
    return serialize_docs(exams)

@router.post("", response_model=ExaminationResponse)
def create_examination(
    exam_in: ExaminationCreate,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(require_role(["ADMIN", "MODERATOR"]))
):
    subject = db.subjects.find_one({"id": exam_in.subject_id})
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    exam_data = exam_in.model_dump()
    selected_units = exam_data.get("selected_units", [1, 2])
    
    exam_id = get_next_sequence("examinations")
    doc = {
        "id": exam_id,
        **exam_data,
        "selected_units_json": selected_units,
        "created_at": datetime.now(timezone.utc)
    }
    db.examinations.insert_one(doc)
    return serialize_doc(doc)

@router.get("/{exam_id}", response_model=ExaminationResponse)
def get_examination(
    exam_id: int,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user)
):
    exam = db.examinations.find_one({"id": exam_id})
    if not exam:
        raise HTTPException(status_code=404, detail="Examination configuration not found")
    return serialize_doc(exam)
