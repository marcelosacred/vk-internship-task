from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.auth import AuthRequest, TokenResponse
from app.schemas.user import UserCreate, UserResponse
from app.services.auth import (
    authenticate_credentials,
    create_access_token,
    require_jwt_subject,
)
from app.services.user import (
    create_user as create_user_service,
    free_users as free_users_service,
    get_users as get_users_service,
    lock_user as lock_user_service,
)

router = APIRouter()


# [post] /users - создать юзера
# [get] /users - получить всех юзеров
# [post] /users/lock - заблокировать юзера путем установки locktime в текущее время
# [post] /users/free - разблокировать всех юзеров (locktime = null)

@router.post("/auth/token", response_model=TokenResponse)
async def get_access_token(auth_data: AuthRequest):
    if not authenticate_credentials(auth_data.username, auth_data.password):
        raise HTTPException(status_code=401, detail="invalid credentials")

    token = create_access_token(subject=auth_data.username)
    return TokenResponse(access_token=token)


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_jwt_subject),
):
    try:
        user = await create_user_service(db, user_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return user


@router.get("/users", response_model=list[UserResponse])
async def get_users(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_jwt_subject),
):
    return await get_users_service(db)


@router.post("/users/lock", response_model=UserResponse)
async def lock_user(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_jwt_subject),
):
    try:
        user = await lock_user_service(db)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return user


@router.post("/users/free")
async def free_users(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_jwt_subject),
):
    await free_users_service(db)
    return {"detail": "all users unlocked"}
