from fastapi import APIRouter, Request

from app.config import settings
from app.database import DbDep
from app.rate_limit import enforce_rate_limit, get_remote_address
from app.stats.schema import SwimCountOut, UserCountOut
from app.swim_time.model import SwimTime
from app.user.model import User

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/users-count", response_model=UserCountOut)
def get_user_count(request: Request, db: DbDep) -> UserCountOut:
    enforce_rate_limit(limit_string=settings.stats_rate_limit_per_ip, key=get_remote_address(request))
    count = db.query(User).count()
    return UserCountOut(user_count=count)


@router.get("/swims-count", response_model=SwimCountOut)
def get_swim_count(request: Request, db: DbDep) -> SwimCountOut:
    enforce_rate_limit(limit_string=settings.stats_rate_limit_per_ip, key=get_remote_address(request))
    count = db.query(SwimTime).count()
    return SwimCountOut(swim_count=count)
