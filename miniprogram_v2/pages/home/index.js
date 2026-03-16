const { ensureLogin } = require("../../utils/guard");
const { get } = require("../../utils/request");
const { getUser } = require("../../utils/session");
const { toAssetCardViewModel } = require("../../utils/view-models");

const QUICK_ACTIONS = [
  { key: "image-edit", glyph: "换", label: "换头像", desc: "上传后智能精修" },
  { key: "create-menu", glyph: "灵", label: "灵感集", desc: "看看现在做什么" },
  { key: "text-generate", glyph: "绘", label: "AI绘画", desc: "一句话生成头像" },
  { key: "profile", glyph: "我", label: "个人页", desc: "作品与会员信息" },
];

const HOME_TAGS = ["推荐", "我的作品", "最近生成", "温暖风格"];

const FALLBACK_GALLERY = [
  { id: "fallback-1", title: "奶油晨光", author: "灵感示例", likes: "去创作", coverClass: "cover-cream", badge: "示例" },
  { id: "fallback-2", title: "午后暖调", author: "灵感示例", likes: "去创作", coverClass: "cover-sunset", badge: "示例" },
  { id: "fallback-3", title: "森林回眸", author: "灵感示例", likes: "去创作", coverClass: "cover-forest", badge: "示例" },
  { id: "fallback-4", title: "夜色肖像", author: "灵感示例", likes: "去创作", coverClass: "cover-night", badge: "示例" },
];

Page({
  data: {
    user: {
      nickname: "创作者",
    },
    quickActions: QUICK_ACTIONS,
    tags: HOME_TAGS,
    currentTag: "推荐",
    gallery: FALLBACK_GALLERY,
  },

  async onShow() {
    const ok = await ensureLogin();
    if (!ok) return;
    await this.loadData();
  },

  async loadData() {
    const user = getUser() || {};
    this.setData({
      user: {
        nickname: user.nickname || "创作者",
      },
    });

    try {
      const [assetsRes, tasksRes] = await Promise.all([
        get("/assets?limit=4"),
        get("/tasks?limit=40"),
      ]);
      const taskMap = {};
      (tasksRes.items || []).forEach((task) => {
        taskMap[task.id] = task;
      });
      const gallery = (assetsRes.items || []).map((item) => toAssetCardViewModel(item, taskMap));
      if (gallery.length) {
        this.setData({ gallery });
      }
    } catch (err) {
      this.setData({ gallery: FALLBACK_GALLERY });
    }
  },

  goCreateMenu() {
    wx.navigateTo({ url: "/pages/create-menu/index" });
  },

  onActionTap(e) {
    const key = e.currentTarget.dataset.key;
    const map = {
      "image-edit": "/pages/image-edit/index",
      "create-menu": "/pages/create-menu/index",
      "text-generate": "/pages/text-generate/index",
      profile: "/pages/profile/index",
    };
    const url = map[key];
    if (!url) return;
    wx.navigateTo({ url });
  },

  onTagTap(e) {
    const tag = e.currentTarget.dataset.tag;
    if (!tag) return;
    this.setData({ currentTag: tag });
  },

  onGalleryTap(e) {
    const taskId = e.currentTarget.dataset.taskid;
    if (taskId) {
      wx.navigateTo({ url: `/pages/result/index?taskId=${encodeURIComponent(taskId)}` });
      return;
    }
    wx.navigateTo({ url: "/pages/create-menu/index" });
  },

  goAssets() {
    wx.navigateTo({ url: "/pages/assets/index" });
  },
});
