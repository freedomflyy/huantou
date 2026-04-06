# 幻头后端

`backend` 是本项目的服务端部分，负责处理用户体系、生成任务、资产管理、积分体系、审核与管理接口。

## 技术栈

- FastAPI
- SQLAlchemy
- PostgreSQL
- Pydantic Settings
- JWT
- 腾讯云 COS / 本地文件存储

## 主要模块

- `app/api/routes`：API 路由
- `app/models`：数据库模型
- `app/schemas`：请求与响应结构
- `app/services`：核心业务逻辑
- `app/core`：配置、日志、限流、运行时安全
- `scripts`：初始化、联调、验证与运维脚本

## 已实现能力

- 微信登录
- JWT `access_token + refresh_token`
- 积分余额、积分流水、签到、兑换
- 任务创建、执行、重试、状态查询
- 作品上传、结果资产、收藏
- 内容审核回调
- 简易管理端接口
- 请求日志、限流、基础监控指标

## 本地启动

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 复制环境变量模板

```bash
cp .env.example .env
```

3. 初始化数据库

```bash
python scripts/init_db.py
```

4. 启动服务

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

5. 健康检查

```bash
curl http://127.0.0.1:8000/api/v1/health
```

## 关键接口

- `POST /api/v1/auth/wechat-login`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/points/balance`
- `GET /api/v1/points/ledgers`
- `POST /api/v1/tasks`
- `GET /api/v1/tasks/{task_id}`
- `POST /api/v1/assets/upload`
- `GET /api/v1/assets`
- `GET /api/v1/assets/favorites`
- `GET /api/v1/admin/overview`

## 配置说明

仓库已移除真实密钥和真实云资源信息。你需要自行提供：

- 数据库连接
- 微信小程序 `AppID` / `AppSecret`
- 图像生成服务密钥
- COS 存储配置
- 审核服务配置

请使用 [.env.example](/d:/desktop/CS/backend/.env.example) 作为模板。

## 说明

- 默认配置偏向本地开发与展示，不代表生产建议值
- 部分演示数据已替换为公开示例或占位内容
- 若要部署成正式环境，建议补充异步队列、对象存储策略、监控告警和安全加固
