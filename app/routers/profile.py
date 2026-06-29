from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Profile, User
from app.schemas import ProfileIn, ProfileOut

router = APIRouter(tags=["profile"])


@router.post("/profile", response_model=ProfileOut)
def upsert_profile(
    payload: ProfileIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Profile:
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()

    if profile is None:
        profile = Profile(user_id=current_user.id, **payload.model_dump())
        db.add(profile)
    else:
        for field, value in payload.model_dump().items():
            setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return profile
