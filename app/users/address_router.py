from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db import get_db
from app.users.utils import JWTBearer
from app.users.models import UserAddress
from app.users.schemas import AddressCreate, AddressResponse
from app.users.services import create_address, get_user_addresses, get_address, update_address, delete_address

router = APIRouter(prefix="/api/address", tags=["address"])

@router.post("/addresses/", response_model=AddressResponse)
async def create_user_address(
    address: AddressCreate,
    db: Session = Depends(get_db),
    token: str = Depends(JWTBearer())
):
    """Create a new address for the current user"""
    try:
        return create_address(db, address, token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/addresses/", response_model=List[AddressResponse])
async def get_addresses(
    db: Session = Depends(get_db),
    token: str = Depends(JWTBearer())
):
    """Get all addresses for the current user"""
    try:
        return get_user_addresses(db, token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/addresses/{address_id}", response_model=AddressResponse)
async def get_address_by_id(
    address_id: str,
    db: Session = Depends(get_db),
    token: str = Depends(JWTBearer())
):
    """Get a specific address by ID"""
    try:
        address = get_address(db, address_id, token)
        if not address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Address not found"
            )
        return address
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.put("/addresses/{address_id}", response_model=AddressResponse)
async def update_user_address(
    address_id: str,
    address: AddressCreate,
    db: Session = Depends(get_db),
    token: str = Depends(JWTBearer())
):
    """Update an existing address"""
    try:
        updated_address = update_address(db, address_id, address, token)
        if not updated_address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Address not found"
            )
        return updated_address
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/addresses/{address_id}")
async def delete_user_address(
    address_id: str,
    db: Session = Depends(get_db),
    token: str = Depends(JWTBearer())
):
    """Delete an address"""
    try:
        success = delete_address(db, address_id, token)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Address not found"
            )
        return {"message": "Address deleted successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) 