function saveSession(payload) {
  wx.setStorageSync("access_token_v2", payload.access_token || "");
  wx.setStorageSync("refresh_token_v2", payload.refresh_token || "");
  wx.setStorageSync("user_info_v2", payload.user || null);
}

function updateUser(user) {
  wx.setStorageSync("user_info_v2", user || null);
}

function clearSession() {
  wx.removeStorageSync("access_token_v2");
  wx.removeStorageSync("refresh_token_v2");
  wx.removeStorageSync("user_info_v2");
}

function getToken() {
  return wx.getStorageSync("access_token_v2") || "";
}

function getRefreshToken() {
  return wx.getStorageSync("refresh_token_v2") || "";
}

function getUser() {
  return wx.getStorageSync("user_info_v2") || null;
}

function hasRealProfile() {
  const user = getUser();
  if (!user) return false;
  const nickname = (user.nickname || "").trim();
  const avatarUrl = (user.avatar_url || "").trim();
  return !!nickname && nickname !== "微信用户" && !!avatarUrl;
}

function isLoggedIn() {
  return !!getToken();
}

module.exports = {
  saveSession,
  clearSession,
  getToken,
  getRefreshToken,
  getUser,
  hasRealProfile,
  isLoggedIn,
  updateUser,
};
