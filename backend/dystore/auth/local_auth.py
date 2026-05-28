from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dystore.db.models import LocalSession, LocalUser

SESSION_DAYS = 7
ADMIN_PERMISSIONS = ["*"]
OPERATOR_PERMISSIONS = [
    "dashboard:view",
    "orders:view",
    "goods:view",
    "stock:view",
    "comments:view",
    "aftersale:view",
    "member:view",
    "compass:view",
    "content:manage",
    "chat:use",
    "agents:manage",
    "tasks:manage",
    "alerts:view",
    "settings:view",
]
VIEWER_PERMISSIONS = [
    "dashboard:view",
    "orders:view",
    "goods:view",
    "stock:view",
    "comments:view",
    "aftersale:view",
    "member:view",
    "compass:view",
    "alerts:view",
]
ROLE_PERMISSIONS = {
    "admin": ADMIN_PERMISSIONS,
    "operator": OPERATOR_PERMISSIONS,
    "viewer": VIEWER_PERMISSIONS,
}


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"pbkdf2_sha256$120000${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt, digest = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iterations)).hex()
        return hmac.compare_digest(candidate, digest)
    except Exception:
        return False


def permissions_for_role(role: str) -> list[str]:
    return list(ROLE_PERMISSIONS.get(role, OPERATOR_PERMISSIONS))


def serialize_permissions(value: list[str] | None, role: str) -> str:
    items = value if value is not None else permissions_for_role(role)
    return "\n".join(sorted({item.strip() for item in items if item.strip()}))


def parse_permissions(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.splitlines() if item.strip()]


def user_to_dict(row: LocalUser) -> dict[str, Any]:
    return {
        "id": row.id,
        "username": row.username,
        "display_name": row.display_name,
        "role": row.role,
        "permissions": parse_permissions(row.permissions),
        "enabled": row.enabled,
        "last_login_at": row.last_login_at.isoformat() if row.last_login_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


async def has_users(session: AsyncSession) -> bool:
    count = await session.scalar(select(func.count()).select_from(LocalUser))
    return bool(count)


async def register_user(
    session: AsyncSession,
    *,
    username: str,
    password: str,
    display_name: str | None = None,
) -> LocalUser:
    exists = await session.scalar(select(LocalUser).where(LocalUser.username == username))
    if exists is not None:
        raise ValueError("username already exists")
    first = not await has_users(session)
    role = "admin" if first else "operator"
    row = LocalUser(
        username=username,
        password_hash=hash_password(password),
        display_name=display_name or username,
        role=role,
        permissions=serialize_permissions(None, role),
        enabled=True,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def authenticate(session: AsyncSession, *, username: str, password: str) -> LocalUser | None:
    row = await session.scalar(select(LocalUser).where(LocalUser.username == username))
    if row is None or not row.enabled or not verify_password(password, row.password_hash):
        return None
    row.last_login_at = datetime.utcnow()
    await session.commit()
    await session.refresh(row)
    return row


async def create_session(session: AsyncSession, user_id: int) -> LocalSession:
    token = secrets.token_urlsafe(48)
    row = LocalSession(user_id=user_id, token=token, expires_at=datetime.utcnow() + timedelta(days=SESSION_DAYS))
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def get_user_by_token(session: AsyncSession, token: str | None) -> LocalUser | None:
    if not token:
        return None
    await session.execute(delete(LocalSession).where(LocalSession.expires_at < datetime.utcnow()))
    row = await session.scalar(select(LocalSession).where(LocalSession.token == token, LocalSession.expires_at >= datetime.utcnow()))
    if row is None:
        await session.commit()
        return None
    user = await session.get(LocalUser, row.user_id)
    await session.commit()
    if user is None or not user.enabled:
        return None
    return user


async def logout(session: AsyncSession, token: str | None) -> None:
    if token:
        await session.execute(delete(LocalSession).where(LocalSession.token == token))
        await session.commit()


async def list_users(session: AsyncSession) -> list[LocalUser]:
    rows = (await session.execute(select(LocalUser).order_by(LocalUser.id))).scalars().all()
    return list(rows)


async def update_user(session: AsyncSession, user_id: int, values: dict[str, Any]) -> LocalUser | None:
    row = await session.get(LocalUser, user_id)
    if row is None:
        return None
    for key in ("display_name", "role", "enabled"):
        if key in values:
            setattr(row, key, values[key])
    if "permissions" in values:
        row.permissions = serialize_permissions(values["permissions"], row.role)
    elif "role" in values:
        row.permissions = serialize_permissions(None, row.role)
    if values.get("password"):
        row.password_hash = hash_password(values["password"])
    await session.commit()
    await session.refresh(row)
    return row


async def delete_user(session: AsyncSession, user_id: int) -> bool:
    row = await session.get(LocalUser, user_id)
    if row is None:
        return False
    await session.execute(delete(LocalSession).where(LocalSession.user_id == user_id))
    await session.delete(row)
    await session.commit()
    return True


def has_permission(user: LocalUser, permission: str) -> bool:
    permissions = parse_permissions(user.permissions)
    return "*" in permissions or permission in permissions
