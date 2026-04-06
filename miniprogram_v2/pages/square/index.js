const { ensureFeatureLogin } = require("../../utils/guard");
const { get } = require("../../utils/request");
const { isLoggedIn, hasRealProfile } = require("../../utils/session");
const { toAssetCardViewModel, toShowcaseCardViewModel } = require("../../utils/view-models");
const { getShowcaseFallback } = require("../../utils/avatar-studio");
const { getUiMetrics } = require("../../utils/ui-metrics");
const { orderShowcaseItems } = require("../../utils/showcase");

const PLAZA_TABS = ["热门", "最新"];
const FALLBACK_CREATORS = ["用户9527", "AvatarMaster", "桃桃同学", "暖光练习生"];

function getFallbackGallery() {
  return getShowcaseFallback().map((item, index) => ({
    ...item,
    creatorName: FALLBACK_CREATORS[index % FALLBACK_CREATORS.length],
  }));
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
    plazaTabs: PLAZA_TABS,
    currentPlazaTab: PLAZA_TABS[0],
    gallery: getFallbackGallery(),
    displayGallery: getFallbackGallery(),
    pageTopStyle: "",
  },

  onLoad() {
    const metrics = getUiMetrics();
    this.setData({
      pageTopStyle: `padding-top:${metrics.pageTopInset}px;`,
    });
  },

  async onShow() {
    await this.loadData();
  },

  setDisplayGallery(tab = this.data.currentPlazaTab, gallery = this.data.gallery) {
    const list = orderShowcaseItems(gallery, tab);
    this.setData({
      currentPlazaTab: tab,
      displayGallery: list,
    });
  },

  async loadData() {
    const loginReady = isLoggedIn() && hasRealProfile();
    try {
      const showcaseRes = await get("/showcase?limit=24");
      const gallery = decorateGallery((showcaseRes.items || []).map(toShowcaseCardViewModel));
      if (gallery.length) {
        this.setData({ gallery });
        this.setDisplayGallery(this.data.currentPlazaTab, gallery);
        return;
      }
    } catch (err) {
      if (loginReady) {
      try {
        const [assetsRes, tasksRes] = await Promise.all([
          get("/assets?limit=24"),
          get("/tasks?limit=60"),
        ]);
        const taskMap = {};
        (tasksRes.items || []).forEach((task) => {
          taskMap[task.id] = task;
        });
        const gallery = decorateGallery((assetsRes.items || []).map((item) => toAssetCardViewModel(item, taskMap)));
        if (gallery.length) {
          this.setData({ gallery });
          this.setDisplayGallery(this.data.currentPlazaTab, gallery);
          return;
        }
      } catch (nestedErr) {
        // Fall through to curated data.
      }
      }
    }

    const fallbackGallery = getFallbackGallery();
    this.setData({ gallery: fallbackGallery });
    this.setDisplayGallery(this.data.currentPlazaTab, fallbackGallery);
  },

  onPlazaTabTap(e) {
    const tab = e.currentTarget.dataset.tab;
    if (!tab) return;
    this.setDisplayGallery(tab, this.data.gallery);
  },

  async onGalleryTap(e) {
    const taskId = e.currentTarget.dataset.taskid;
    const style = e.currentTarget.dataset.style || "";
    if (taskId) {
      wx.navigateTo({ url: `/pages/result/index?taskId=${encodeURIComponent(taskId)}` });
      return;
    }
    const ok = await ensureFeatureLogin("登录后才可以生成同款头像");
    if (!ok) return;
    if (style) {
      wx.navigateTo({ url: `/pages/image-reference/index?style=${encodeURIComponent(style)}` });
      return;
    }
    wx.navigateTo({ url: "/pages/image-reference/index" });
  },

  goCreate() {
    wx.reLaunch({ url: "/pages/create-menu/index" });
  },
});
