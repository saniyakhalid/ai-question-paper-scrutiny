import os
import pymongo
from dotenv import load_dotenv

load_dotenv()
client = pymongo.MongoClient(os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017"))
db = client["question_paper_scrutiny"]

print("=== QUESTION PAPERS ===")
for q in db.question_papers.find():
    fp = q.get('file_path') or ''
    exists = os.path.exists(fp)
    print(f"ID={q.get('id')} | Title={q.get('title')} | Exists={exists} | Path={fp} | Status={q.get('status')}")

print("\n=== SUBJECTS ===")
for s in db.subjects.find():
    print(f"ID={s.get('id')} | Code={s.get('code')} | Name={s.get('name')} | Dept={s.get('department')}")

print("\n=== SUBJECT DOCUMENTS (PPTs) ===")
for d in db.subject_documents.find():
    print(f"ID={d.get('id')} | SubjectID={d.get('subject_id')} | Title={d.get('title')} | File={d.get('filename')}")
