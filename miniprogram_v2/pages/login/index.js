const { loginWithWechat, logoutCurrent } = require("../../utils/auth");
const { upload, patch } = require("../../utils/request");
const { getUser, updateUser } = require("../../utils/session");
const { fetchPublicAssets } = require("../../utils/public-assets");

function syncAppSessionSafe() {
  try {
    const app = getApp();
    if (app && typeof app.syncSession === "function") {
      app.syncSession();
    }
  } catch (err) {
    // Ignore app sync failure on login page.
  }
}

Page({
  data: {
    submitting: false,
    agreed: false,
    errorMsg: "",
    profileNickname: "",
    profileAvatarUrl: "",
    profileAvatarPath: "",
    brandingLogoUrl: "",
    profileSheetVisible: false,
  },

  onLoad() {
    const user = getUser() || {};
    this.setData({
      profileNickname: user.nickname && user.nickname !== "微信用户" ? user.nickname : "",
      profileAvatarUrl: user.avatar_url || "",
      profileAvatarPath: "",
    });
    this.loadPublicAssets();
  },

  async loadPublicAssets() {
    try {
      const assets = await fetchPublicAssets();
      this.setData({
        brandingLogoUrl: assets.loginLogoUrl || "",
      });
    } catch (err) {
      // Keep the avatar area empty when the branding asset is unavailable.
    }
  },

  toggleAgreement() {
    this.setData({
      agreed: !this.data.agreed,
    });
  },

  onNicknameInput(e) {
    this.setData({
      profileNickname: (e.detail.value || "").trim(),
      errorMsg: "",
    });
  },

  onChooseAvatar(e) {
    const path = (e.detail && e.detail.avatarUrl) || "";
    if (!path) return;
    this.setData({
      profileAvatarUrl: path,
      profileAvatarPath: path,
      errorMsg: "",
    });
  },

  openProfileSheet() {
    this.setData({
      profileSheetVisible: true,
      errorMsg: "",
    });
  },

  closeProfileSheet() {
    if (this.data.submitting) return;
    this.setData({
      profileSheetVisible: false,
    });
  },

  openTerms() {
    wx.navigateTo({ url: "/pages/service/index?type=terms" });
  },

  openPrivacy() {
    wx.navigateTo({ url: "/pages/service/index?type=privacy" });
  },

  onSecondaryTap(e) {
    const type = e.currentTarget.dataset.type;
    const tips = {
      phone: "当前版本先开放微信登录，手机号登录后续接入",
      other: "其他登录方式后续开放，当前请使用微信一键登录",
    };
    wx.showToast({
      title: tips[type] || "当前入口暂未开放",
      icon: "none",
    });
  },

  validateProfile() {
    if (!this.data.agreed) {
      this.setData({ errorMsg: "请先勾选并同意用户协议与隐私政策" });
      wx.showToast({ title: "请先同意协议", icon: "none" });
      return false;
    }

    const nickname = (this.data.profileNickname || "").trim();
    const avatarUrl = (this.data.profileAvatarUrl || "").trim();

    if (!avatarUrl) {
      this.setData({ errorMsg: "请先选择微信头像后再继续" });
      return false;
    }
    if (!nickname || nickname === "微信用户") {
      this.setData({ errorMsg: "请先填写一个可用昵称后再继续" });
      return false;
    }
    return true;
  },

  async handlePrimaryLogin() {
    if (this.data.submitting) return;
    if (!this.data.agreed) {
      this.validateProfile();
      return;
    }

    const nickname = (this.data.profileNickname || "").trim();
    const avatarUrl = (this.data.profileAvatarUrl || "").trim();
    if (!avatarUrl || !nickname || nickname === "微信用户") {
      this.openProfileSheet();
      return;
    }

    await this.enterApp();
  },

  async enterApp() {
    if (this.data.submitting) return;
    if (!this.validateProfile()) return;

    const nickname = (this.data.profileNickname || "").trim();
    const avatarUrl = (this.data.profileAvatarUrl || "").trim();
    const avatarPath = (this.data.profileAvatarPath || "").trim();

    let loggedIn = false;
    try {
      this.setData({ submitting: true, errorMsg: "" });

      const loginPayload = {
        nickname,
        avatar_url: !avatarPath && /^https?:\/\//.test(avatarUrl) ? avatarUrl : undefined,
      };
      const loginData = await loginWithWechat(loginPayload);
      loggedIn = true;

      let finalUser = loginData.user;
      if (avatarPath) {
        const uploaded = await upload("/assets/upload", avatarPath, { name: "file" });
        finalUser = await patch("/auth/profile", {
          nickname,
          avatar_url: uploaded.file_url,
        });
        updateUser(finalUser);
        syncAppSessionSafe();
      }

      this.setData({
        profileSheetVisible: false,
      });
      wx.reLaunch({ url: "/pages/home/index" });
    } catch (err) {
      if (loggedIn) {
        try {
          await logoutCurrent();
        } catch (logoutErr) {
          // Ignore logout cleanup error.
        }
      }
      this.setData({
        errorMsg: err.message || "登录失败，请稍后重试",
      });
    } finally {
      this.setData({ submitting: false });
    }
  },

  noop() {},
});
