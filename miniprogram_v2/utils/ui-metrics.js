function readWindowInfo() {
  if (typeof wx !== "undefined" && wx.getWindowInfo) {
    return wx.getWindowInfo();
  }
  if (typeof wx !== "undefined" && wx.getSystemInfoSync) {
    return wx.getSystemInfoSync();
  }
  return {};
}

function getUiMetrics() {
  const app = typeof getApp === "function" ? getApp() : null;
  if (app && app.globalData && app.globalData.uiMetrics) {
    return app.globalData.uiMetrics;
  }

  const windowInfo = readWindowInfo();
  const statusBarHeight = windowInfo.statusBarHeight || 20;
  const windowHeight = windowInfo.windowHeight || 667;

  let menuButton = null;
  try {
    if (typeof wx !== "undefined" && wx.getMenuButtonBoundingClientRect) {
      menuButton = wx.getMenuButtonBoundingClientRect();
    }
  } catch (err) {
    menuButton = null;
  }

  const capsuleTop = menuButton && menuButton.top ? menuButton.top : statusBarHeight + 10;
  const capsuleHeight = menuButton && menuButton.height ? menuButton.height : 32;
  const capsuleBottom = capsuleTop + capsuleHeight;

  const metrics = {
    statusBarHeight,
    windowHeight,
    capsuleTop,
    capsuleHeight,
    capsuleBottom,
    navContentTop: capsuleTop,
    pageTopInset: capsuleBottom + 12,
    homeSpacerHeight: capsuleBottom + 32,
  };

  if (app && app.globalData) {
    app.globalData.uiMetrics = metrics;
  }

  return metrics;
}

module.exports = {
  getUiMetrics,
};
