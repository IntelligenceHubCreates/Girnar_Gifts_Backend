import os
import random
import string
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Union, Any
from jose import jwt
from app.db import get_db, get_db_manually
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import delete

from app.users.models import Users

ACCESS_TOKEN_EXPIRE_MINUTES = 4320
ALGORITHM = "HS256"
JWT_SECRET_KEY = "ydnmakingasecurekey@jwt#developerqgm"
MY_KEY = "IamGonnaBeUsingThisKey"
COOKIE_ACCESS_KEY = 'user_session'


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_user_by_id(db: Session, user_id: str) -> Users:
    """Get user by ID"""
    return db.query(Users).filter(Users.id == user_id).first()


def create_access_token(subject: Union[str, Any], session: Session, expires_delta: int = None) -> str:
    if expires_delta is not None:
        expires_delta = datetime.utcnow() + expires_delta
    else:
        expires_delta = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expires_delta, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, ALGORITHM)
    return encoded_jwt

def decodeJWT(jwtoken: str, db: Session, return_object: bool = False):
    try:
        # Decode and verify the token
        payload = jwt.decode(jwtoken, JWT_SECRET_KEY, ALGORITHM)
        if(payload):
            user = get_user_by_id(db, payload['sub'])
            if user:
                if return_object:
                    return user

                return {
                    'email': user.email, 
                    'id': user.id, 
                    'role': user.role, 
                    'confirmed': user.confirmed, 
                    'created_at': user.created_at,
                    "name": user.name,
                    "phone": user.phone,
                    "address": user.addresses
                }, None
            return None, None
        return None, None
    except Exception as e:
        print("Error", e)
        return None, e

async def get_current_user(request: Request, db: Session, return_object: bool = False):
    try:
        token = request.cookies.get(COOKIE_ACCESS_KEY)
        if not token:
            return None
        
        payload, error_message = decodeJWT(token, db)
        if not payload:
            return None, error_message
            
        return payload, None
    except Exception as e:
        print(f"Error getting current user: {str(e)}")
        return None, e

class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        credentials = request.cookies
        access_key = credentials.get(COOKIE_ACCESS_KEY, None)

        if not access_key:
            # Check Authorization header
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                access_key = auth_header.split(" ")[1]

        if access_key:
            db = get_db_manually()
            user = None
            try:
                isTokenValid, user = self.verify_jwt(access_key, db)
                if not isTokenValid:
                    raise HTTPException(status_code=403, detail="Invalid token or expired token.")
            finally: 
                db.close()
            return user
        else:
            raise HTTPException(status_code=403, detail="Invalid authorization code.")

    def verify_jwt(self, jwtoken: str, db) -> bool:
        isTokenValid: bool = False
        try:
            payload, e = decodeJWT(jwtoken, db)
        except:
            payload = None
        if payload:
            return True, payload
        
        return isTokenValid, None
