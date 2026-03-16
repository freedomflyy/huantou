# Huanto 后端全链路 Demo 报告

时间：`2026-03-13`  
脚本：`backend/scripts/demo_full_flow.py`  
报告原始 JSON：`backend/reports/demo_full_flow_latest.json`

## 执行命令

```bash
ADMIN_API_KEY=demo-admin-key python scripts/demo_full_flow.py --ai-provider auto
```

## 本次环境

- `APP_ENV=dev`
- `AUTH_LOGIN_MODE=wechat`（本次未提供真实 `wechat_code`，自动降级到 `X-User-Id` 调试用户）
- `STORAGE_PROVIDER=cos`
- `MODERATION_PROVIDER=mock`
- AI 生成：`volcengine`

## 结果概览

- 总步骤：`18`
- 通过：`18`
- 失败：`0`

## 已验证链路

- 登录链路（wechat 模式下的降级联调路径）
- 积分查询与流水查询
- 资产上传（COS）
- 四类任务全量执行：
  - `txt2img`
  - `img2img`
  - `style_transfer`
  - `quick_edit`
- 作品列表与收藏增删查
- 管理接口：
  - `overview/users/tasks/assets/moderation-audits`
  - `admin points adjust`
  - `admin asset take-down`
- 审核回调入库
- 观测指标接口 `GET /api/v1/health/metrics`
