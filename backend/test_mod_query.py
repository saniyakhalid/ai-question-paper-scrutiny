import re
from app.db.mongo import get_mongo_db

db = get_mongo_db()

test_inputs = [
    'moderator@college.edu',
    'Moderator@college.edu',
    'MODERATOR@COLLEGE.EDU',
    'moderator',
    'Moderator',
    'MODERATOR',
    '  moderator@college.edu  '
]

for test_input in test_inputs:
    clean = test_input.strip()
    query = {
        "$or": [
            {"email": re.compile(f"^{re.escape(clean)}$", re.IGNORECASE)},
            {"email": re.compile(f"^{re.escape(clean)}@college\\.edu$", re.IGNORECASE)},
            {"role": clean.upper()}
        ]
    }
    u = db.users.find_one(query)
    print(f"'{test_input}' => {u['email'] if u else 'NOT FOUND'}")
