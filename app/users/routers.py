from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from app import models
from app.db import SessionLocal, get_db
from app.users.models import UserTokens, Users
from app.users.schemas import TokenSchema, UserCreate, requestdetails
from app.users.utils import COOKIE_ACCESS_KEY, create_access_token, get_hashed_password, verify_password

router = APIRouter(prefix= '/api/user')

@router.post("/register")
def register_user(user: UserCreate, response: Response, session: Session = Depends(get_db)):
    existing_user = session.query(Users).filter_by(email=user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    encrypted_password = get_hashed_password(user.password)

    new_user = Users(email=user.email, hashed_password=encrypted_password, confirmed=True, role=5 )

    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    access = create_access_token(new_user.id, session)

    response.set_cookie(key=COOKIE_ACCESS_KEY, value=access, httponly=True, samesite="strict")
    
    return {"message":"user created successfully"}

@router.post('/login')
def login(request: requestdetails, response: Response, db: Session = Depends(get_db)):
    user = db.query(Users).filter(Users.email == request.email).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect email")
    hashed_pass = user.hashed_password
    if not verify_password(request.password, hashed_pass):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )
    
    access = create_access_token(user.id, db)

    response.set_cookie(key=COOKIE_ACCESS_KEY, value=access, httponly=True, samesite="strict")

    print("Test", response)

    return {
        "Message": "Successfully Logged In",
    }
