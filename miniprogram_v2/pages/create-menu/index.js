const { getCreateModes, getStyleCards } = require("../../utils/demo-data");

Page({
  data: {
    modes: [],
    ideas: [],
  },

  onShow() {
    this.setData({
      modes: getCreateModes(),
      ideas: getStyleCards().map((item) => item.name),
    });
  },

  onModeTap(e) {
    const url = e.currentTarget.dataset.url;
    if (!url) return;
    wx.navigateTo({ url });
  },

  onIdeaTap(e) {
    const idea = e.currentTarget.dataset.idea;
    if (!idea) return;
    wx.navigateTo({ url: `/pages/text-generate/index?idea=${encodeURIComponent(idea)}` });
  },

  goHelp() {
    wx.navigateTo({ url: "/pages/service/index?type=help" });
  },
});
