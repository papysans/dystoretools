"""巨量引擎/千川开放平台 HTTP 客户端.

约定:
- OAuth 接口: app_id + secret 走 JSON body，无 Access-Token 头。
- 业务接口: 携带 `Access-Token` 头 + advertiser_id 参数。
- 统一返回信封 {"code":0,"message":"OK","data":{...},"request_id":...}; code!=0 抛错。
"""

from __future__ import annotations

from typing import Any

import httpx

from dystore.core.config import get_settings
from dystore.core.logging import get_logger

log = get_logger(__name__)

DEFAULT_TIMEOUT = httpx.Timeout(60.0, connect=10.0)


class OceanEngineError(RuntimeError):
    def __init__(self, code: int, message: str, request_id: str | None = None) -> None:
        super().__init__(f"oceanengine code={code} msg={message} request_id={request_id}")
        self.code = code
        self.message = message
        self.request_id = request_id


def _base() -> str:
    return get_settings().oceanengine_base_url.rstrip("/")


def _unwrap(data: dict) -> Any:
    code = data.get("code", -1)
    if code != 0:
        raise OceanEngineError(code, data.get("message") or "", data.get("request_id"))
    return data.get("data")


async def post_oauth(path: str, payload: dict) -> Any:
    """OAuth 类接口: app_id+secret 在 body 中。path 形如 'oauth2/access_token/'。"""
    url = f"{_base()}/open_api/{path.lstrip('/')}"
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return _unwrap(resp.json())


async def get_api(path: str, *, access_token: str, params: dict | None = None) -> Any:
    """业务 GET 接口: Access-Token 头。path 形如 'v3.0/qianchuan/report/advertiser/get/'。"""
    url = f"{_base()}/open_api/{path.lstrip('/')}"
    headers = {"Access-Token": access_token}
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        resp = await client.get(url, headers=headers, params=params or {})
        resp.raise_for_status()
        return _unwrap(resp.json())
