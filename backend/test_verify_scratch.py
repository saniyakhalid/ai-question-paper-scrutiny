import argparse

from app.db.mongo import get_mongo_db


def inspect_paper(paper_id: int):
    db = get_mongo_db()
    paper = db.question_papers.find_one({"id": paper_id})
    if not paper:
        print(f"Paper {paper_id} not found")
        return
    
    subject_id = paper.get("subject_id")
    selected_subject = db.subjects.find_one({"id": subject_id})
    print(f"--- Testing Paper #{paper_id}: '{paper.get('title')}' ---")
    if selected_subject:
        print(f"Selected Subject: ID {subject_id} | {selected_subject.get('code')} - {selected_subject.get('name')}")
    else:
        print(f"Selected Subject: ID {subject_id} | subject record not found")
    
    questions = list(db.extracted_questions.find({"paper_id": paper_id}))
    raw_text = paper.get("raw_text") or ""
    q_texts = [q.get("question_text", "") for q in questions if q.get("question_text")]
    combined_q_text = " ".join(q_texts)
    
    print(f"Question count: {len(q_texts)} | Questions text length: {len(combined_q_text)} | Raw text length: {len(raw_text)}")
    print(f"Questions preview: {combined_q_text[:150]}...")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect a paper in the configured Mongo database.")
    parser.add_argument("paper_id", type=int)
    inspect_paper(parser.parse_args().paper_id)
