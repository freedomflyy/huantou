# 幻头小程序 V2

暗色 + 粉紫主题的产品化前端版本，和旧 `miniprogram/` 并行维护。

## 运行

1. 微信开发者工具导入目录：`/home/zbzl/cs/miniprogram_v2`
2. AppID：`wx3078cab5ea320996`
3. 确认 request 合法域名包含：`https://828md02534xr.vicp.fun`
4. 确认 downloadFile 合法域名包含：`https://huanto-1331012038.cos.ap-beijing.myqcloud.com`

## 页面

- `login`
- `home`
- `create-menu`
- `text-generate`
- `image-edit`
- `image-reference`
- `quick-edit`
- `loading`
- `result`
- `history`
- `assets`
- `profile`
- `service`
- `points`

## 关键链路

`POST /tasks` -> 后端异步队列消费 -> `GET /tasks/{id}` 轮询 -> `result`
