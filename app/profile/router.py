from fastapi import APIRouter, HTTPException, status

from app.database import DbDep, upsert_returning
from app.deps import CurrentUserDep
from app.profile.model import Profile
from app.profile.schema import ProfileIn, ProfileOut

router = APIRouter(tags=["profile"])


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
    # PUT is an idempotent upsert: the first call creates the profile, every
    # later call overwrites it.
    #
    # That's one INSERT ... ON CONFLICT (user_id) DO UPDATE statement, not a
    # "look up the row, then insert or update" sequence. Look-up-first has a gap:
    # two concurrent first-time PUTs can both see no existing profile and both
    # try to INSERT, so the second one collides with the first. ON CONFLICT
    # closes that gap - the second INSERT just becomes the UPDATE instead.
    #
    # user_id is the profiles table's only unique constraint, so it's the only
    # column ON CONFLICT needs to watch here.
    fields = payload.model_dump()
    profile = upsert_returning(
        db,
        Profile,
        values={"user_id": current_user.id, **fields},
        conflict_columns=["user_id"],
        update_columns=list(fields),
    )
    db.commit()
    return profile
