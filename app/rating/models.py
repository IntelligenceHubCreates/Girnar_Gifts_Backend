from datetime import datetime
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
import uuid
from sqlalchemy.dialects.postgresql import UUID
from app.models import Base

class Rating(Base):
    __tablename__ = "ratings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    review = Column(String(300))
    user = relationship("User", back_populates="ratings")
    product = relationship("Product", back_populates="ratings")
