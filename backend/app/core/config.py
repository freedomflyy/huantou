from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Huanto API"
    app_env: str = "dev"
    api_v1_prefix: str = "/api/v1"
    public_base_url: str | None = None
    admin_api_key: str | None = None
    log_level: str = "INFO"
    log_json: bool = True
    sentry_dsn: str | None = None
    sentry_traces_sample_rate: float = 0.0
    rate_limit_enabled: bool = True
    rate_limit_global_per_minute: int = 120
    rate_limit_auth_per_minute: int = 30
    rate_limit_task_execute_per_minute: int = 20

    database_url: str = (
        "postgresql+psycopg://huanto_app:HuantoDev%402026@127.0.0.1:5433/huanto"
    )

    image_retention_days: int = 7
    points_signup_bonus: int = 100
    points_daily_bonus: int = 10
    points_redeem_code: str | None = "zbzl"
    points_redeem_points: int = 1000
    points_invite_share_bonus: int = 100
    points_txt2img_cost: int = 20
    points_img2img_cost: int = 18
    points_style_transfer_cost: int = 22

    auth_login_mode: str = "mock"  # mock / wechat
    auth_allow_debug_user_header: bool = True
    auth_accept_mock_token: bool = False
    auth_force_disable_debug_user_header_in_prod: bool = True
    auth_force_disable_mock_token_in_prod: bool = True
    auth_review_login_enabled: bool = True
    auth_review_login_openid: str = "review_tester_account"
    auth_review_login_nickname: str = "审核测试账号"
    auth_review_login_avatar_url: str = (
        "https://huanto-1331012038.cos.ap-beijing.myqcloud.com/materials/public/login-logo.jpg"
    )
    auth_review_login_username: str = "audit"
    auth_review_login_password: str = "phantom2026"
    auth_review_login_min_points_balance: int = 5000
    jwt_secret_key: str = "change_me_in_production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 120
    jwt_refresh_token_expire_days: int = 14
    wechat_api_base: str = "https://api.weixin.qq.com"
    wechat_appid: str | None = None
    wechat_app_secret: str | None = None

    ai_provider_default: str = "volcengine"  # mock / local_comfyui / volcengine
    volcengine_endpoint: str = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
    volcengine_api_key: str | None = None
    volcengine_model: str = "doubao-seedream-4-5-251128"
    volcengine_image_size: str = "2K"
    volcengine_watermark: bool = True
    volcengine_timeout_seconds: int = 120

    tencentcloud_appid: str | None = None
    tencentcloud_region: str = "ap-beijing"
    storage_provider: str = "local"  # local / cos
    cos_secret_id: str | None = None
    cos_secret_key: str | None = None
    cos_bucket: str | None = None
    cos_region: str | None = None
    cos_public_base_url: str | None = None
    cos_sign_url_expire_seconds: int = 7200

    moderation_provider: str = "mock"  # mock / tencent / volcengine
    moderation_api_key: str | None = None
    moderation_tencent_biz_type: str | None = None
    moderation_text_detect_type: int = 9
    moderation_image_detect_type: int = 9
    moderation_block_labels: str = "Porn,Politics,Terrorism,Illegal,Abuse,Ads"
    moderation_callback_token: str | None = None

    task_worker_poll_seconds: int = 3
    task_worker_batch_size: int = 2
    task_worker_embedded_enabled: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
