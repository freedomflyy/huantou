const { ensureLogin } = require("../../utils/guard");
const { get } = require("../../utils/request");
const { toAssetCardViewModel } = require("../../utils/view-models");
const { getShowcaseFallback } = require("../../utils/avatar-studio");
const { getUiMetrics } = require("../../utils/ui-metrics");

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
    const ok = await ensureLogin();
    if (!ok) return;
    await this.loadData();
  },

  setDisplayGallery(tab = this.data.currentPlazaTab, gallery = this.data.gallery) {
    const list = tab === "最新" ? gallery.slice().reverse() : gallery.slice();
    this.setData({
      currentPlazaTab: tab,
      displayGallery: list,
    });
  },

  async loadData() {
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
    } catch (err) {
      // Fall through to curated data.
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

  onGalleryTap(e) {
    const taskId = e.currentTarget.dataset.taskid;
    if (taskId) {
      wx.navigateTo({ url: `/pages/result/index?taskId=${encodeURIComponent(taskId)}` });
      return;
    }
    wx.navigateTo({ url: "/pages/image-reference/index" });
  },

  goCreate() {
    wx.reLaunch({ url: "/pages/create-menu/index" });
  },
});
