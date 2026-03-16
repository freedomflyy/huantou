from __future__ import annotations

import hashlib

import httpx

from app.core.config import settings


class WechatAuthError(Exception):
    pass


def _mock_openid_from_code(code: str) -> str:
    digest = hashlib.sha256(code.encode("utf-8")).hexdigest()
    return f"mock_{digest[:24]}"


def resolve_openid_from_code(code: str) -> str:
    if settings.auth_login_mode == "mock":
        return _mock_openid_from_code(code)

    if settings.auth_login_mode != "wechat":
        raise WechatAuthError(f"Unsupported auth mode: {settings.auth_login_mode}")

    if not settings.wechat_appid or not settings.wechat_app_secret:
        raise WechatAuthError("Missing WECHAT_APPID / WECHAT_APP_SECRET")

    url = f"{settings.wechat_api_base.rstrip('/')}/sns/jscode2session"
    params = {
        "appid": settings.wechat_appid,
        "secret": settings.wechat_app_secret,
        "js_code": code,
        "grant_type": "authorization_code",
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
    except Exception as exc:  # pragma: no cover
        raise WechatAuthError("Failed to call WeChat code2Session API") from exc

    openid = data.get("openid")
    errcode = data.get("errcode")
    if not openid or errcode:
        errmsg = data.get("errmsg", "unknown error")
        raise WechatAuthError(f"WeChat auth failed: {errmsg}")
    return openid

