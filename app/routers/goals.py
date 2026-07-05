from fastapi import APIRouter, HTTPException, status

from app.database import DbDep
from app.deps import CurrentUserDep
from app.models import Goal
from app.schemas import GoalDeactivateReason, GoalIn, GoalOut

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("", response_model=list[GoalOut])
def list_goals(current_user: CurrentUserDep, db: DbDep) -> list[Goal]:
    return (
        db.query(Goal)
        .filter(Goal.user_id == current_user.id, Goal.is_active.is_(True))
        .order_by(Goal.created_at.desc())
        .all()
    )


@router.post("", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
def create_goal(payload: GoalIn, current_user: CurrentUserDep, db: DbDep) -> Goal:
    goal = Goal(user_id=current_user.id, **payload.model_dump())
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def _get_owned_goal(goal_id: int, current_user: CurrentUserDep, db: DbDep) -> Goal:
    goal = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == current_user.id).first()
    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    return goal


@router.patch("/{goal_id}", response_model=GoalOut)
def update_goal(goal_id: int, payload: GoalIn, current_user: CurrentUserDep, db: DbDep) -> Goal:
    goal = _get_owned_goal(goal_id, current_user, db)
    goal.text = payload.text
    db.commit()
    db.refresh(goal)
    return goal


@router.patch("/{goal_id}/deactivate", response_model=GoalOut)
def deactivate_goal(goal_id: int, payload: GoalDeactivateReason, current_user: CurrentUserDep, db: DbDep) -> Goal:
    goal = _get_owned_goal(goal_id, current_user, db)
    goal.is_active = False
    goal.deactivation_reason = payload.reason
    db.commit()
    db.refresh(goal)
    return goal
