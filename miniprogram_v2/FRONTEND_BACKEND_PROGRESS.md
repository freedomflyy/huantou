# 幻头小程序前后端对接进度

更新时间：2026-03-16 16:24

## 当前进度

- [x] 欢迎页改成真实登录入口
- [x] 登录态存储、401 刷新、失效回跳登录页
- [x] 我的页面去掉“最近作品”
- [x] 作品集改成“我的作品 / 收藏”两个板块
- [x] 作品集接入真实接口
- [x] 创作记录接入真实接口
- [x] 会员中心接入真实积分与流水
- [x] 文生图创建任务接入真实接口
- [x] 图生图精修创建任务接入真实接口
- [x] 风格迁移创建任务接入真实接口
- [x] 火山组图生成接入 backend
- [x] 小程序创作页接入 1/2/4 张候选图入口
- [x] 生成中页面改为真实异步任务轮询
- [x] 结果页改为读取真实任务与作品
- [x] 任务默认 provider 改为火山
- [x] backend 内嵌异步 worker 已启用
- [x] 积分签到接口与前端展示已接通
- [x] 激活码兑换积分入口已接通
- [x] COS 作品图改为签名 URL 返回
- [x] 旧 mock 作品已从作品列表中过滤
- [ ] 首页灵感流改成真实“公共广场”
- [ ] 贴纸库、局部重绘、蒙版交互
- [ ] 支付/积分充值真实链路
- [ ] 作品下载、删除、再次编辑

## 已接接口

### 鉴权

- `POST /api/v1/auth/wechat-login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`

### 作品与收藏

- `GET /api/v1/assets`
- `GET /api/v1/assets/favorites`
- `POST /api/v1/assets/upload`
- `POST /api/v1/assets/{asset_id}/favorite`
- `DELETE /api/v1/assets/{asset_id}/favorite`

### 任务

- `POST /api/v1/tasks`
- `GET /api/v1/tasks`
- `GET /api/v1/tasks/{task_id}`
- `POST /api/v1/tasks/{task_id}/execute`

组图调用方式：

- 前端传 `params.output_count`
- backend 会自动转成火山的：
- `sequential_image_generation=auto`
- `sequential_image_generation_options.max_images={output_count}`

### 积分

- `GET /api/v1/points/balance`
- `GET /api/v1/points/ledgers`
- `POST /api/v1/points/check-in`
- `POST /api/v1/points/redeem-code`

## 当前已知问题

### 1. 当前配置的穿透域名可用，但命令行代理会干扰 HTTPS 测试

- 前端当前配置地址：`https://828md02534xr.vicp.fun`
- 终端环境里存在这些代理变量：
- `http_proxy=http://127.0.0.1:65533`
- `https_proxy=http://127.0.0.1:65533`
- 直接执行 `curl https://828md02534xr.vicp.fun/api/v1/health` 时，请求会先走本地代理，因此可能出现：
- `HTTP/1.1 200 Connection established`
- 后续 `OpenSSL SSL_connect: SSL_ERROR_SYSCALL`
- 这不代表 backend 挂了，而是代理干扰了 TLS 握手
- 使用直连方式测试后，域名本身正常：
- `curl --noproxy '*' https://828md02534xr.vicp.fun/api/v1/health`
- 返回 `HTTP/1.1 200 OK`
- 结论：穿透域名和 HTTPS 接口本身可用，命令行测试时要绕过本地代理

建议测试方式：

- `curl --noproxy '*' https://828md02534xr.vicp.fun/api/v1/health`
- 或临时清掉 `http_proxy/https_proxy`

### 2. 历史 mock 图和 COS 403 问题已经完成修复

- `mock.huanto.local` 报错来源于旧测试期遗留的 mock 作品
- backend 现在会把 `object_key` 以 `mock/` 开头的旧作品从 `/assets` 和 `/assets/favorites` 里过滤掉
- COS 图片之前返回的是直链，私有桶会出现 `403 Forbidden`
- backend 现在统一返回带签名的临时下载 URL
- 本地在 `2026-03-16 16:24` 已验证：
- 用户 `3` 的旧 COS 作品返回签名链接
- 直接访问签名图返回 `200 image/jpeg`

### 3. 风格迁移接口当前要求参考图必传

- 后端 `style_transfer` 校验要求：
- `input_image_url` 必传
- `reference_image_url` 必传
- 所以前端现在把“参考图”改成必传项
- 如果你后面想做成“点一个内置风格卡片就能转绘”，我们需要准备每个风格对应的参考图素材，或者调整后端校验逻辑

### 4. 小程序生成链路已切换成真实异步队列

- 前端不再直接依赖 `/tasks/{id}/execute`
- 当前链路改为：
- `POST /tasks` 创建任务
- loading 页轮询 `GET /tasks/{id}`
- backend 内嵌 worker 自动消费队列
- `queued -> running -> succeeded/failed` 状态会真实展示到页面
- 本地在 `2026-03-16 16:05` 实测：
- 新任务未显式传 `provider`
- backend 返回 `provider=volcengine`
- 状态按 `queued -> running -> succeeded` 推进
- 最终成功写入 COS 作品

### 5. 首页“灵感广场”暂时不是真实社区流

- 当前 backend 只有“我的作品 / 我的收藏”
- 暂时没有公共广场、推荐作品、官方模板接口
- 所以首页现在优先展示用户自己的最近作品，没有作品时才回落到示例卡片

### 6. AI 精修页目前是基础版

- 现在已经能创建 `img2img` 任务
- 但“贴纸库 / 局部重绘 / 蒙版画笔 / 拖拽缩放”还没有真实素材和交互引擎
- 这部分需要单独补资源和交互方案

### 7. 会员中心里的充值套餐还是展示位

- 积分余额和流水已经是真实接口
- 每日签到现在已经是真实接口
- 激活码兑换现在已经是真实接口
- 当前临时口令为 `zbzl`，单账号成功兑换一次后可获得 `1000` 积分
- 充值套餐、购买支付、会员权益还没有真实支付链路

### 8. 组图生成已经跑通，但耗时会明显增加

- 本地实测 `txt2img + output_count=4` 已成功返回 4 个 `output_urls`
- 同一任务已成功写入 4 条 COS 作品记录
- 外网域名再次调用同一任务，也能拿到 4 个 `output_urls`
- 组图同步执行时间明显长于单图，当前一次 4 图文生图实测约 60 秒

## 需要你帮我准备的素材

### A. 风格迁移参考图

- 每种风格至少 1 到 3 张高质量参考图
- 建议分类：
- 柔焦插画
- 皮克斯风
- 古典油画
- 森系童话
- 赛博肖像
- 素描炭笔

建议素材要求：

- 竖图优先，比例 `4:5`
- 画面主体明确，不要太杂
- 风格特征足够强
- 尽量统一版权来源

### B. 贴纸素材

- 透明底 PNG / WebP
- 建议分类：
- 眼镜
- 帽子
- 发饰
- 耳饰
- 腮红/雀斑点缀
- 相框边框
- 文字贴纸
- 星光、爱心、气泡、花朵等氛围元素

建议素材要求：

- 单个贴纸尺寸尽量在 `512x512` 或 `1024x1024`
- 透明边裁干净
- 命名统一，后面方便做分类检索

### C. 默认插画与占位图

- 登录页/空状态插画
- 风格迁移默认示意图
- 精修工作台默认示意图
- 会员中心 banner

### D. 文案素材

- 关于我们
- 使用帮助
- 会员权益说明
- 积分套餐说明
- 用户协议 / 隐私政策

## 建议下一批开发顺序

- [ ] 统一开发环境里的代理策略，确保命令行和小程序测试结论一致
- [ ] 把首页改成“真实最近作品 + 官方推荐位”
- [ ] 整理 worker 部署方式，线上环境固定保留 1 个异步消费实例
- [ ] 做作品下载、删除、再次编辑
- [ ] 为风格迁移接入内置参考图素材
- [ ] 为贴纸库建立素材目录与分类结构
- [ ] 设计局部重绘的蒙版交互方案
- [ ] 再接支付/会员购买

## 我这边后续会继续推进的内容

- [ ] 首页真实化
- [ ] 结果页更多操作
- [ ] 作品管理能力
- [ ] 精修页贴纸/蒙版结构预埋
- [ ] 把示例文案逐步换成正式产品文案

## 你现在最值得优先提供给我的东西

- [ ] 真机和开发工具里都能稳定访问的 backend 地址配置
- [ ] 一批风格迁移参考图
- [ ] 一批贴纸素材
- [ ] 是否保留“会员充值”入口的产品决定
- [ ] 是否要做公共广场/社区流的产品决定
