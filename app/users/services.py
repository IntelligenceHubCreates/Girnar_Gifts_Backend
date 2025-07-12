from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from app.users.utils import decodeJWT
from fastapi import HTTPException, status

from app.users.models import Users, UserAddress
from app.users.schemas import UserCreate, UserResponse, AddressCreate, AddressResponse, ProfileUpdate, GoogleLoginRequest

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_hashed_password(password: str) -> str:
    return password_context.hash(password)

def verify_password(password: str, hashed_pass: str) -> bool:
    return password_context.verify(password, hashed_pass)

def handle_google_login(db: Session, google_data: GoogleLoginRequest) -> Users:
    """Handle Google login - create or update user"""
    try:
        # Check if user exists by Google ID
        existing_user = db.query(Users).filter(Users.google_id == google_data.google_id).first()
        
        if existing_user:
            # Update existing user with latest Google data
            existing_user.name = google_data.name
            existing_user.email = google_data.email
            existing_user.profile_image = google_data.image
            existing_user.google_id_token = google_data.google_id_token
            existing_user.google_access_token = google_data.google_access_token
            existing_user.confirmed = True
            db.commit()
            db.refresh(existing_user)
            return existing_user
        
        # Check if user exists by email (for users who registered with email but now using Google)
        existing_user_by_email = db.query(Users).filter(Users.email == google_data.email).first()
        
        if existing_user_by_email:
            # Link Google account to existing email account
            existing_user_by_email.google_id = google_data.google_id
            existing_user_by_email.google_id_token = google_data.google_id_token
            existing_user_by_email.google_access_token = google_data.google_access_token
            existing_user_by_email.profile_image = google_data.image
            existing_user_by_email.confirmed = True
            db.commit()
            db.refresh(existing_user_by_email)
            return existing_user_by_email
        
        # Create new user
        new_user = Users(
            email=google_data.email,
            name=google_data.name,
            google_id=google_data.google_id,
            google_id_token=google_data.google_id_token,
            google_access_token=google_data.google_access_token,
            profile_image=google_data.image,
            confirmed=True,
            role=5,  # Default role for regular users
            hashed_password=None  # Google users don't need password
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process Google login: {str(e)}"
        )

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

def create_address(db: Session, address: AddressCreate, user) -> UserAddress:
    """Create a new address for user"""
    try:
        # Get user ID from token
        if not user or 'id' not in user:
            raise Exception("Invalid token")
        
        user_id = user['id']
        
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

def get_user_addresses(db: Session, token: str) -> List[UserAddress]:
    """Get all addresses for user"""
    try:
        payload, _ = decodeJWT(token, db)
        if not payload:
            raise Exception("Invalid token")
        
        user_id = payload['id']
        return db.query(UserAddress).filter(UserAddress.user_id == user_id).all()
    except Exception as e:
        raise e

def get_address(db: Session, address_id: str, user) -> UserAddress:
    """Get specific address for user"""
    try:
        from app.users.utils import decodeJWT

        if not user or 'id' not in user:
            raise Exception("Invalid token")
        
        user_id = user['id']
        
        return db.query(UserAddress).filter(
            UserAddress.id == address_id,
            UserAddress.user_id == user_id
        ).first()
    except Exception as e:
        raise e

def update_address(
    db: Session,
    address_id: str,
    address: AddressCreate,
    user
) -> UserAddress:
    """Update user address"""
    try:
        from app.users.utils import decodeJWT

        if not user or 'id' not in user:
            raise Exception("Invalid token")
        
        user_id = user['id']
        
        db_address = get_address(db, address_id, user)
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

def delete_address(db: Session, address_id: str, user: str) -> bool:
    """Delete user address"""
    try:
        from app.users.utils import decodeJWT

        if not user or 'id' not in user:
            raise Exception("Invalid token")
        
        user_id = user['id']
        
        db_address = get_address(db, address_id, user)
        if not db_address:
            return False
        
        db.delete(db_address)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise e