from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database
from app.db.mongo import get_db, serialize_doc, get_next_sequence
from app.schemas.schemas import ExamPatternBase, ExamPatternOut
from app.core.dependencies import MongoUser, get_current_user, require_role

router = APIRouter(prefix="/subjects/{subject_id}/rules", tags=["Exam Rules Configuration"])

@router.get("", response_model=ExamPatternOut)
def get_rules(
    subject_id: int,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user)
):
    subject = db.subjects.find_one({"id": subject_id})
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    pattern = db.examination_patterns.find_one({"subject_id": subject_id})
    if not pattern:
        pat_id = get_next_sequence("examination_patterns")
        pattern = {
            "id": pat_id,
            "subject_id": subject_id,
            "total_marks": subject.get("total_marks", 100),
            "duration_minutes": subject.get("duration_minutes", 180),
            "exam_duration_mins": subject.get("duration_minutes", 180),
            "choice_pattern": "Standard Choice",
            "min_co_coverage_pct": None,
            "min_unit_coverage_pct": None,
            "min_higher_order_bloom_pct": None,
            "internal_choice_required": None,
            "solve_time_limit_pct": None,
            "similarity_threshold": None
        }
        db.examination_patterns.insert_one(pattern)
    return serialize_doc(pattern)

@router.put("", response_model=ExamPatternOut)
def update_rules(
    subject_id: int,
    rules_in: ExamPatternBase,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(require_role(["FACULTY", "ADMIN", "MODERATOR"]))
):
    if not db.subjects.find_one({"id": subject_id}):
        raise HTTPException(status_code=404, detail="Subject not found")
    pattern = db.examination_patterns.find_one({"subject_id": subject_id})
    data = rules_in.model_dump(exclude_unset=True)
    if "min_co_coverage_pct" not in data and "min_co_coverage" in data:
        data["min_co_coverage_pct"] = data["min_co_coverage"]
    if "min_unit_coverage_pct" not in data and "min_unit_coverage" in data:
        data["min_unit_coverage_pct"] = data["min_unit_coverage"]
    if "duration_minutes" not in data and "exam_duration_mins" in data:
        data["duration_minutes"] = data["exam_duration_mins"]
    data.pop("min_co_coverage", None)
    data.pop("min_unit_coverage", None)
    data["exam_duration_mins"] = data.get(
        "duration_minutes", (pattern or {}).get("duration_minutes")
    )
    if not pattern:
        pat_id = get_next_sequence("examination_patterns")
        pattern = {"id": pat_id, "subject_id": subject_id, **data}
        db.examination_patterns.insert_one(pattern)
    else:
        db.examination_patterns.update_one({"subject_id": subject_id}, {"$set": data})
        pattern.update(data)

    return serialize_doc(pattern)
