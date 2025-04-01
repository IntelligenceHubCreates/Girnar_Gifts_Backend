from datetime import datetime
import uuid
from app.models import Base
from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, func, text
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.orm import relationship
from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import UUID

class Users(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True, unique=True)
    email = Column(String, nullable=False, unique=True)
    confirmed = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    hashed_password = Column(String, nullable=False, unique=False)
    role = Column(Integer, nullable=False, unique=False)
    tokens = relationship("UserTokens", back_populates="user")

class UserTokens(Base):
    __tablename__ = "user_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    extra = Column(String, nullable=False, unique=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    user = relationship("Users", back_populates="tokens")

class UserBase(BaseModel):
    email: str
    created_at: datetime

    class Config:
        from_attributes = True
