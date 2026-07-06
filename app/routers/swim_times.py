import base64
from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import and_, or_

from app.database import DbDep
from app.deps import CurrentUserDep
from app.models import SwimTime
from app.schemas import SwimTimeIn, SwimTimeOut, SwimTimePage

router = APIRouter(prefix="/swim-times", tags=["swim-times"])


def _encode_cursor(last_date: date, last_id: int) -> str:
    return base64.urlsafe_b64encode(f"{last_date.isoformat()}|{last_id}".encode()).decode()


def _decode_cursor(cursor: str) -> tuple[date, int]:
    try:
        raw_date, raw_id = base64.urlsafe_b64decode(cursor.encode()).decode().split("|")
        return date.fromisoformat(raw_date), int(raw_id)
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid cursor") from exc


@router.get("", response_model=SwimTimePage)
def list_swim_times(
    current_user: CurrentUserDep,
    db: DbDep,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(default=None),
    stroke: Literal["freestyle", "backstroke", "breaststroke", "butterfly", "individual_medley"] | None = None,
    course: Literal["scy", "scm", "lcm"] | None = None,
    length: int | None = Query(default=None, gt=0),
    is_official: bool | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> SwimTimePage:
    """Cursor and filter params must be resent unchanged on every page request -
    the cursor only encodes position, not the active filters."""
    query = db.query(SwimTime).filter(SwimTime.user_id == current_user.id)

    if stroke is not None:
        query = query.filter(SwimTime.stroke == stroke)
    if course is not None:
        query = query.filter(SwimTime.course == course)
    if length is not None:
        query = query.filter(SwimTime.length == length)
    if is_official is not None:
        query = query.filter(SwimTime.is_official == is_official)
    if date_from is not None:
        query = query.filter(SwimTime.date >= date_from)
    if date_to is not None:
        query = query.filter(SwimTime.date <= date_to)

    if cursor is not None:
        cursor_date, cursor_id = _decode_cursor(cursor)
        query = query.filter(
            or_(
                SwimTime.date < cursor_date,
                and_(SwimTime.date == cursor_date, SwimTime.id < cursor_id),
            )
        )

    rows = query.order_by(SwimTime.date.desc(), SwimTime.id.desc()).limit(limit + 1).all()

    has_more = len(rows) > limit
    items = rows[:limit]
    next_cursor = _encode_cursor(items[-1].date, items[-1].id) if has_more and items else None

    return SwimTimePage(items=items, next_cursor=next_cursor)


@router.post("", response_model=SwimTimeOut, status_code=status.HTTP_201_CREATED)
def create_swim_time(payload: SwimTimeIn, current_user: CurrentUserDep, db: DbDep) -> SwimTime:
    swim_time = SwimTime(user_id=current_user.id, **payload.model_dump())
    db.add(swim_time)
    db.commit()
    db.refresh(swim_time)
    return swim_time
