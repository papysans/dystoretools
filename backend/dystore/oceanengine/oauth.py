"""千川 OAuth: auth_code 换 token、刷新、广告主拉取、加密持久化.

token 复用项目既有 AES-GCM（CHAT_MASTER_ENCRYPTION_KEY）加密存储，明文绝不落库。
access_token 有效期 24h、refresh_token 30 天 —— get_valid_access_token 在到期前自动刷新。
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select

from dystore.core.config import get_settings
from dystore.core.logging import get_logger
from dystore.db.models import QianchuanAdvertiser, QianchuanToken
from dystore.db.session import SessionLocal
from dystore.llm.registry.crypto import decrypt_secret, encrypt_secret
from dystore.oceanengine.client import get_api, post_oauth

log = get_logger(__name__)

# 提前刷新窗口：到期前 1 小时即刷新，避免边界失效
_REFRESH_SKEW = timedelta(hours=1)


def _creds() -> tuple[str, str]:
    s = get_settings()
    if not s.oceanengine_app_id or not s.oceanengine_app_secret:
        raise RuntimeError("OCEANENGINE_APP_ID / OCEANENGINE_APP_SECRET 未配置 (.env)")
    return s.oceanengine_app_id, s.oceanengine_app_secret


async def exchange_auth_code(auth_code: str) -> QianchuanToken:
    """用回调 auth_code 换取首个 token 并落库（按 uid upsert）。"""
    app_id, secret = _creds()
    data = await post_oauth(
        "oauth2/access_token/",
        {"app_id": app_id, "secret": secret, "grant_type": "auth_code", "auth_code": auth_code},
    )
    return await _persist_token(data)


async def refresh_token(token: QianchuanToken) -> QianchuanToken:
    app_id, secret = _creds()
    data = await post_oauth(
        "oauth2/refresh_token/",
        {
            "app_id": app_id,
            "secret": secret,
            "grant_type": "refresh_token",
            "refresh_token": decrypt_secret(token.refresh_token_enc),
        },
    )
    return await _persist_token(data)


async def _persist_token(data: dict) -> QianchuanToken:
    now = datetime.utcnow()
    uid = str(data.get("uid") or data.get("user_id") or "default")
    access = data["access_token"]
    refresh = data["refresh_token"]
    access_exp = now + timedelta(seconds=int(data.get("expires_in", 86400)))
    refresh_exp = now + timedelta(seconds=int(data.get("refresh_token_expires_in", 2592000)))
    async with SessionLocal() as s:
        row = (await s.execute(select(QianchuanToken).where(QianchuanToken.uid == uid))).scalar_one_or_none()
        if row is None:
            row = QianchuanToken(uid=uid)
            s.add(row)
        row.access_token_enc = encrypt_secret(access)
        row.refresh_token_enc = encrypt_secret(refresh)
        row.access_expires_at = access_exp
        row.refresh_expires_at = refresh_exp
        row.scope_json = data.get("scope")
        row.updated_at = now
        await s.commit()
        await s.refresh(row)
    log.info("qianchuan.token_persisted", uid=uid, access_expires_at=access_exp.isoformat())
    return row


async def get_valid_access_token(uid: str | None = None) -> str:
    """返回有效 access_token；临近过期自动刷新。uid 省略时取首个 token。"""
    async with SessionLocal() as s:
        q = select(QianchuanToken)
        if uid:
            q = q.where(QianchuanToken.uid == uid)
        token = (await s.execute(q.order_by(QianchuanToken.id))).scalars().first()
    if token is None:
        raise RuntimeError("千川尚未授权：请先在前端完成 OAuth 授权")
    if datetime.utcnow() + _REFRESH_SKEW >= token.access_expires_at:
        token = await refresh_token(token)
    return decrypt_secret(token.access_token_enc)


async def fetch_advertisers(token: QianchuanToken) -> list[dict]:
    """拉取该授权下的千川广告账户并 upsert 到 qianchuan_advertiser。"""
    app_id, secret = _creds()
    access = decrypt_secret(token.access_token_enc)
    data = await get_api(
        "oauth2/advertiser/get/",
        access_token=access,
        params={"access_token": access, "app_id": app_id, "secret": secret},
    )
    items = (data or {}).get("list") or []
    async with SessionLocal() as s:
        for it in items:
            adv_id = str(it.get("advertiser_id"))
            row = (
                await s.execute(
                    select(QianchuanAdvertiser).where(QianchuanAdvertiser.advertiser_id == adv_id)
                )
            ).scalar_one_or_none()
            if row is None:
                row = QianchuanAdvertiser(advertiser_id=adv_id, token_id=token.id)
                s.add(row)
            row.advertiser_name = it.get("advertiser_name")
            row.token_id = token.id
            row.raw_json = it
        await s.commit()
    log.info("qianchuan.advertisers_synced", count=len(items))
    return items
