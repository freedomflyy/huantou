const { ensureLogin } = require("../../utils/guard");
const { get } = require("../../utils/request");
const { getUser } = require("../../utils/session");
const { toAssetCardViewModel } = require("../../utils/view-models");
const { getStyleTemplates, getShowcaseFallback } = require("../../utils/avatar-studio");

const FEATURE_ITEMS = [
  { key: "smart-edit", title: "图像编辑", note: "细节优化", tone: "tone-blue" },
  { key: "cutout", title: "智能抠图", note: "背景替换", tone: "tone-purple" },
];

const PLAZA_TABS = ["热门", "最新"];
const FALLBACK_CREATORS = ["用户9527", "AvatarMaster", "桃桃同学", "暖光练习生"];

function getFallbackGallery() {
  return getShowcaseFallback().map((item, index) => ({
    ...item,
    creatorName: FALLBACK_CREATORS[index % FALLBACK_CREATORS.length],
    author: "广场精选",
  }));
}

function attachTemplateImages(templates, gallery) {
  const list = gallery && gallery.length ? gallery : getFallbackGallery();
  return templates.slice(0, 6).map((item, index) => ({
    ...item,
    imageUrl: list[index % list.length] ? list[index % list.length].imageUrl || "" : "",
  }));
}

function mapHomeStyles(materialItems, fallbackTemplates) {
  return materialItems.map((item, index) => {
    const fallback = fallbackTemplates[index % fallbackTemplates.length] || fallbackTemplates[0] || {};
    return {
      id: item.id,
      name: item.title,
      desc: item.subtitle || fallback.desc || "",
      badge: item.badge || fallback.badge || "",
      coverClass: fallback.coverClass || "cover-cream",
      imageUrl: item.file_url || "",
    };
  });
}

function decorateGallery(items) {
  const source = items && items.length ? items : getFallbackGallery();
  return source.map((item, index) => ({
    ...item,
    creatorName: item.creatorName || FALLBACK_CREATORS[index % FALLBACK_CREATORS.length],
  }));
}

Page({
  data: {
    user: {
      nickname: "创作者",
    },
    featureItems: FEATURE_ITEMS,
    plazaTabs: PLAZA_TABS,
    currentPlazaTab: PLAZA_TABS[0],
    styleTemplates: attachTemplateImages(getStyleTemplates(), []),
    gallery: getFallbackGallery(),
    displayGallery: getFallbackGallery().slice(0, 4),
  },

  async onShow() {
    const ok = await ensureLogin();
    if (!ok) return;
    await this.loadData();
  },

  setDisplayGallery(tab = this.data.currentPlazaTab, gallery = this.data.gallery) {
    const list = tab === "最新" ? gallery.slice().reverse() : gallery.slice();
    this.setData({
      currentPlazaTab: tab,
      displayGallery: list.slice(0, 4),
    });
  },

  async loadData() {
    const user = getUser() || {};
    const fallbackGallery = getFallbackGallery();
    const fallbackTemplates = getStyleTemplates();
    let gallery = fallbackGallery;
    let styleTemplates = attachTemplateImages(fallbackTemplates, fallbackGallery);

    this.setData({
      user: {
        nickname: user.nickname || "创作者",
      },
    });

    try {
      const [assetsRes, tasksRes] = await Promise.all([
        get("/assets?limit=12"),
        get("/tasks?limit=50"),
      ]);
      const taskMap = {};
      (tasksRes.items || []).forEach((task) => {
        taskMap[task.id] = task;
      });
      const galleryItems = decorateGallery((assetsRes.items || []).map((item) => toAssetCardViewModel(item, taskMap)));
      if (galleryItems.length) {
        gallery = galleryItems;
        styleTemplates = attachTemplateImages(fallbackTemplates, galleryItems);
      }
    } catch (err) {
      // Keep fallback gallery.
    }

    try {
      const materialsRes = await get("/materials");
      if (materialsRes.home_styles && materialsRes.home_styles.length) {
        styleTemplates = mapHomeStyles(materialsRes.home_styles, fallbackTemplates);
      }
    } catch (err) {
      // Keep template fallback when materials are unavailable.
    }

    this.setData({
      gallery,
      styleTemplates,
    });
    this.setDisplayGallery(this.data.currentPlazaTab, gallery);
  },

  goStyleTransfer() {
    wx.navigateTo({ url: "/pages/image-reference/index" });
  },

  goTextGenerate() {
    wx.navigateTo({ url: "/pages/text-generate/index" });
  },

  goSquare() {
    wx.reLaunch({ url: "/pages/square/index" });
  },

  goPoints() {
    wx.navigateTo({ url: "/pages/points/index" });
  },

  onFeatureTap(e) {
    const key = e.currentTarget.dataset.key;
    if (key === "smart-edit" || key === "cutout") {
      wx.navigateTo({ url: "/pages/image-edit/index" });
    }
  },

  onTemplateTap(e) {
    const style = e.currentTarget.dataset.style;
    wx.navigateTo({
      url: `/pages/image-reference/index?style=${encodeURIComponent(style || "")}`,
    });
  },

  onPlazaTabTap(e) {
    const tab = e.currentTarget.dataset.tab;
    if (!tab) return;
    this.setDisplayGallery(tab, this.data.gallery);
  },

  onGalleryTap(e) {
    const taskId = e.currentTarget.dataset.taskid;
    if (taskId) {
      wx.navigateTo({ url: `/pages/result/index?taskId=${encodeURIComponent(taskId)}` });
      return;
    }
    this.goSquare();
  },
});
