from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.auth.model import User
from app.database import DbDep
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

    if decoded.issued_at < user.token_valid_after:
        raise credentials_exception

    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
