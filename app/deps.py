from datetime import UTC
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.database import DbDep
from app.models import User
from app.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DbDep,
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    decoded = decode_access_token(token)
    if decoded is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == decoded.user_id).first()
    if user is None:
        raise credentials_exception

    cutoff = user.token_valid_after
    # Postgres round-trips a DateTime(timezone=True) value as tz-aware, but
    # SQLite (used in tests and local dev) always returns it naive - normalize
    # to UTC before comparing so this doesn't raise on the SQLite path.
    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=UTC)
    if decoded.issued_at < cutoff:
        raise credentials_exception

    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
