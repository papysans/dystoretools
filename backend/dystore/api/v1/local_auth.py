from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from dystore.auth import local_auth as service
from dystore.db.session import get_session

router = APIRouter(prefix="/api/v1/local-auth", tags=["local-auth"])
COOKIE_NAME = "dystore_session"


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    display_name: str | None = Field(default=None, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=128)
    role: str | None = Field(default=None, pattern="^(admin|operator|viewer)$")
    permissions: list[str] | None = None
    enabled: bool | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(COOKIE_NAME, token, max_age=7 * 24 * 60 * 60, httponly=True, samesite="lax")


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, httponly=True, samesite="lax")


async def current_user(
    dystore_session: str | None = Cookie(default=None),
    session: AsyncSession = Depends(get_session),
):
    user = await service.get_user_by_token(session, dystore_session)
    if user is None:
        raise HTTPException(401, detail="not authenticated")
    return user


async def current_admin(user=Depends(current_user)):
    if not service.has_permission(user, "*"):
        raise HTTPException(403, detail="admin permission required")
    return user


@router.get("/bootstrap")
async def bootstrap(session: AsyncSession = Depends(get_session)) -> dict[str, bool]:
    return {"has_users": await service.has_users(session)}


@router.post("/register")
async def register(req: RegisterRequest, response: Response, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    try:
        user = await service.register_user(session, username=req.username, password=req.password, display_name=req.display_name)
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc))
    local_session = await service.create_session(session, user.id)
    set_session_cookie(response, local_session.token)
    return {"user": service.user_to_dict(user)}


@router.post("/login")
async def login(req: LoginRequest, response: Response, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    user = await service.authenticate(session, username=req.username, password=req.password)
    if user is None:
        raise HTTPException(401, detail="invalid username or password")
    local_session = await service.create_session(session, user.id)
    set_session_cookie(response, local_session.token)
    return {"user": service.user_to_dict(user)}


@router.post("/logout")
async def logout(response: Response, dystore_session: str | None = Cookie(default=None), session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    await service.logout(session, dystore_session)
    clear_session_cookie(response)
    return {"status": "ok"}


@router.get("/me")
async def me(user=Depends(current_user)) -> dict[str, Any]:
    return {"user": service.user_to_dict(user)}


@router.get("/users")
async def users(_: Any = Depends(current_admin), session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    rows = await service.list_users(session)
    return {"items": [service.user_to_dict(row) for row in rows]}


@router.patch("/users/{user_id}")
async def update_user(user_id: int, req: UserUpdate, _: Any = Depends(current_admin), session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    row = await service.update_user(session, user_id, req.model_dump(exclude_unset=True))
    if row is None:
        raise HTTPException(404, detail="user not found")
    return service.user_to_dict(row)


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, admin: Any = Depends(current_admin), session: AsyncSession = Depends(get_session)) -> dict[str, int]:
    if admin.id == user_id:
        raise HTTPException(400, detail="cannot delete current user")
    ok = await service.delete_user(session, user_id)
    if not ok:
        raise HTTPException(404, detail="user not found")
    return {"deleted": user_id}
