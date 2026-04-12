from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from schemas.auth import LoginIn, RegisterIn, TokenOut, UserOut
from services import auth as auth_svc

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Returns the authenticated user, or None for anonymous requests."""
    if not token:
        return None
    try:
        user_id = auth_svc.decode_token(token)
        return await auth_svc.get_user_by_id(db, user_id)
    except JWTError:
        return None


async def require_user(user: Optional[User] = Depends(get_current_user)) -> User:
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        created_at=user.created_at.isoformat(),
    )


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterIn, db: AsyncSession = Depends(get_db)) -> TokenOut:
    if await auth_svc.get_user_by_email(db, body.email):
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=body.email,
        display_name=body.display_name,
        hashed_password=auth_svc.hash_password(body.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return TokenOut(
        access_token=auth_svc.create_access_token(user.id),
        user=_user_out(user),
    )


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, db: AsyncSession = Depends(get_db)) -> TokenOut:
    user = await auth_svc.get_user_by_email(db, body.email)
    if not user or not auth_svc.verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return TokenOut(
        access_token=auth_svc.create_access_token(user.id),
        user=_user_out(user),
    )


# OAuth2PasswordRequestForm compatibility (for /docs Authorize button)
@router.post("/token", response_model=TokenOut, include_in_schema=False)
async def login_form(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenOut:
    return await login(LoginIn(email=form.username, password=form.password), db)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(require_user)) -> UserOut:
    return _user_out(user)
