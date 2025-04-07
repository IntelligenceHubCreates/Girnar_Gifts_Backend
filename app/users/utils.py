import os
import random
import string
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Union, Any
from jose import jwt
from app.users.services import get_user_by_id
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import delete

from app.users.models import UserBase, UserTokens

ACCESS_TOKEN_EXPIRE_MINUTES = 4320
ALGORITHM = "HS256"
JWT_SECRET_KEY = "ydnmakingasecurekey@jwt#developerqgm"
MY_KEY = "IamGonnaBeUsingThisKey"
COOKIE_ACCESS_KEY = 'user_session'


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_hashed_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, hashed_pass: str) -> bool:
    return password_context.verify(password, hashed_pass)

def create_access_token(subject: Union[str, Any], session: Session, expires_delta: int = None) -> str:
    if expires_delta is not None:
        expires_delta = datetime.utcnow() + expires_delta
        
    else:
        expires_delta = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
         
    # letters = string.ascii_uppercase
    # extra = ''.join(random.choice(letters) for _ in range(8))
    # input_max_length = len(JWT_SECRET_KEY)
    # extra_place = random.randint(0, input_max_length)
    # one_more_place = random.randint(0, input_max_length)

    # secret_key = JWT_SECRET_KEY[:extra_place] + extra + JWT_SECRET_KEY[extra_place:]
    # secret_key = secret_key[:one_more_place] + MY_KEY + secret_key[one_more_place:]

    # stmt = delete(UserTokens).where(UserTokens.user_id == str(subject))
    # result = session.execute(stmt)
    # session.commit()

    # new_token = UserTokens(user_id= subject, extra= extra)
    # session.add(new_token)
    # session.commit()
    # session.refresh(new_token)

    # print("TEst", secret_key, extra)
    to_encode = {"exp": expires_delta, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, ALGORITHM)
     
    return encoded_jwt

def decodeJWT(jwtoken: str):
    try:
        # Decode and verify the token
        print("Verification", jwtoken)
        payload = jwt.decode(jwtoken, JWT_SECRET_KEY, ALGORITHM)
        print("PPO", payload)
        if(payload):
            print("Entered", payload)
            user = get_user_by_id(payload['sub'])
            print("TYe", user)
            if user:
                return {'email': user.email, 'id': user.id, 'role': user.role, 'confirmed': user.confirmed, 'created_at': user.created_at}
            return None
        return None
    except Exception as e:
        print("TTTT", e)
        return None


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        credentials = request.cookies
        if credentials:
            print("Came in")
            access_key = credentials.get(COOKIE_ACCESS_KEY, None)
            if not access_key:
                raise HTTPException(status_code=403, detail="Invalid authorization code.")
            isTokenValid, user = self.verify_jwt(access_key)
            print("THat", user)
            if not isTokenValid:
                raise HTTPException(status_code=403, detail="Invalid token or expired token.")
            return user
        else:
            raise HTTPException(status_code=403, detail="Invalid authorization code.")

    def verify_jwt(self, jwtoken: str) -> bool:
        isTokenValid: bool = False

        try:
            payload = decodeJWT(jwtoken)
        except:
            payload = None
        
        if payload:
            return True, payload
        
        return isTokenValid, None
