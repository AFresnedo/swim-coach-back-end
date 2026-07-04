from fastapi import APIRouter

from app.database import DbDep
from app.deps import CurrentUserDep
from app.models import Profile
from app.schemas import ProfileIn, ProfileOut

router = APIRouter(tags=["profile"])


@router.put("/profile", response_model=ProfileOut)
def upsert_profile(
    payload: ProfileIn,
    current_user: CurrentUserDep,
    db: DbDep,
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
