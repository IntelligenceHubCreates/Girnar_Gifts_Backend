from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.users.models import Users, UserAddress
from app.users.schemas import UserCreate, UserResponse, AddressCreate, AddressResponse, ProfileUpdate

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_hashed_password(password: str) -> str:
    return password_context.hash(password)

def verify_password(password: str, hashed_pass: str) -> bool:
    return password_context.verify(password, hashed_pass)

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

def create_address(db: Session, address: AddressCreate, token: str) -> UserAddress:
    """Create a new address for user"""
    try:
        # Get user ID from token
        from app.users.utils import decodeJWT
        payload = decodeJWT(token)
        if not payload or 'sub' not in payload:
            raise Exception("Invalid token")
        
        user_id = payload['sub']
        
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
        from app.users.utils import decodeJWT
        payload = decodeJWT(token)
        if not payload or 'sub' not in payload:
            raise Exception("Invalid token")
        
        user_id = payload['sub']
        return db.query(UserAddress).filter(UserAddress.user_id == user_id).all()
    except Exception as e:
        raise e

def get_address(db: Session, address_id: str, token: str) -> UserAddress:
    """Get specific address for user"""
    try:
        from app.users.utils import decodeJWT
        payload = decodeJWT(token)
        if not payload or 'sub' not in payload:
            raise Exception("Invalid token")
        
        user_id = payload['sub']
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
    token: str
) -> UserAddress:
    """Update user address"""
    try:
        from app.users.utils import decodeJWT
        payload = decodeJWT(token)
        if not payload or 'sub' not in payload:
            raise Exception("Invalid token")
        
        user_id = payload['sub']
        db_address = get_address(db, address_id, token)
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

def delete_address(db: Session, address_id: str, token: str) -> bool:
    """Delete user address"""
    try:
        from app.users.utils import decodeJWT
        payload = decodeJWT(token)
        if not payload or 'sub' not in payload:
            raise Exception("Invalid token")
        
        user_id = payload['sub']
        db_address = get_address(db, address_id, token)
        if not db_address:
            return False
        
        db.delete(db_address)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise e