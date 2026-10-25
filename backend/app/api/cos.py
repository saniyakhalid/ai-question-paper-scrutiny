from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database
from app.db.mongo import get_db, serialize_doc, serialize_docs, get_next_sequence
from app.schemas.schemas import CourseOutcomeCreate, CourseOutcomeOut, CourseOutcomeBatchCreate
from app.core.dependencies import MongoUser, get_current_user, require_role

router = APIRouter(prefix="/subjects/{subject_id}/cos", tags=["Course Outcomes"])

@router.get("", response_model=List[CourseOutcomeOut])
def get_cos(
    subject_id: int,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user)
):
    cos = list(db.course_outcomes.find({"subject_id": subject_id}))
    return serialize_docs(cos)

@router.post("", response_model=CourseOutcomeOut, status_code=status.HTTP_201_CREATED)
def create_co(
    subject_id: int,
    co_in: CourseOutcomeCreate,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(require_role(["FACULTY", "ADMIN", "MODERATOR"]))
):
    subject = db.subjects.find_one({"id": subject_id})
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    code_str = co_in.co_code.strip()
    desc_str = co_in.description.strip()
    existing = db.course_outcomes.find_one({"subject_id": subject_id, "co_code": code_str})
    if existing:
        db.course_outcomes.update_one(
            {"id": existing["id"]},
            {"$set": {"description": desc_str}}
        )
        return serialize_doc({**existing, "description": desc_str})

    co_id = get_next_sequence("course_outcomes")
    doc = {
        "id": co_id,
        "subject_id": subject_id,
        "co_code": code_str,
        "description": desc_str
    }
    db.course_outcomes.insert_one(doc)
    return serialize_doc(doc)

@router.put("/{co_id}", response_model=CourseOutcomeOut)
def update_co(
    subject_id: int,
    co_id: int,
    co_in: CourseOutcomeCreate,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(require_role(["FACULTY", "ADMIN", "MODERATOR"]))
):
    subject = db.subjects.find_one({"id": subject_id})
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    existing = db.course_outcomes.find_one({"id": co_id, "subject_id": subject_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Course Outcome not found")

    code_str = co_in.co_code.strip()
    desc_str = co_in.description.strip()
    db.course_outcomes.update_one(
        {"id": co_id, "subject_id": subject_id},
        {"$set": {"co_code": code_str, "description": desc_str}}
    )
    return serialize_doc({**existing, "co_code": code_str, "description": desc_str})

@router.post("/batch", response_model=List[CourseOutcomeOut])
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

    return serialize_docs(results)

@router.delete("/{co_id}")
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
