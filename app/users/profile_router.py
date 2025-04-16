from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..auth import get_current_user
from .models import Users
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

@router.get("/profile", response_model=ProfileResponse)
async def get_profile(current_user: Users = Depends(get_current_user)):
    """Get the current user's profile"""
    return current_user

@router.put("/profile", response_model=ProfileResponse)
async def update_profile(
    profile: ProfileBase,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update the current user's profile"""
    try:
        current_user.name = profile.name
        current_user.email = profile.email
        current_user.phone = profile.phone
        db.commit()
        db.refresh(current_user)
        return current_user
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) 