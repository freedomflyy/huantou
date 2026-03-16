# 幻头 AI头像生成小程序 UI 原型说明

(供 AI Agent / Codex 阅读)

------

# 1 项目概述

项目名称：

**幻头（Huanto）**

项目类型：

**AI 头像生成工具小程序 UI 原型**

用途：

- 毕业设计
- AI 图像生成工具
- 目前是 **HTML UI 原型**
- 后续将转换为 **微信小程序**

当前技术：

```
HTML
TailwindCSS
Iconify Icons
```

每个页面为 **独立 HTML 文件**，通过 `href` 实现跳转。

------

# 2 UI 风格

设计风格：

```
深色科技感
玻璃拟态
金色点缀
高端 AI 工具风格
```

视觉特征：

- 深色背景
- 金色渐变
- glass blur 卡片
- 圆角 UI
- 科技感动画

------

# 3 页面列表

当前 UI 原型包含以下页面：

```
home.html
text-generate.html
image-edit.html
image-reference.html
quick-edit.html
loading.html
result.html
ai-editor.html
preview.html
gallery.html
history.html
profile.html
assets.html
create-menu.html
```

共：

```
14 个页面
```

------

# 4 页面功能说明

## 首页

```
home.html
```

功能：

AI 工具入口页面

元素：

- Banner
- 四个功能入口
- 最近作品
- 底部导航

入口按钮：

```
文本生成 → text-generate.html
图片修改 → image-edit.html
参考图生成 → image-reference.html
快速编辑 → quick-edit.html
```

底部导航：

```
首页 → home.html
画廊 → gallery.html
创建 → create-menu.html
历史 → history.html
我的 → profile.html
```

------

# 5 创作流程

AI 头像生成流程：

```
text-generate.html
↓
loading.html
↓
result.html
↓
preview.html
↓
ai-editor.html
```

说明：

1 输入 prompt
2 生成头像
3 查看结果
4 预览大图
5 继续编辑

------

# 6 页面跳转关系

## 首页

```
home
 ├ text-generate
 ├ image-edit
 ├ image-reference
 ├ quick-edit
 ├ gallery
 ├ history
 └ profile
```

------

## 文本生成流程

```
text-generate
 └ loading
     └ result
         ├ preview
         └ ai-editor
```

------

## 图片修改流程

```
image-edit
 └ loading
     └ result
```

------

## 参考图生成流程

```
image-reference
 └ loading
     └ result
```

------

## 快速编辑流程

```
quick-edit
 ├ preview
 └ ai-editor
```

------

## 浏览流程

```
gallery
 └ preview
```

------

## 历史流程

```
history
 └ result
```

------

## 个人中心

```
profile
 └ assets
     └ preview
```

------

# 7 页面职责

### text-generate

输入 Prompt

元素：

```
prompt 输入框
风格选择
比例选择
生成按钮
```

------

### image-edit

上传图片进行 AI 修改

元素：

```
上传图片
修改提示词
开始修改
```

------

### image-reference

参考图生成

元素：

```
上传参考图
prompt
生成按钮
```

------

### quick-edit

基础图片编辑

功能：

```
裁剪
旋转
翻转
亮度
对比度
```

------

### loading

生成中页面

元素：

```
动画
进度条
生成信息
```

------

### result

生成结果页

元素：

```
2x2 图片结果
继续编辑
再生成
查看大图
```

------

### preview

大图预览

元素：

```
图片展示
下载
收藏
分享
```

------

### ai-editor

AI 编辑页

功能：

```
重绘
风格化
细节增强
扩展
```

------

### gallery

优秀作品展示

元素：

```
作品瀑布流
点击查看
```

------

### history

用户生成历史

元素：

```
历史记录列表
点击查看结果
```

------

### profile

用户中心

元素：

```
用户信息
资产入口
帮助
反馈
```

------

### assets

用户资产

包含：

```
保存作品
收藏
草稿
```

------

### create-menu

创作入口

功能：

```
选择创作方式
```

选项：

```
文本生成
图片修改
参考图生成
快速编辑
```

------

# 8 需要 Agent 完成的任务

Codex / Agent 需要：

### 1 修复页面跳转

检查：

```
href 是否正确
页面是否存在
```

------

### 2 优化结构

建议：

```
提取通用组件
统一 CSS
统一导航
```

------

### 3 添加页面逻辑

例如：

```
loading 自动跳转 result
preview 图片切换
结果页选择图片
```

------

### 4 准备小程序迁移

目标：

将 HTML 转换为：

```
微信小程序
```

建议结构：

```
pages/
  home
  text-generate
  image-edit
  image-reference
  quick-edit
  result
  preview
  gallery
  history
  profile
  assets
```

------

# 9 项目目标

本项目最终目标：

```
AI 头像生成小程序
```

功能：

```
文本生成头像
图片修改头像
参考图生成头像
AI 编辑头像
历史记录
作品管理
```

------

# 10 当前阶段

当前阶段：

```
UI 原型阶段
```

后续步骤：

```
1 调试 HTML UI
2 完善交互
3 转换为小程序
4 接入 AI 图像接口
```

------

# 11 给 Agent 的任务总结

Agent 需要：

```
1 检查所有 HTML 页面跳转
2 修复缺失页面
3 统一导航结构
4 优化 UI 代码结构
5 准备小程序迁移
```

------

# 12 原型联通更新（2026-03-12）

本轮 UI 梳理已完成：

```
1 统一文件名：text-generate.html
2 文本生成 / 图片修改 / 参考图生成 均走 loading -> result 流程
3 loading / result / preview 新增来源路由逻辑（prototype-routing.js）
4 gallery / assets / quick-edit 进入 preview 后可正确返回来源页
5 profile 中占位入口不再使用 #，改为 service.html 功能占位页
6 全量 href 已校验，无缺失页面链接
```

新增文件：

```
ui/prototype-routing.js
ui/service.html
```

------

