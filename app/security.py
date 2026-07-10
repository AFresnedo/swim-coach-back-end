from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.config import settings

ALGORITHM = "HS256"


@dataclass(frozen=True)
class DecodedToken:
    user_id: int
    issued_at: datetime


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def create_access_token(subject: int) -> str:
    issued_at = datetime.now(UTC)
    expire = issued_at + timedelta(minutes=settings.access_token_expire_minutes)
    # sub is the user's immutable id, not their email: email is mutable (a future
    # email-change feature could let it be reused by a different account), and a
    # still-valid token minted before the change would then resolve to the wrong
    # user if it were keyed by email instead.
    # iat as a float, not a datetime: PyJWT truncates a datetime value for this
    # claim to whole seconds, which let a token minted right after logout, in
    # the same wall-clock second, round down below the revocation cutoff and
    # get wrongly rejected.
    payload = {"sub": str(subject), "exp": expire, "iat": issued_at.timestamp()}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> DecodedToken | None:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "iat"]},
        )
        return DecodedToken(
            user_id=int(payload["sub"]),
            issued_at=datetime.fromtimestamp(payload["iat"], tz=UTC),
        )
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        return None
