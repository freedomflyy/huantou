const { post, refreshSession } = require("./request");
const { saveSession, clearSession, getRefreshToken, getUser, isLoggedIn, hasRealProfile } = require("./session");

function getAppSafe() {
  try {
    return getApp();
  } catch (err) {
    return null;
  }
}

function syncAppSession() {
  const app = getAppSafe();
  if (app && typeof app.syncSession === "function") {
    app.syncSession();
  }
}

function runWxLogin() {
  return new Promise((resolve, reject) => {
    wx.login({
      success(res) {
        if (res.code) {
          resolve(res.code);
          return;
        }
        reject(new Error("微信登录未返回 code"));
      },
      fail(err) {
        reject(new Error((err && err.errMsg) || "微信登录失败"));
      },
    });
  });
}

async function loginWithWechat(profile = {}) {
  const code = await runWxLogin();
  const payload = {
    code,
    nickname: profile.nickname || "微信用户",
    avatar_url: profile.avatar_url || undefined,
  };
  const data = await post("/auth/wechat-login", payload);
  saveSession(data);
  syncAppSession();
  return data;
}

function ensureSession() {
  if (isLoggedIn() && hasRealProfile()) {
    return Promise.resolve(getUser());
  }
  if (getRefreshToken()) {
    return refreshSession().then(() => {
      if (hasRealProfile()) {
        return getUser();
      }
      throw new Error("请先完成微信头像昵称授权");
    });
  }
  return Promise.reject(new Error("请先完成微信头像昵称授权"));
}

async function logoutCurrent() {
  const refreshToken = getRefreshToken();
  if (refreshToken) {
    try {
      await post("/auth/logout", { refresh_token: refreshToken });
    } catch (err) {
      // Ignore logout failure and clear local session anyway.
    }
  }
  clearSession();
  syncAppSession();
}

module.exports = {
  loginWithWechat,
  ensureSession,
  logoutCurrent,
};
