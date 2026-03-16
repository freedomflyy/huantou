const { isLoggedIn } = require("./session");
const { ensureSession } = require("./auth");
const { ENABLE_DEMO_MODE } = require("../config");

async function ensureLogin() {
  if (ENABLE_DEMO_MODE) {
    return true;
  }
  if (isLoggedIn()) {
    return true;
  }
  try {
    await ensureSession();
    return true;
  } catch (err) {
    wx.reLaunch({ url: "/pages/login/index" });
    return false;
  }
}

module.exports = {
  ensureLogin,
};
