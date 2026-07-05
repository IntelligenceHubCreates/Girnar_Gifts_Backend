import os
import random
import string
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Union, Any, Optional, Tuple
from jose import jwt
from app.db import get_db, get_db_manually
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import delete

from app.settings import settings
from app.users.models import Users

ACCESS_TOKEN_EXPIRE_MINUTES = 4320
ALGORITHM = "HS256"
JWT_SECRET_KEY = settings.secret_key
MY_KEY = "IamGonnaBeUsingThisKey"
COOKIE_ACCESS_KEY = 'user_session'


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_user_by_id(db: Session, user_id: str) -> Optional[Users]:
    """Get user by ID."""
    return db.query(Users).filter(Users.id == user_id).first()


def create_access_token(subject: Union[str, Any], session: Session, expires_delta: int = None) -> str:
    if expires_delta is not None:
        expires_delta = datetime.utcnow() + expires_delta
    else:
        expires_delta = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expires_delta, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, ALGORITHM)
    return encoded_jwt


def _extract_token(request: Request) -> Optional[str]:
    """
    Resolve a JWT from either the legacy session cookie OR the
    Authorization: Bearer <token> header (used by the NextAuth flow).
    """
    token = request.cookies.get(COOKIE_ACCESS_KEY)
    if token:
        return token

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1].strip() or None

    return None


def decodeJWT(jwtoken: str, db: Session, return_object: bool = False) -> Tuple[Any, Any]:
    """
    Decode + verify a JWT.

    ALWAYS returns a 2-tuple (payload_or_user, error) so every caller can safely
    do `payload, err = decodeJWT(...)`.

    - return_object=False -> payload is a plain dict (shape used by JWTBearer)
    - return_object=True  -> payload is the Users ORM object
    """
    try:
        payload = jwt.decode(jwtoken, JWT_SECRET_KEY, ALGORITHM)
        if not payload:
            return None, "Invalid token payload"

        user = get_user_by_id(db, payload.get('sub'))
        if not user:
            return None, "User not found"

        if return_object:
            return user, None

        return {
            'email': user.email,
            'id': user.id,
            'role': user.role,
            'confirmed': user.confirmed,
            'created_at': user.created_at,
            "name": user.name,
            "phone": user.phone,
            "address": user.addresses,
        }, None
    except Exception as e:
        print("Error decoding JWT:", e)
        return None, str(e)


async def get_current_user(
    request: Request,
    db: Session,
    return_object: bool = False,
) -> Tuple[Any, Any]:
    """
    Resolve the current user from cookie OR Authorization header.

    ALWAYS returns a 2-tuple (user, error_message). This is critical: callers do
    `current_user, error_message = await get_current_user(...)`, so returning a
    bare `None` (as the original did when no cookie was present) caused a
    `TypeError: cannot unpack non-iterable NoneType` on every NextAuth request.
    """
    try:
        token = _extract_token(request)
        if not token:
            return None, "Not authenticated"

        payload, error_message = decodeJWT(token, db, return_object)
        if not payload:
            return None, error_message or "Invalid or expired token"

        return payload, None
    except Exception as e:
        print(f"Error getting current user: {str(e)}")
        return None, str(e)


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        credentials = request.cookies
        access_key = credentials.get(COOKIE_ACCESS_KEY, None)

        if not access_key:
            # Check Authorization header (NextAuth bearer flow)
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                access_key = auth_header.split(" ", 1)[1].strip()

        if access_key:
            db = get_db_manually()
            user = None
            try:
                isTokenValid, user = self.verify_jwt(access_key, db)
                if not isTokenValid:
                    if self.auto_error:
                        raise HTTPException(status_code=401, detail="Invalid token or expired token.")
                    return None
            finally:
                db.close()
            return user
        else:
            if self.auto_error:
                raise HTTPException(status_code=401, detail="Invalid authorization code.")
            return None

    def verify_jwt(self, jwtoken: str, db) -> Tuple[bool, Any]:
        isTokenValid: bool = False
        try:
            payload, e = decodeJWT(jwtoken, db)
        except Exception:
            payload = None
        if payload:
            return True, payload
        return isTokenValid, None