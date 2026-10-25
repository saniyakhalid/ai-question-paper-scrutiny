from typing import List, Union, Any, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pymongo.database import Database
from app.core.config import settings
from app.db.mongo import get_db, serialize_doc

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_PREFIX}/auth/login", auto_error=False)

class MongoUser:
    def __init__(self, data: dict):
        self._data = data or {}
        self.id = data.get("id")
        self.email = data.get("email")
        self.full_name = data.get("full_name", "")
        self.role = data.get("role", "FACULTY")
        self.department = data.get("department", "")
        self.is_active = bool(data.get("is_active", True))
        self.created_at = data.get("created_at")

    def __getitem__(self, item):
        return self._data.get(item)

    def get(self, item, default=None):
        return self._data.get(item, default)

    def to_dict(self):
        return serialize_doc(self._data)

def get_current_user(
    db: Database = Depends(get_db),
    header_token: Optional[str] = Depends(oauth2_scheme)
) -> MongoUser:
    # Accept bearer credentials only from the Authorization header; query strings
    # can leak tokens through browser history, referrers, and access logs.
    token = header_token
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id_sub = payload.get("sub")
        if user_id_sub is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    query = {"$or": [{"email": str(user_id_sub)}]}
    if str(user_id_sub).isdigit():
        query["$or"].append({"id": int(user_id_sub)})

    user_data = db.users.find_one(query)
    if user_data is None:
        raise credentials_exception
    user = MongoUser(user_data)
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user account")
    return user

def require_role(allowed_roles: List[Union[str, Any]]):
    allowed_str_roles = [
        r.value if hasattr(r, "value") else str(r).upper() for r in allowed_roles
    ]
    def role_checker(current_user: MongoUser = Depends(get_current_user)) -> MongoUser:
        user_role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role).upper()
        if user_role not in allowed_str_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires one of roles: {', '.join(allowed_str_roles)}",
            )
        return current_user
    return role_checker
