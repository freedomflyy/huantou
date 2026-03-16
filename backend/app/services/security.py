from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class SecurityConfigError(RuntimeError):
    pass


def validate_runtime_security() -> None:
    if settings.app_env.lower() != "prod":
        return

    secret = settings.jwt_secret_key or ""
    if secret == "change_me_in_production" or len(secret) < 24:
        raise SecurityConfigError("JWT_SECRET_KEY is too weak for production")

    if settings.auth_allow_debug_user_header and not settings.auth_force_disable_debug_user_header_in_prod:
        raise SecurityConfigError(
            "X-User-Id debug header cannot stay enabled in production without force-disable"
        )

    if settings.auth_accept_mock_token and not settings.auth_force_disable_mock_token_in_prod:
        raise SecurityConfigError(
            "Mock token cannot stay enabled in production without force-disable"
        )

    if not settings.admin_api_key:
        logger.warning("ADMIN_API_KEY is empty in production; admin endpoints will be unavailable")

    logger.info("Security runtime checks passed for prod environment")
