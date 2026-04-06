const { isLoggedIn, hasRealProfile } = require("./session");
const { ensureSession } = require("./auth");
const { ENABLE_DEMO_MODE } = require("../config");

async function ensureLogin() {
  if (ENABLE_DEMO_MODE) {
    return true;
  }
  if (isLoggedIn() && hasRealProfile()) {
    return true;
  }
  try {
    await ensureSession();
    return true;
  } catch (err) {
    wx.showToast({
      title: "请先登录后再继续",
      icon: "none",
    });
    return false;
  }
}

async function ensureFeatureLogin(message = "请先登录后再使用这个功能") {
  if (ENABLE_DEMO_MODE) {
    return true;
  }
  if (isLoggedIn() && hasRealProfile()) {
    return true;
  }
  try {
    await ensureSession();
    return true;
  } catch (err) {
    wx.showToast({
      title: message,
      icon: "none",
    });
    setTimeout(() => {
      wx.navigateTo({ url: "/pages/login/index" });
    }, 120);
    return false;
  }
}

module.exports = {
  ensureLogin,
  ensureFeatureLogin,
};
