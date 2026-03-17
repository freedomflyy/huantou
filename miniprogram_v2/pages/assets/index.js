const { ensureLogin } = require("../../utils/guard");
const { get, post, del } = require("../../utils/request");
const { toAssetCardViewModel } = require("../../utils/view-models");

Page({
  data: {
    selectMode: false,
    target: "",
    currentTab: "mine",
    myAssets: [],
    favoriteAssets: [],
    taskMap: {},
    errorMsg: "",
  },

  onLoad(query) {
    this.setData({
      selectMode: query && query.select === "1",
      target: (query && query.target) || "",
    });
  },

  async onShow() {
    const ok = await ensureLogin();
    if (!ok) return;
    await this.loadAssets();
  },

  findCard(section, id) {
    const list = section === "favorites" ? this.data.favoriteAssets : this.data.myAssets;
    return list.find((item) => item.id === id) || null;
  },

  onTabTap(e) {
    const tab = e.currentTarget.dataset.tab;
    if (!tab) return;
    this.setData({ currentTab: tab });
  },

  async loadAssets() {
    this.setData({ errorMsg: "" });
    try {
      const [tasksRes, myAssetsRes, favoriteRes] = await Promise.all([
        get("/tasks?limit=100"),
        get("/assets?limit=100"),
        get("/assets/favorites?limit=100"),
      ]);
      const taskMap = {};
      (tasksRes.items || []).forEach((task) => {
        taskMap[task.id] = task;
      });
      this.setData({
        taskMap,
        myAssets: (myAssetsRes.items || []).map((item) => toAssetCardViewModel(item, taskMap)),
        favoriteAssets: (favoriteRes.items || []).map((item) => toAssetCardViewModel(item, taskMap)),
      });
    } catch (err) {
      this.setData({ errorMsg: err.message || "作品加载失败" });
    }
  },

  async onFavoriteTap(e) {
    const id = e.currentTarget.dataset.id;
    const section = e.currentTarget.dataset.section;
    const favorited = !!e.currentTarget.dataset.favorited;
    if (!id) return;
    try {
      if (favorited) {
        await del(`/assets/${id}/favorite`);
      } else {
        await post(`/assets/${id}/favorite`, {});
      }
      wx.showToast({
        title: favorited ? "已取消收藏" : "已加入收藏",
        icon: "none",
      });
      await this.loadAssets();
    } catch (err) {
      const item = this.findCard(section, id);
      this.setData({ errorMsg: err.message || "收藏操作失败" });
      if (item && item.fileUrl) {
        wx.showToast({ title: err.message || "收藏操作失败", icon: "none" });
      }
    }
  },

  onAssetTap(e) {
    const taskId = e.currentTarget.dataset.taskid;
    const id = e.currentTarget.dataset.id;
    const section = e.currentTarget.dataset.section;
    const asset = this.findCard(section, id);
    if (this.data.selectMode && asset) {
      const eventChannel = this.getOpenerEventChannel();
      eventChannel.emit("assetSelected", {
        target: this.data.target,
        url: asset.fileUrl || asset.imageUrl,
        item: asset,
      });
      wx.navigateBack();
      return;
    }
    if (taskId) {
      wx.navigateTo({ url: `/pages/result/index?taskId=${encodeURIComponent(taskId)}` });
      return;
    }
    if (asset && asset.fileUrl) {
      wx.previewImage({
        current: asset.fileUrl,
        urls: [asset.fileUrl],
      });
      return;
    }
    wx.navigateTo({ url: "/pages/create-menu/index" });
  },

  goCreate() {
    wx.navigateTo({ url: "/pages/create-menu/index" });
  },
});
