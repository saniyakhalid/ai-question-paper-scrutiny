from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database
from app.db.mongo import get_db, serialize_doc, serialize_docs, get_next_sequence
from app.schemas.schemas import UserCreate, UserOut
from app.core.security import get_password_hash
from app.core.dependencies import MongoUser, require_role

router = APIRouter(prefix="/admin/users", tags=["User Management"])

@router.get("", response_model=List[UserOut])
def list_users(
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(require_role(["ADMIN"]))
):
    users = list(db.users.find())
    return serialize_docs(users)

@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    db: Database = Depends(get_db),
    current_user: MongoUser = Depends(require_role(["ADMIN"]))
):
    existing = db.users.find_one({"email": user_in.email})
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    user_id = get_next_sequence("users")
    doc = {
        "id": user_id,
        "email": user_in.email,
        "hashed_password": get_password_hash(user_in.password),
        "full_name": user_in.full_name,
        "role": user_in.role.value if hasattr(user_in.role, "value") else str(user_in.role),
        "department": user_in.department,
        "is_active": True,
        "created_at": datetime.now(timezone.utc)
    }
    db.users.insert_one(doc)
    return serialize_doc(doc)
