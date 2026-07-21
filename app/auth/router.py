from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, status

from app.auth.model import User
from app.auth.schema import Token, UserCreate, UserLogin, UserOut
from app.config import settings
from app.database import DbDep, insert_skip_on_conflict
from app.deps import CurrentUserDep
from app.rate_limit import enforce_rate_limit, get_remote_address
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

# A bcrypt hash of an arbitrary, never-used password. It exists purely as something
# for verify_password() to hash *against* when no matching user was found, so that
# a login attempt for an email that doesn't exist takes the same ~150ms bcrypt-hashing
# time as one for a real email with a wrong password. Without this, `login` below would
# return almost instantly when the email isn't found (verify_password is skipped by the
# `or` short-circuit) but take ~150ms when it is found (verify_password actually runs) -
# an attacker could use that timing difference alone to enumerate which emails are
# registered, even though both cases return the same "Incorrect email or password"
# response. Computed once at import time, not per-request, since bcrypt hashing is the
# expensive part we're trying to control, not avoid.
_DUMMY_HASH = hash_password("not-a-real-password")


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(request: Request, payload: UserCreate, db: DbDep) -> Token:
    enforce_rate_limit(limit_string=settings.register_rate_limit_per_ip, key=get_remote_address(request))

    # INSERT ... ON CONFLICT (email) DO NOTHING in a single atomic statement: a
    # duplicate email inserts nothing and comes back as None, with no read-then-INSERT
    # window where two concurrent registrations both pass a pre-check and one 500s on
    # the collision. email is the users table's only unique constraint, so it's the
    # sole conflict target; any other constraint violation still raises rather than
    # being read as a duplicate email.
    user = insert_skip_on_conflict(
        db,
        User,
        values={
            "name": payload.name,
            "email": payload.email,
            "hashed_password": hash_password(payload.password),
        },
        conflict_columns=["email"],
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    db.commit()

    return Token(access_token=create_access_token(subject=user.id))


@router.post("/login", response_model=Token)
def login(request: Request, payload: UserLogin, db: DbDep) -> Token:
    enforce_rate_limit(limit_string=settings.login_rate_limit_per_ip, key=get_remote_address(request))
    enforce_rate_limit(limit_string=settings.login_rate_limit_per_email, key=payload.email)

    user = db.query(User).filter(User.email == payload.email).first()
    hashed_password = user.hashed_password if user is not None else _DUMMY_HASH
    password_valid = verify_password(plain_password=payload.password, hashed_password=hashed_password)

    if user is None or not password_valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    return Token(access_token=create_access_token(subject=user.id))


@router.get("/me", response_model=UserOut)
def read_current_user(current_user: CurrentUserDep) -> User:
    return current_user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(current_user: CurrentUserDep, db: DbDep) -> None:
    # Moves the user's revocation cutoff to now, invalidating every token issued
    # up to and including the one used for this request. Sessions aren't tracked
    # individually, so this can't target just the one token - logging out always
    # logs out every device at once.
    current_user.token_valid_after = datetime.now(UTC)
    db.commit()
