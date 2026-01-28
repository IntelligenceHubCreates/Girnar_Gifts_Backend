from app.rating.models import Rating
from fastapi import APIRouter

router = APIRouter(prefix='/api/rating', tags=["Ratings"])
