const { ensureLogin } = require("../../utils/guard");
const { get } = require("../../utils/request");
const { getStyleTemplates } = require("../../utils/avatar-studio");

const FEATURE_ITEMS = [
  { key: "style-transfer", title: "风格迁移", note: "多种艺术风格", glyph: "绘", tone: "tone-pink" },
  { key: "ai-edit", title: "AI编辑", note: "智能修图优化", glyph: "修", tone: "tone-orange" },
  { key: "text-generate", title: "文生图", note: "文字一键绘图", glyph: "文", tone: "tone-rose" },
  { key: "decorate", title: "贴纸像框", note: "精美装饰点缀", glyph: "框", tone: "tone-amber" },
];

function getFallbackInspirations() {
  return getStyleTemplates().slice(0, 4).map((item) => ({
    id: item.id,
    title: item.name,
    imageUrl: "",
    coverClass: item.coverClass,
  }));
}

function mapMaterialStyles(items, fallbackItems) {
  return items.map((item, index) => {
    const fallback = fallbackItems[index % fallbackItems.length] || fallbackItems[0] || {};
    return {
      id: item.id,
      title: item.title,
      imageUrl: item.file_url || "",
      coverClass: fallback.coverClass || "cover-cream",
    };
  });
}

Page({
  data: {
    features: FEATURE_ITEMS,
    inspirations: getFallbackInspirations(),
  },

  async onShow() {
    const ok = await ensureLogin();
    if (!ok) return;
    await this.loadInspirations();
  },

  async loadInspirations() {
    const fallback = getFallbackInspirations();
    try {
      const res = await get("/materials");
      if (res.home_styles && res.home_styles.length) {
        this.setData({ inspirations: mapMaterialStyles(res.home_styles, fallback) });
        return;
      }
    } catch (err) {
      // Keep curated fallback cards when materials are unavailable.
    }
    this.setData({ inspirations: fallback });
  },

  onBack() {
    if (getCurrentPages().length > 1) {
      wx.navigateBack();
      return;
    }
    wx.reLaunch({ url: "/pages/home/index" });
  },

  onFeatureTap(e) {
    const key = e.currentTarget.dataset.key;
    const routes = {
      "style-transfer": "/pages/image-reference/index",
      "ai-edit": "/pages/image-edit/index",
      "text-generate": "/pages/text-generate/index",
      decorate: "/pages/avatar-decorate/index",
    };
    const url = routes[key];
    if (!url) return;
    wx.navigateTo({ url });
  },

  onInspirationTap(e) {
    const title = e.currentTarget.dataset.title;
    wx.navigateTo({
      url: `/pages/image-reference/index?style=${encodeURIComponent(title || "")}`,
    });
  },

  goSquare() {
    wx.reLaunch({ url: "/pages/square/index" });
  },
});
