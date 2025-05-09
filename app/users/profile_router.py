from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
from app.db import get_db
from app.users.utils import get_current_user, get_user_by_id
from app.users.models import Users
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/api/user", tags=["user"])

class ProfileBase(BaseModel):
    name: str
    email: EmailStr
    phone: str

class ProfileResponse(ProfileBase):
    id: str

    class Config:
        from_attributes = True

@router.get("/profile")
async def get_profile(request: Request, db: Session = Depends(get_db)):
    """Get the current user's profile"""
    current_user, error_message = await get_current_user(request, db)
    if(error_message):
        return {'error': error_message}

    return current_user

@router.put("/profile")
async def update_profile(
    profile: ProfileBase,
    request: Request,
    db: Session = Depends(get_db)
):
    """Update the current user's profile"""
    current_user, error_message = await get_current_user(request, db, True)
    user = get_user_by_id(db, current_user['id'])
    try:
        user.name = profile.name
        user.email = profile.email
        user.phone = profile.phone
        db.commit()
        db.refresh(user)
        return {"message": "Updated Successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) 