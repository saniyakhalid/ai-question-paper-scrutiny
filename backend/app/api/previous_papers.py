import os
import json
import shutil
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Query
from pymongo.database import Database
from pymongo import DESCENDING

from app.core.config import settings
from app.db.mongo import get_db, serialize_doc, serialize_docs, get_next_sequence
from app.core.dependencies import MongoUser, get_current_user
from app.services.extraction_service import DocumentExtractionService
from app.services.question_parser import QuestionParserService
from app.services.similarity_service import similarity_service

router = APIRouter(prefix="/previous-papers", tags=["Previous Exam Papers Repository"])

@router.get("")
def list_previous_papers(
    subject_id: Optional[int] = Query(None),
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user)
):
    query = {}
    if subject_id:
        query["subject_id"] = subject_id
    papers = list(db.previous_papers.find(query).sort("uploaded_at", DESCENDING))
    
    result = []
    for p in papers:
        qs = list(db.previous_questions.find({"paper_id": p.get("id")}))
        q_list = [
            {
                "id": q.get("id"),
                "question_number": q.get("question_number"),
                "question_text": q.get("question_text"),
                "marks": q.get("marks")
            }
            for q in qs
        ]
        result.append({
            "id": p.get("id"),
            "subject_id": p.get("subject_id"),
            "academic_year": p.get("academic_year"),
            "exam_type": p.get("exam_type"),
            "title": p.get("title"),
            "file_path": p.get("file_path"),
            "uploaded_at": p.get("uploaded_at").isoformat() if isinstance(p.get("uploaded_at"), datetime) else p.get("uploaded_at"),
            "questions": q_list
        })
    return result

@router.post("/upload", status_code=status.HTTP_201_CREATED)
def upload_previous_paper(
    subject_id: int = Form(...),
    title: Optional[str] = Form(None),
    academic_year: Optional[str] = Form("2024-2025"),
    year: Optional[str] = Form(None),
    exam_type: Optional[str] = Form("End-Semester Examination"),
    selected_units: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user)
):
    subject = db.subjects.find_one({"id": subject_id})
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    eff_year = academic_year or year or "2024-2025"
    eff_title = title or os.path.splitext(file.filename)[0]

    ext = os.path.splitext(file.filename)[1].lower().replace(".", "")
    if ext not in ["pdf", "docx", "txt"]:
        raise HTTPException(status_code=400, detail="Supported file formats: PDF, DOCX, TXT")

    save_dir = os.path.join(settings.UPLOAD_DIR, "previous_papers")
    os.makedirs(save_dir, exist_ok=True)
    saved_path = os.path.join(save_dir, f"prev_{int(os.urandom(4).hex(), 16)}.{ext}")

    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    paper_id = get_next_sequence("previous_papers")
    paper_doc = {
        "id": paper_id,
        "subject_id": subject_id,
        "academic_year": eff_year,
        "exam_type": exam_type,
        "title": eff_title,
        "file_path": saved_path,
        "uploaded_at": datetime.now(timezone.utc)
    }
    db.previous_papers.insert_one(paper_doc)

    try:
        raw_text = DocumentExtractionService.extract_text(saved_path, ext)
        parsed_qs = QuestionParserService.parse_extracted_text(raw_text)

        for q in parsed_qs:
            pq_id = get_next_sequence("previous_questions")
            pq_doc = {
                "id": pq_id,
                "paper_id": paper_id,
                "question_number": q.get("question_number", "Q1"),
                "question_text": q["question_text"],
                "marks": q.get("marks") if q.get("marks") is not None else None
            }
            db.previous_questions.insert_one(pq_doc)

            vec = similarity_service.compute_embedding_vector(q["question_text"])
            emb_id = get_next_sequence("question_embeddings")
            emb_doc = {
                "id": emb_id,
                "previous_question_id": pq_id,
                "vector_json": json.dumps(vec)
            }
            db.question_embeddings.insert_one(emb_doc)

        return {
            "message": "Question paper uploaded and indexed successfully.",
            "paper_id": paper_id,
            "questions_count": len(parsed_qs)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process and index previous question paper: {str(e)}")

@router.delete("/{paper_id}")
def delete_previous_paper(
    paper_id: int,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user)
):
    paper = db.previous_papers.find_one({"id": paper_id})
    if not paper:
        raise HTTPException(status_code=404, detail="Previous question paper not found")

    # Get questions to delete embeddings
    questions = list(db.previous_questions.find({"paper_id": paper_id}))
    for q in questions:
        db.question_embeddings.delete_many({"previous_question_id": q.get("id")})
    db.previous_questions.delete_many({"paper_id": paper_id})

    # Delete physical file
    file_path = paper.get("file_path")
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

    db.previous_papers.delete_one({"id": paper_id})
    return {"message": "Previous question paper and associated indexed questions deleted successfully"}
