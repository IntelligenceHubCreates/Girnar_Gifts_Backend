from datetime import datetime
from typing import List
from app.users.utils import get_hashed_password
from sqlalchemy.orm import Session

from app.users.models import Users, UserAddress
from app.users.schemas import UserCreate, UserResponse, AddressCreate, AddressResponse, ProfileUpdate

def create_user(db: Session, user: UserCreate) -> Users:
    """Create a new user"""
    try:
        hashed_password = get_hashed_password(user.password)
        db_user = Users(
            email=user.email,
            name=user.name,
            phone=user.phone,
            password=hashed_password
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        db.rollback()
        raise e

def get_user_by_email(db: Session, email: str) -> Users:
    """Get user by email"""
    return db.query(Users).filter(Users.email == email).first()

def get_user_by_id(db: Session, user_id: str) -> Users:
    """Get user by ID"""
    return db.query(Users).filter(Users.id == user_id).first()

def update_user_profile(db: Session, user: Users, profile: ProfileUpdate) -> Users:
    """Update user profile"""
    try:
        for key, value in profile.model_dump(exclude_unset=True).items():
            setattr(user, key, value)
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        db.rollback()
        raise e

def create_user_address(db: Session, user_id: str, address: AddressCreate) -> UserAddress:
    """Create a new address for user"""
    try:
        if address.is_default:
            # Reset all other addresses to non-default
            db.query(UserAddress).filter(
                UserAddress.user_id == user_id,
                UserAddress.is_default == True
            ).update({"is_default": False})
        
        db_address = UserAddress(
            user_id=user_id,
            **address.model_dump()
        )
        db.add(db_address)
        db.commit()
        db.refresh(db_address)
        return db_address
    except Exception as e:
        db.rollback()
        raise e

def get_user_addresses(db: Session, user_id: str) -> List[UserAddress]:
    """Get all addresses for user"""
    return db.query(UserAddress).filter(UserAddress.user_id == user_id).all()

def get_user_address(db: Session, user_id: str, address_id: str) -> UserAddress:
    """Get specific address for user"""
    return db.query(UserAddress).filter(
        UserAddress.id == address_id,
        UserAddress.user_id == user_id
    ).first()

def update_user_address(
    db: Session,
    user_id: str,
    address_id: str,
    address: AddressCreate
) -> UserAddress:
    """Update user address"""
    try:
        db_address = get_user_address(db, user_id, address_id)
        if not db_address:
            return None
        
        if address.is_default:
            # Reset all other addresses to non-default
            db.query(UserAddress).filter(
                UserAddress.user_id == user_id,
                UserAddress.is_default == True,
                UserAddress.id != address_id
            ).update({"is_default": False})
        
        for key, value in address.model_dump().items():
            setattr(db_address, key, value)
        
        db.commit()
        db.refresh(db_address)
        return db_address
    except Exception as e:
        db.rollback()
        raise e

def delete_user_address(db: Session, user_id: str, address_id: str) -> bool:
    """Delete user address"""
    try:
        db_address = get_user_address(db, user_id, address_id)
        if not db_address:
            return False
        
        db.delete(db_address)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise e