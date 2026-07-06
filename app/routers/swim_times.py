from fastapi import APIRouter, Query, status

from app.database import DbDep
from app.deps import CurrentUserDep
from app.models import SwimTime
from app.schemas import SwimTimeIn, SwimTimeOut

router = APIRouter(prefix="/swim-times", tags=["swim-times"])


@router.get("", response_model=list[SwimTimeOut])
def list_swim_times(
    current_user: CurrentUserDep,
    db: DbDep,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[SwimTime]:
    return (
        db.query(SwimTime)
        .filter(SwimTime.user_id == current_user.id)
        .order_by(SwimTime.date.desc(), SwimTime.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.post("", response_model=SwimTimeOut, status_code=status.HTTP_201_CREATED)
def create_swim_time(payload: SwimTimeIn, current_user: CurrentUserDep, db: DbDep) -> SwimTime:
    swim_time = SwimTime(user_id=current_user.id, **payload.model_dump())
    db.add(swim_time)
    db.commit()
    db.refresh(swim_time)
    return swim_time
