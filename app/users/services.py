from app.db import get_db
from app.users.models import Users
from sqlalchemy.orm import Session

def get_user_by_id(id):
    print("Entered 3")
    db: Session = next(get_db())
    print("Entered 4", id)
    user = db.query(Users).filter(Users.id == id).first()
    print("Entered 2")
    return user