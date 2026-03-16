# Huanto Backend (MVP)

## 1. Install dependencies

```bash
conda activate bs
cd /home/zbzl/cs/backend
pip install -r requirements.txt
```

## 2. Configure env

```bash
cp .env.example .env
```

If your DB password contains special characters (for example `@`), keep it URL-encoded in `DATABASE_URL`.

Login mode switch:
- `AUTH_LOGIN_MODE=mock`: local mock openid (default)
- `AUTH_LOGIN_MODE=wechat`: call WeChat `code2Session` (requires `WECHAT_APPID` + `WECHAT_APP_SECRET`)

Token mode:
- return JWT `access_token + refresh_token`
- `AUTH_ACCEPT_MOCK_TOKEN=true`: allow legacy `mock-{user_id}` token compatibility
- `AUTH_ALLOW_DEBUG_USER_HEADER=true`: allow `X-User-Id` debug shortcut
- `AUTH_FORCE_DISABLE_DEBUG_USER_HEADER_IN_PROD=true`: disable debug header when `APP_ENV=prod`
- `AUTH_FORCE_DISABLE_MOCK_TOKEN_IN_PROD=true`: disable mock token when `APP_ENV=prod`

## 3. Initialize database

```bash
python scripts/init_db.py
```

## 4. Start API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

Cloud readiness check:

```bash
python scripts/verify_cloud_services.py
```

Volcengine end-to-end test (3 cases: txt2img/img2img/style_transfer):

```bash
python scripts/test_volcengine_cases.py
```

Quick edit + favorite demo:

```bash
python scripts/demo_quick_edit_and_favorite.py
```

Async queue demo:

```bash
python scripts/demo_async_queue.py
```

Run task worker once:

```bash
python scripts/task_worker.py --once
```

Run task worker loop:

```bash
python scripts/task_worker.py
```

Admin API demo:

```bash
python scripts/demo_admin_apis.py
```

Full feature demo (login/points/tasks/assets/favorites/admin/moderation callback):

```bash
# If .env has empty ADMIN_API_KEY, inject one for this run.
ADMIN_API_KEY=demo-admin-key python scripts/demo_full_flow.py --ai-provider auto
```

Options:
- `--ai-provider auto|mock|volcengine` (default `auto`)
- `--wechat-code <real_code>` when `AUTH_LOGIN_MODE=wechat`
- `--use-uploaded-input` to use uploaded COS URL as input image for generation/edit

Expired assets cleanup:

```bash
python scripts/cleanup_expired_assets.py
```

Expired refresh tokens cleanup:

```bash
python scripts/cleanup_refresh_tokens.py
```

## 5. Download local AI models (optional)

If you want to run local SDXL/ControlNet/IP-Adapter instead of cloud providers, use:

```bash
# plan only (no download)
python scripts/download_models.py --group recommended --dry-run

# download recommended stack to backend/models
python scripts/download_models.py --group recommended
```

Model directory convention is documented in:

- `models/README.md`

## 6. Core APIs (MVP)

- `POST /api/v1/auth/wechat-login`  
  登录，返回 `access_token + refresh_token`（JWT），并处理新用户赠送积分、每日登录积分。
- `POST /api/v1/auth/refresh`  
  使用 `refresh_token` 刷新登录态。
- `POST /api/v1/auth/logout`  
  使用 `refresh_token` 撤销当前会话。
- `POST /api/v1/auth/logout-all`  
  撤销当前用户全部 refresh 会话（需 access token）。
- `GET /api/v1/points/balance`  
  查询当前积分与积分规则。
- `GET /api/v1/points/ledgers`  
  查询积分流水。
- `POST /api/v1/tasks`  
  创建任务并按任务类型扣分，默认进入 `queued`。
- `GET /api/v1/tasks` / `GET /api/v1/tasks/{task_id}`  
  查询任务列表与详情。
- `POST /api/v1/tasks/{task_id}/retry`  
  重试失败任务。
- `POST /api/v1/tasks/{task_id}/execute`  
  执行任务：
  - `quick_edit`：本地基础编辑（裁剪/旋转/亮度/饱和度/对比度等）并写入 `assets`
  - 其他类型：`mock` 或 `volcengine`，`volcengine` 结果会下载后再落地到本地/COS
  - 已接入审核拦截（按 `MODERATION_PROVIDER` 配置）
  - 也可由 `scripts/task_worker.py` 异步消费 `queued` 任务
- `POST /api/v1/tasks/{task_id}/mock-complete`  
  mock 标记任务成功，并写入一条作品记录（7 天过期）。
- `POST /api/v1/tasks/{task_id}/mock-fail`  
  mock 标记任务失败，可按参数触发积分返还。
- `GET /api/v1/assets`  
  我的作品列表。
- `POST /api/v1/assets/upload`  
  上传图片到本地/COS（用于后续图生图、风格迁移、编辑），并进行审核拦截。
- `GET /api/v1/assets/favorites`  
  收藏列表。
- `POST /api/v1/assets/{asset_id}/favorite`  
  收藏作品。
- `DELETE /api/v1/assets/{asset_id}/favorite`  
  取消收藏。
- `GET /api/v1/assets/local/{object_key}`  
  读取本地存储图片（需登录且属于当前用户）。
- `GET /api/v1/admin/console`  
  简易管理控制台页面（浏览器访问），页面内调用 admin API 需填写 `ADMIN_API_KEY`。
- `GET /api/v1/admin/overview`  
  管理总览统计。
- `GET /api/v1/admin/users`  
  用户列表。
- `POST /api/v1/admin/users/{user_id}/status`  
  启用/禁用用户。
- `POST /api/v1/admin/users/{user_id}/points-adjust`  
  管理员调整用户积分。
- `GET /api/v1/admin/tasks`  
  任务列表（支持按状态筛选）。
- `POST /api/v1/admin/tasks/{task_id}/retry`  
  管理员重试任务。
- `POST /api/v1/admin/assets/{asset_id}/take-down`  
  管理员下架作品。
- `GET /api/v1/admin/assets`  
  管理员查看作品列表（可按用户过滤）。
- `GET /api/v1/admin/moderation-audits`  
  审核审计记录列表（支持 `blocked=true/false` 过滤）。
- `POST /api/v1/moderation/tencent/callback`  
  腾讯 COS/CI 审核回调接收入口（可配置 `MODERATION_CALLBACK_TOKEN`）。
- `GET /api/v1/health/metrics`  
  观测指标（需 `X-Admin-Key`），包含请求统计与限流统计。

Use one of these auth headers after login:
- `Authorization: Bearer <access_token>` (recommended)
- `X-User-Id: {user_id}` (debug only, when `AUTH_ALLOW_DEBUG_USER_HEADER=true`)

Admin API header:
- `X-Admin-Key: {ADMIN_API_KEY}`

推荐补充环境变量：
- `ADMIN_API_KEY`：启用管理 API
- `PUBLIC_BASE_URL`：本地文件 URL 拼接基地址（可填内网穿透地址）
- `COS_PUBLIC_BASE_URL`：自定义 COS 访问域名（可选）
- `MODERATION_PROVIDER`：`mock` / `tencent`
- `MODERATION_CALLBACK_TOKEN`：审核回调令牌（建议配置）
- `LOG_LEVEL`：日志级别（默认 `INFO`）
- `LOG_JSON`：是否 JSON 结构化日志（默认 `true`）
- `SENTRY_DSN`：Sentry 错误追踪 DSN（留空则关闭）
- `SENTRY_TRACES_SAMPLE_RATE`：Sentry 性能采样率（0~1）
- `RATE_LIMIT_ENABLED`：是否开启 API 限流
- `RATE_LIMIT_GLOBAL_PER_MINUTE`：全局每分钟限流阈值（按 `IP + method`）
- `RATE_LIMIT_AUTH_PER_MINUTE`：`/auth/*` 每分钟限流阈值
- `RATE_LIMIT_TASK_EXECUTE_PER_MINUTE`：`/tasks/*/execute` 每分钟限流阈值

说明：
- 所有 HTTP 响应会附带 `X-Request-Id`，便于问题定位。
- 被限流时返回 `429`，并携带 `Retry-After`、`X-RateLimit-Limit`、`X-RateLimit-Remaining`。
