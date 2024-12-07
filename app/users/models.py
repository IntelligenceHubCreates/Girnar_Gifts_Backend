from datetime import datetime
from app.models import Base
from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, func
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.orm import relationship
from pydantic import BaseModel, field_serializer

class Users(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, unique=True)
    confirmed = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    hashed_password = Column(String, nullable=False, unique=False)
    role = Column(Integer, nullable=False, unique=False)
    tokens = relationship("UserTokens", back_populates="user")

class UserTokens(Base):
    __tablename__ = "user_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    extra = Column(String, nullable=False, unique=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    user = relationship("Users", back_populates="tokens")

class UserBase(BaseModel):
    email: str
    created_at: datetime

    class Config:
        from_attributes = True
