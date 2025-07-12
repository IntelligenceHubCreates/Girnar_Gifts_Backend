from app.users.services import get_hashed_password, verify_password, handle_google_login
from fastapi import APIRouter, Depends, HTTPException, Response, status, Request
from sqlalchemy.orm import Session
from app import models
from app.db import SessionLocal, get_db
from app.users.models import UserTokens, Users
from app.users.schemas import TokenSchema, UserCreate, requestdetails, GoogleLoginRequest
from app.users.utils import COOKIE_ACCESS_KEY, create_access_token, get_current_user

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

@router.post('/google-login')
def google_login(google_data: GoogleLoginRequest, response: Response, db: Session = Depends(get_db)):
    """Handle Google login"""
    try:
        print("Google Data", google_data)
        # Process Google login
        user = handle_google_login(db, google_data)
        
        # Create access token
        access = create_access_token(user.id, db)
        
        # Set cookie
        response.set_cookie(key=COOKIE_ACCESS_KEY, value=access, httponly=True, samesite="strict")
        
        return {
            "message": "Successfully logged in with Google",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "profile_image": user.profile_image
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get('/profile')
async def get_profile(request: Request, db: Session = Depends(get_db)):
    try:
        user, error_message = await get_current_user(request, db)
        if not user:
            raise Exception(error_message)
        
        return {
            "email": user.get("email", ''),
            "name": user.get("name", '') or '',
            "phone": user.get("phone", '') or '', 
            "address": user.get("address", '') or ''
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

# @router.get('/')
# def get_users(response: Response, db: Session = Depends(get_db)):
#     user = db.query(Users).all()
#     # if user is None:
#     #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect email")
#     # hashed_pass = user.hashed_password
#     # if not verify_password(request.password, hashed_pass):
#     #     raise HTTPException(
#     #         status_code=status.HTTP_400_BAD_REQUEST,
#     #         detail="Incorrect password"
#     #     )
    
#     # access = create_access_token(user.id, db)

#     # response.set_cookie(key=COOKIE_ACCESS_KEY, value=access, httponly=True, samesite="strict")

#     print("Test", response)

#     return {
#         "Message": "Successfully Logged In",
#         "First User": user
#     }
