from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database
from app.db.mongo import get_db, serialize_doc
from datetime import datetime, timezone
from app.schemas.schemas import UserLogin, Token, UserOut, UserCreate
from app.core.security import verify_password, create_access_token, get_password_hash
from app.db.mongo import get_next_sequence
from app.core.dependencies import get_current_user, MongoUser
from app.services.audit_service import AuditService

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=Token)
def login(login_data: UserLogin, db: Database = Depends(get_db)):
    user_doc = db.users.find_one({"email": login_data.email})
    if not user_doc or not verify_password(login_data.password, user_doc.get("hashed_password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user_doc.get("is_active", True):
        raise HTTPException(status_code=400, detail="Inactive user account")
    
    role_str = user_doc.get("role", "FACULTY")
    user_id = user_doc.get("id")
    access_token = create_access_token(subject=user_id, role=role_str)
    
    AuditService.log_action(
        db, action="LOGIN", entity="User", entity_id=user_id,
        user_id=user_id, user_role=role_str, metadata={"email": user_doc.get("email")}
    )

    ser_user = serialize_doc(user_doc)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserOut.model_validate(ser_user)
    }

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Database = Depends(get_db)):
    """Public faculty registration for the examination portal."""
    existing = db.users.find_one({"email": user_in.email})
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    # Public registration is always faculty. Moderator/admin roles must be assigned
    # by an already-authorized administrator through the user-management workflow.
    role = "FACULTY"

    user_id = get_next_sequence("users")
    doc = {
        "id": user_id,
        "email": user_in.email,
        "hashed_password": get_password_hash(user_in.password),
        "full_name": user_in.full_name,
        "role": role,
        "department": user_in.department or "General",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    db.users.insert_one(doc)

    AuditService.log_action(
        db,
        action="REGISTER",
        entity="User",
        entity_id=user_id,
        user_id=user_id,
        user_role=role,
        metadata={"email": user_in.email},
    )
    return UserOut.model_validate(serialize_doc(doc))


@router.get("/me", response_model=UserOut)
def get_me(current_user: MongoUser = Depends(get_current_user)):
    return UserOut.model_validate(current_user.to_dict())
