from fastapi import APIRouter

from app.database import DbDep
from app.models import User
from app.schemas import UserCountOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/count", response_model=UserCountOut)
def get_user_count(db: DbDep) -> UserCountOut:
    count = db.query(User).count()
    return UserCountOut(user_count=count)
