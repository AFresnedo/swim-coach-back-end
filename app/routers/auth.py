from fastapi import APIRouter, HTTPException, status

from app.database import DbDep
from app.deps import CurrentUserDep
from app.models import User
from app.schemas import Token, UserCreate, UserLogin, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: DbDep) -> Token:
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()

    return Token(access_token=create_access_token(subject=user.email))


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: DbDep) -> Token:
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    return Token(access_token=create_access_token(subject=user.email))


@router.get("/me", response_model=UserOut)
def read_current_user(current_user: CurrentUserDep) -> User:
    return current_user
