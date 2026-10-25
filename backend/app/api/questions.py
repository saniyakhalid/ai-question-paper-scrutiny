from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database
from app.db.mongo import get_db, serialize_doc
from app.schemas.schemas import QuestionOut
from app.core.dependencies import MongoUser, get_current_user

router = APIRouter(prefix="/questions", tags=["Questions"])

@router.get("/{id}", response_model=QuestionOut)
def get_question(
    id: int,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user)
):
    question = db.extracted_questions.find_one({"id": id})
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return serialize_doc(question)
