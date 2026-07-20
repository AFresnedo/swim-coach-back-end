from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.database import DbDep, is_unique_violation
from app.deps import CurrentUserDep
from app.models import Profile
from app.schemas import ProfileIn, ProfileOut

router = APIRouter(tags=["profile"])


def _apply_profile_fields(profile: Profile, payload: ProfileIn) -> None:
    for field, value in payload.model_dump().items():
        setattr(profile, field, value)


@router.get("/profile", response_model=ProfileOut)
def get_profile(
    current_user: CurrentUserDep,
    db: DbDep,
) -> Profile:
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()

    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    return profile


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
        try:
            db.commit()
        except IntegrityError as exc:
            # Two concurrent PUT /profile calls for a brand-new user can both see
            # profile is None before either commits (TOCTOU race), so the second
            # INSERT collides with the first on the profiles.user_id unique index.
            # Only fall back to an update when that's genuinely what failed - PUT is
            # meant to be an idempotent upsert, so "someone else just created it a
            # moment ago" should still succeed by updating the row that now exists,
            # while an unrelated constraint violation must propagate as-is.
            db.rollback()
            if not is_unique_violation(exc, column="user_id"):
                raise
            profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
            if profile is None:
                # The constraint violation said another row now exists for this
                # user_id, so it should be findable here - if it isn't, something
                # is genuinely wrong (e.g. it was deleted in the same instant).
                # Don't silently proceed with no profile; surface the original error.
                raise
            _apply_profile_fields(profile, payload)
            db.commit()
    else:
        _apply_profile_fields(profile, payload)
        db.commit()

    db.refresh(profile)
    return profile
