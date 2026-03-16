const { loginWithWechat } = require("../../utils/auth");

Page({
  data: {
    submitting: false,
    errorMsg: "",
  },

  async enterApp() {
    if (this.data.submitting) return;
    this.setData({ submitting: true, errorMsg: "" });
    try {
      await loginWithWechat();
      wx.reLaunch({ url: "/pages/home/index" });
    } catch (err) {
      this.setData({ errorMsg: err.message || "登录失败，请稍后重试" });
    } finally {
      this.setData({ submitting: false });
    }
  },
});
