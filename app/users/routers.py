from app.users.services import get_hashed_password, verify_password, handle_google_login
from fastapi import APIRouter, Depends, HTTPException, Response, status, Request
from sqlalchemy.orm import Session
from app import models
from app.db import SessionLocal, get_db
from app.users.models import UserTokens, Users
from app.users.schemas import TokenSchema, UserCreate, requestdetails, GoogleLoginRequest
from app.users.utils import COOKIE_ACCESS_KEY, create_access_token, get_current_user
import httpx
import json

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

    # user.id = ""

    return {
        "user": user,
        "token": access,
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

async def verify_google_token(access_token: str) -> dict:
    """Verify Google access token with Google API"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
    except Exception as e:
        print(f"Error verifying Google token: {e}")
        return None

@router.get('/verify-login')
async def verify_login(request: Request, db: Session = Depends(get_db)):
    """Verify if user is still logged in"""
    try:
        user, error_message = await get_current_user(request, db)
        if not user:
            return {
                "is_logged_in": False,
                "message": error_message or "User not authenticated"
            }
        
        # Check if user is a Google user
        is_google_user = user.get("google_id") is not None
        
        # If Google user, verify Google access token
        google_verified = False
        google_user_info = None
        
        if is_google_user and user.get("google_access_token"):
            google_user_info = await verify_google_token(user.get("google_access_token"))
            google_verified = google_user_info is not None
            
            # If Google token is invalid, we might want to refresh it or log out the user
            if not google_verified:
                return {
                    "is_logged_in": False,
                    "message": "Google access token expired or invalid",
                    "requires_google_refresh": True
                }
        
        return {
            "is_logged_in": True,
            "user": {
                "id": user.get("id"),
                "email": user.get("email", ''),
                "name": user.get("name", '') or '',
                "phone": user.get("phone", '') or '',
                "profile_image": user.get("profile_image", '') or '',
                "role": user.get("role", 5),
                "is_google_user": is_google_user,
                "google_verified": google_verified
            },
            "google_info": google_user_info if is_google_user else None,
            "message": "User is authenticated" + (" and Google access verified" if google_verified else "")
        }
        
    except Exception as e:
        return {
            "is_logged_in": False,
            "message": str(e)
        }

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

@router.post('/logout')
async def logout(response: Response):
    """Clear access token cookie"""
    response.delete_cookie(key=COOKIE_ACCESS_KEY, httponly=True, samesite="strict")
    return {"message": "Successfully logged out"}

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
