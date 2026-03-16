const { ensureLogin } = require("../../utils/guard");
const { get } = require("../../utils/request");

const TABS = [
  { key: "stickers", label: "贴纸", glyph: "贴" },
  { key: "text", label: "文字", glyph: "字" },
  { key: "frames", label: "边框", glyph: "框" },
];

const STICKER_CATEGORIES = ["动物", "植物", "几何", "表情", "装饰", "日常"];

function buildPlaceholders(prefix, count, type) {
  return Array.from({ length: count }).map((_, index) => ({
    id: `${prefix}-${index + 1}`,
    title: type === "text" ? `字体 ${index + 1}` : (type === "frame" ? `边框 ${index + 1}` : `贴纸 ${index + 1}`),
  }));
}

Page({
  data: {
    taskId: "",
    imageUrl: "",
    activeTab: "stickers",
    activeCategory: STICKER_CATEGORIES[0],
    tabs: TABS,
    categories: STICKER_CATEGORIES,
    recentStickers: buildPlaceholders("recent", 4, "sticker"),
    stickerItems: buildPlaceholders("sticker", 8, "sticker"),
    fontItems: buildPlaceholders("font", 8, "text"),
    frameItems: buildPlaceholders("frame", 6, "frame"),
  },

  onLoad(query) {
    this.setData({
      taskId: query.taskId || "",
      imageUrl: query.imageUrl ? decodeURIComponent(query.imageUrl) : "",
    });
  },

  async onShow() {
    const ok = await ensureLogin();
    if (!ok) return;
    if (!this.data.imageUrl && this.data.taskId) {
      await this.loadPreview();
    }
  },

  async loadPreview() {
    try {
      const [task, assetsRes] = await Promise.all([
        get(`/tasks/${this.data.taskId}`),
        get("/assets?limit=100"),
      ]);
      const outputs = (assetsRes.items || []).filter((item) => item.source_task_id === this.data.taskId);
      const imageUrl = outputs[0]
        ? (outputs[0].thumbnail_url || outputs[0].file_url)
        : (task.input_image_url || "");
      if (imageUrl) {
        this.setData({ imageUrl });
      }
    } catch (err) {
      // Keep placeholder state when task preview is unavailable.
    }
  },

  onTabTap(e) {
    const tab = e.currentTarget.dataset.tab;
    if (!tab) return;
    this.setData({ activeTab: tab });
  },

  onCategoryTap(e) {
    const category = e.currentTarget.dataset.category;
    if (!category) return;
    this.setData({ activeCategory: category });
  },

  onPlaceholderTap() {
    wx.showToast({
      title: "素材准备中，先保留占位",
      icon: "none",
    });
  },

  onResetTap() {
    wx.showToast({
      title: "装饰能力接入后会支持重置",
      icon: "none",
    });
  },

  onSaveTap() {
    wx.showToast({
      title: "导出能力会在素材和编辑逻辑完成后接入",
      icon: "none",
    });
  },

  previewImage() {
    if (!this.data.imageUrl) return;
    wx.previewImage({
      current: this.data.imageUrl,
      urls: [this.data.imageUrl],
    });
  },
});
