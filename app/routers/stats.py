from fastapi import APIRouter, Request

from app.config import settings
from app.database import DbDep
from app.models import SwimTime, User
from app.rate_limit import enforce_rate_limit, get_remote_address
from app.schemas import SwimCountOut, UserCountOut

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/users-count", response_model=UserCountOut)
def get_user_count(request: Request, db: DbDep) -> UserCountOut:
    enforce_rate_limit(settings.stats_rate_limit_per_ip, get_remote_address(request))
    count = db.query(User).count()
    return UserCountOut(user_count=count)


@router.get("/swims-count", response_model=SwimCountOut)
def get_swim_count(request: Request, db: DbDep) -> SwimCountOut:
    enforce_rate_limit(settings.stats_rate_limit_per_ip, get_remote_address(request))
    count = db.query(SwimTime).count()
    return SwimCountOut(swim_count=count)
