from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.db import get_db
from app.users.models import UserAddress
from app.users.utils import get_current_user
from pydantic import BaseModel
from typing import List, Optional
import uuid

router = APIRouter(prefix='/api/user/addresses')

class AddressBase(BaseModel):
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str
    is_default: bool = False

    class Config:
        from_attributes = True

class AddressCreate(AddressBase):
    pass

class AddressResponse(AddressBase):
    id: str
    user_id: str
    created_at: str

    class Config:
        from_attributes = True

@router.post("/", response_model=AddressResponse)
async def create_address(
    address: AddressCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        user = await get_current_user(request, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )

        # If this is set as default, unset all other defaults
        if address.is_default:
            db.query(UserAddress).filter(
                UserAddress.user_id == user.id,
                UserAddress.is_default == True
            ).update({"is_default": False})

        new_address = UserAddress(
            id=uuid.uuid4(),
            user_id=user.id,
            **address.dict()
        )
        db.add(new_address)
        db.commit()
        db.refresh(new_address)
        return new_address
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/", response_model=List[AddressResponse])
async def get_addresses(
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        user = await get_current_user(request, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        
        addresses = db.query(UserAddress).filter(UserAddress.user_id == user.id).all()
        return addresses
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{address_id}", response_model=AddressResponse)
async def get_address(
    address_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        user = await get_current_user(request, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        
        address = db.query(UserAddress).filter(
            UserAddress.id == address_id,
            UserAddress.user_id == user.id
        ).first()
        
        if not address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Address not found"
            )
        return address
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put("/{address_id}", response_model=AddressResponse)
async def update_address(
    address_id: str,
    address: AddressCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        user = await get_current_user(request, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )

        # If this is set as default, unset all other defaults
        if address.is_default:
            db.query(UserAddress).filter(
                UserAddress.user_id == user.id,
                UserAddress.is_default == True,
                UserAddress.id != address_id
            ).update({"is_default": False})

        db.query(UserAddress).filter(
            UserAddress.id == address_id,
            UserAddress.user_id == user.id
        ).update(address.dict())
        
        db.commit()
        updated_address = db.query(UserAddress).filter(
            UserAddress.id == address_id,
            UserAddress.user_id == user.id
        ).first()
        
        if not updated_address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Address not found"
            )
        return updated_address
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/{address_id}")
async def delete_address(
    address_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        user = await get_current_user(request, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        
        address = db.query(UserAddress).filter(
            UserAddress.id == address_id,
            UserAddress.user_id == user.id
        ).first()
        
        if not address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Address not found"
            )
        
        db.delete(address)
        db.commit()
        return {"message": "Address deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) 