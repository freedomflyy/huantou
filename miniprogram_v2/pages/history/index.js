const { ensureLogin } = require("../../utils/guard");
const { get } = require("../../utils/request");
const { toTaskCardViewModel } = require("../../utils/view-models");

Page({
  data: {
    tasks: [],
  },

  async onShow() {
    const ok = await ensureLogin();
    if (!ok) return;
    await this.loadTasks();
  },

  async loadTasks() {
    try {
      const res = await get("/tasks?limit=100");
      this.setData({
        tasks: (res.items || []).map((item) => toTaskCardViewModel(item)),
      });
    } catch (err) {
      wx.showToast({
        title: err.message || "创作记录加载失败",
        icon: "none",
      });
    }
  },

  openTask(e) {
    const taskId = e.currentTarget.dataset.taskid;
    const status = e.currentTarget.dataset.status;
    const from = e.currentTarget.dataset.from || "";
    if (!taskId) return;
    if (status === "queued" || status === "running") {
      wx.navigateTo({ url: `/pages/loading/index?taskId=${encodeURIComponent(taskId)}&from=${encodeURIComponent(from)}` });
      return;
    }
    wx.navigateTo({ url: `/pages/result/index?taskId=${encodeURIComponent(taskId)}&from=${encodeURIComponent(from)}` });
  },

  goCreate() {
    wx.navigateTo({ url: "/pages/create-menu/index" });
  },
});
