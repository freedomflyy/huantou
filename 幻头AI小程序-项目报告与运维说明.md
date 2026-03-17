# 幻头 AI 小程序项目报告与运维说明

## 1. 项目结论

当前项目已经完成可上线的主体能力建设，产品主线聚焦在：

- 上传照片
- 选择风格
- 生成头像
- 结果查看
- 头像装饰
- 作品沉淀与分享

前后端已经打通，AI 生成、COS 存储、素材分发、积分体系、官方精选广场、微信登录都已经接入真实链路。

## 2. 当前已实现功能

### 2.1 登录与用户体系

- 微信登录
- 微信头像与昵称授权写入账户
- 个人资料编辑：支持修改头像与昵称
- JWT 登录态与刷新机制
- 个人中心展示积分、作品数、收藏数

### 2.2 头像生成主流程

- 风格迁移
  - 上传照片
  - 正方形裁剪
  - 选择风格模板
  - 自动带入对应参考图
  - 发起真实异步生成任务

- AI 文生图
  - 输入提示词
  - 选择推荐风格或无风格
  - 查看历史生成结果

- AI 编辑
  - 上传头像
  - 裁剪
  - 参考图可选
  - 快速编辑标签
  - 智能指令修改

### 2.3 头像装饰

- 贴纸展示与分类
- 头像框展示
- 文本装饰
- 拖拽文本
- 上传头像后进入装饰
- 头像导出保存

### 2.4 广场与内容展示

- 首页风格轮播
- 官方精选广场
- 广场页热门/最新切换
- 官方精选 24 张样本图
- 每日稳定随机展示热门内容

### 2.5 作品与资产

- 我的作品
- 收藏
- 作品详情
- 结果页候选图查看
- 收藏/取消收藏

### 2.6 积分体系

- 注册积分
- 每日签到积分
- 激活码兑换积分
- 分享邀请奖励
- 任务扣分与失败退款

## 3. 当前广场机制

当前广场已经不再依赖“当前用户自己的作品”来充门面，而是优先读取官方精选池。

实现方式：

- 后台新增 `showcase` 数据源
- 通过脚本批量生成 24 张官方精选样本
- 首页与广场优先读取 `/api/v1/showcase`
- 热门：按日期稳定随机
- 最新：按发布时间排序
- 若 `showcase` 不可用，才退回旧的 fallback 或个人作品逻辑

相关文件：

- `/mnt/d/desktop/CS/backend/app/api/routes/showcase.py`
- `/mnt/d/desktop/CS/backend/app/services/showcase.py`
- `/mnt/d/desktop/CS/backend/app/data/showcase_gallery.json`
- `/mnt/d/desktop/CS/backend/scripts/generate_showcase_samples.py`

## 4. 当前真实服务接入情况

### 已真实接入

- 微信登录：已接真实 `wechat-login`
- 火山图片生成：已接真实 Volcengine
- COS 存储：已接真实腾讯云 COS
- 公共素材与头像框：已改为 COS 分发
- 广场官方精选：已由后台真实生成并写入 COS

### 当前仍保留的开发/测试能力

- Backend 仍保留 `mock` 相关代码分支和测试接口
- `tasks/{id}/mock-complete`、`mock-fail` 仍存在，但不在主流程使用
- 旧 `mock` 作品已从作品列表中过滤

## 5. 仍需特别注意的“非完全正式化”项

### 5.1 内容审核仍是 mock

当前 `.env` 中：

- `MODERATION_PROVIDER=mock`

这意味着现在文本和图片审核不是真实第三方审核。

上线前建议：

- 接入真实腾讯云或火山审核
- 至少覆盖：
  - 提示词审核
  - 上传图片审核
  - 生成结果审核

这是当前最需要补齐的正式化项。

### 5.2 Debug 头能力仍可用

当前后端认证仍支持开发态 `X-User-Id` 调试头。

这方便本地联调，但正式上线时应关闭或确保生产环境失效。

重点关注：

- `AUTH_ALLOW_DEBUG_USER_HEADER`
- `APP_ENV`
- `AUTH_FORCE_DISABLE_DEBUG_USER_HEADER_IN_PROD`

### 5.3 Quick Edit 页面曾暴露 mock provider

这个前台入口我已经改掉，现在只保留 `volcengine`。

但它本身属于旧工具页，不是当前主流程重点，后续可继续弱化或下线。

## 6. 邀请分享奖励机制

当前实现目标是贴近你的要求：

- 不看有没有人点击
- 只要发起分享链路，就自动申请奖励

现状：

- 前端在进入分享链路时就申请奖励
- 后端仍做防重复
- 当前规则仍是“每天首次分享奖励一次”

如果后续你要改成：

- 每分享一次都加 100

则只需要调整后端 `grant_invite_share_bonus_if_needed` 的去重逻辑。

## 7. 运维注意事项

### 7.1 必须长期稳定的基础服务

- PostgreSQL
- Backend API
- 花生壳/外网穿透域名
- 腾讯云 COS
- 火山引擎图片生成 API

### 7.2 小程序后台需要配置的域名

- `request` 合法域名
- `uploadFile` 合法域名
- `downloadFile` 合法域名

至少应覆盖：

- 后端外网域名
- COS 下载域名

### 7.3 后端启动

本地常用启动方式：

```bash
cd /mnt/d/desktop/CS/backend
env PYTHONPATH=/mnt/d/desktop/CS/backend /home/zbzl/anaconda3/envs/bs/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 7.4 常用资源刷新脚本

素材目录更新后：

```bash
cd /mnt/d/desktop/CS/backend
python scripts/upload_material_catalog.py
python scripts/upload_public_assets.py
```

广场官方精选需要重生成时：

```bash
cd /mnt/d/desktop/CS/backend
python scripts/generate_showcase_samples.py
```

生成完成后建议重启 backend。

### 7.5 关注成本项

- 火山 API 调用费用
- COS 存储与流量费用
- 花生壳稳定性
- 图片保留时长与过期清理

建议定期执行：

- 过期资产清理
- 日志清理
- 数据库备份

## 8. 本次交付后建议的下一步

### 高优先级

- 接入真实内容审核
- 关闭生产调试头
- 真机完整回归测试一次
- 配齐小程序后台域名白名单

### 中优先级

- 给广场精选增加后台人工替换能力
- 给官方精选增加权重/推荐位
- 细化分享奖励规则

### 低优先级

- 下线 legacy quick-edit
- 增加管理后台内容运营入口
- 增加广场人工精选与下架机制

## 9. 最终判断

从“产品完整度”和“主链路可用性”看，这个项目已经完成了第一阶段交付。

真正还需要在上线前重点盯住的，不是前端页面本身，而是这三件事：

- 内容审核从 mock 切到真实服务
- 生产环境关闭调试能力
- 真机回归验证分享、生成、下载、域名配置

只要把这三项补稳，这个项目就可以进入正式上线节奏。
