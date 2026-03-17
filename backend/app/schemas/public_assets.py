from __future__ import annotations

from pydantic import BaseModel


class PublicAssetsResponse(BaseModel):
    login_logo_url: str
    home_hero_url: str
    share_card_url: str
