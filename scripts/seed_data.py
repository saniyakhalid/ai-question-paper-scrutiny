"""Optionally create the first administrator from environment-provided secrets.

This script never creates demo credentials and never updates an existing account.
"""

import os
import sys
from datetime import datetime, timezone

backend_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.security import get_password_hash
from app.db.mongo import get_mongo_db, get_next_sequence, init_mongo_indexes


def seed_initial_admin() -> bool:
    email = (os.getenv("SEED_ADMIN_EMAIL") or "").strip().lower()
    password = os.getenv("SEED_ADMIN_PASSWORD") or ""
    full_name = (os.getenv("SEED_ADMIN_NAME") or "System Administrator").strip()
    department = (os.getenv("SEED_ADMIN_DEPARTMENT") or "Examination Cell").strip()

    if not email or not password:
        print("No initial account created. Set SEED_ADMIN_EMAIL and SEED_ADMIN_PASSWORD for a one-time administrator bootstrap.")
        return False
    if len(password) < 12:
        raise ValueError("SEED_ADMIN_PASSWORD must contain at least 12 characters.")

    db = get_mongo_db()
    init_mongo_indexes()
    if db.users.find_one({"email": email}):
        print("The requested administrator account already exists; it was left unchanged.")
        return False

    db.users.insert_one({
        "id": get_next_sequence("users"),
        "email": email,
        "full_name": full_name,
        "hashed_password": get_password_hash(password),
        "role": "ADMIN",
        "department": department,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    print("Initial administrator account created. No password or secret was printed.")
    return True


if __name__ == "__main__":
    seed_initial_admin()
