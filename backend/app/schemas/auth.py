from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.user import UserInfo


class WechatLoginRequest(BaseModel):
    code: str = Field(min_length=1, max_length=128)
    nickname: str | None = Field(default=None, max_length=64)
    avatar_url: str | None = None


class ReviewLoginRequest(BaseModel):
    username: str | None = Field(default=None, max_length=64)
    password: str | None = Field(default=None, max_length=128)
    nickname: str | None = Field(default=None, max_length=64)
    avatar_url: str | None = None


class WechatLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    is_new_user: bool
    signup_bonus_granted: bool
    daily_bonus_granted: bool
    user: UserInfo


class ProfileUpdateRequest(BaseModel):
    nickname: str | None = Field(default=None, max_length=64)
    avatar_url: str | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=4096)


class RefreshTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=4096)


class LogoutResponse(BaseModel):
    revoked: bool


class LogoutAllResponse(BaseModel):
    revoked_count: int
