const { ensureLogin } = require("../../utils/guard");
const { get, post, upload, patch } = require("../../utils/request");
const { getUser, updateUser } = require("../../utils/session");
const { getUiMetrics } = require("../../utils/ui-metrics");
const { fetchPublicAssets } = require("../../utils/public-assets");

Page({
  data: {
    user: {
      nickname: "微信用户",
      signature: "把日常瞬间，变成温柔头像。",
      pointsBalance: 0,
      works: 0,
      favorites: 0,
      avatarText: "桃",
      avatarUrl: "",
    },
    menus: [
      { key: "assets", glyph: "作", title: "我的作品", note: "从这里进入作品集和收藏" },
      { key: "history", glyph: "史", title: "创作记录", note: "查看每一次生成过程" },
      { key: "points", glyph: "会", title: "会员中心", note: "积分、权益和套餐" },
      { key: "about", glyph: "关于", title: "关于幻头", note: "使用帮助与产品说明" },
    ],
    pageTopStyle: "",
    inviteRewardPoints: 100,
    inviteStatusText: "分享成功即可获得 100 积分",
    inviteStatusTone: "idle",
    shareCardUrl: "",
    inviteRewardClaiming: false,
    profileEditorVisible: false,
    profileSaving: false,
    profileDraftNickname: "",
    profileDraftAvatarUrl: "",
    profileDraftAvatarPath: "",
  },

  onLoad() {
    const metrics = getUiMetrics();
    this.setData({
      pageTopStyle: `padding-top:${metrics.pageTopInset}px;`,
    });
  },

  async onShow() {
    const ok = await ensureLogin();
    if (!ok) return;
    await this.loadData();
  },

  syncDraftProfile(user) {
    this.setData({
      profileDraftNickname: user.nickname || "",
      profileDraftAvatarUrl: user.avatarUrl || "",
      profileDraftAvatarPath: "",
    });
  },

  async loadData() {
    const baseUser = getUser() || {};
    try {
      const [balanceRes, assetsRes, favoriteRes, publicAssets] = await Promise.all([
        get("/points/balance"),
        get("/assets?limit=1"),
        get("/assets/favorites?limit=1"),
        fetchPublicAssets().catch(() => null),
      ]);
      const user = {
        nickname: baseUser.nickname || "微信用户",
        signature: "把日常瞬间，变成温柔头像。",
        pointsBalance: balanceRes.points_balance || 0,
        works: assetsRes.total || 0,
        favorites: favoriteRes.total || 0,
        avatarText: (baseUser.nickname || "桃").slice(0, 1),
        avatarUrl: baseUser.avatar_url || "",
      };
      updateUser({
        ...baseUser,
        points_balance: balanceRes.points_balance || 0,
      });
      this.setData({
        user,
        inviteRewardPoints: (balanceRes.rules && balanceRes.rules.invite_share_bonus) || 100,
        inviteStatusText: `分享成功即可获得 ${(balanceRes.rules && balanceRes.rules.invite_share_bonus) || 100} 积分`,
        inviteStatusTone: "idle",
        shareCardUrl: (publicAssets && publicAssets.shareCardUrl) || "",
      });
      this.syncDraftProfile(user);
    } catch (err) {
      const user = {
        nickname: baseUser.nickname || "微信用户",
        signature: "把日常瞬间，变成温柔头像。",
        pointsBalance: baseUser.points_balance || 0,
        works: 0,
        favorites: 0,
        avatarText: (baseUser.nickname || "桃").slice(0, 1),
        avatarUrl: baseUser.avatar_url || "",
      };
      this.setData({
        user,
        inviteRewardPoints: 100,
        inviteStatusText: "分享成功即可获得 100 积分",
        inviteStatusTone: "idle",
        shareCardUrl: "",
      });
      this.syncDraftProfile(user);
    }
  },

  openProfileEditor() {
    const user = this.data.user || {};
    this.setData({
      profileEditorVisible: true,
      profileDraftNickname: user.nickname || "",
      profileDraftAvatarUrl: user.avatarUrl || "",
      profileDraftAvatarPath: "",
    });
  },

  closeProfileEditor() {
    if (this.data.profileSaving) return;
    this.setData({
      profileEditorVisible: false,
    });
  },

  onProfileNicknameInput(e) {
    this.setData({
      profileDraftNickname: (e.detail.value || "").trim(),
    });
  },

  onChooseProfileAvatar(e) {
    const avatarPath = (e.detail && e.detail.avatarUrl) || "";
    if (!avatarPath) return;
    this.setData({
      profileDraftAvatarUrl: avatarPath,
      profileDraftAvatarPath: avatarPath,
    });
  },

  async saveProfileEditor() {
    if (this.data.profileSaving) return;
    const nickname = (this.data.profileDraftNickname || "").trim();
    const avatarUrl = (this.data.profileDraftAvatarUrl || "").trim();
    const avatarPath = (this.data.profileDraftAvatarPath || "").trim();
    const baseUser = getUser() || {};

    if (!nickname) {
      wx.showToast({
        title: "请先填写昵称",
        icon: "none",
      });
      return;
    }

    if (!avatarUrl) {
      wx.showToast({
        title: "请先选择头像",
        icon: "none",
      });
      return;
    }

    try {
      this.setData({ profileSaving: true });
      let finalAvatarUrl = avatarUrl;
      if (avatarPath) {
        const uploaded = await upload("/assets/upload", avatarPath, { name: "file" });
        finalAvatarUrl = uploaded.file_url || avatarUrl;
      }

      const updated = await patch("/auth/profile", {
        nickname,
        avatar_url: finalAvatarUrl,
      });

      updateUser({
        ...baseUser,
        ...updated,
      });
      this.setData({
        profileEditorVisible: false,
      });
      await this.loadData();
      wx.showToast({
        title: "资料已更新",
        icon: "success",
      });
    } catch (err) {
      wx.showToast({
        title: err.message || "资料更新失败",
        icon: "none",
      });
    } finally {
      this.setData({ profileSaving: false });
    }
  },

  onMenuTap(e) {
    const key = e.currentTarget.dataset.key;
    const map = {
      assets: "/pages/assets/index",
      history: "/pages/history/index",
      points: "/pages/points/index",
      about: "/pages/service/index?type=about",
    };
    const url = map[key];
    if (!url) return;
    wx.navigateTo({ url });
  },

  async claimInviteReward() {
    if (this.data.inviteRewardClaiming) return;
    try {
      this.setData({
        inviteRewardClaiming: true,
        inviteStatusText: "分享成功，正在领取奖励...",
        inviteStatusTone: "loading",
      });
      const res = await post("/points/invite-share");
      await this.loadData();
      this.setData({
        inviteStatusText: res.granted ? `分享奖励已到账，获得 ${res.reward_points} 积分` : "今天的分享奖励已经领过了",
        inviteStatusTone: res.granted ? "success" : "idle",
      });
      wx.showToast({
        title: res.granted ? `已获得${res.reward_points}积分` : "今日分享奖励已领取",
        icon: "none",
      });
    } catch (err) {
      this.setData({
        inviteStatusText: `奖励领取失败：${err.message || "请稍后重试"}`,
        inviteStatusTone: "error",
      });
      wx.showToast({
        title: err.message || "奖励领取失败",
        icon: "none",
      });
    } finally {
      this.setData({
        inviteRewardClaiming: false,
      });
    }
  },

  queueInviteReward() {
    if (this.data.inviteRewardClaiming) return;
    this.setData({
      inviteStatusText: "已发起分享，正在领取奖励...",
      inviteStatusTone: "loading",
    });
    setTimeout(() => {
      this.claimInviteReward();
    }, 0);
  },

  onInviteTap() {
    this.setData({
      inviteStatusText: `发起一次分享后会自动领取 ${this.data.inviteRewardPoints || 100} 积分`,
      inviteStatusTone: "hint",
    });
  },

  onShareAppMessage(res) {
    const baseUser = getUser() || {};
    const path = baseUser.id
      ? `/pages/login/index?scene=invite&inviter=${baseUser.id}`
      : "/pages/login/index?scene=invite";
    const sharePayload = {
      title: "我在幻头做了很多好看的头像，来一起试试",
      path,
    };
    if (this.data.shareCardUrl) {
      sharePayload.imageUrl = this.data.shareCardUrl;
    }
    this.queueInviteReward();
    return sharePayload;
  },

  onShareTimeline() {
    const baseUser = getUser() || {};
    const query = baseUser.id ? `scene=invite&inviter=${baseUser.id}` : "scene=invite";
    const timelinePayload = {
      title: "来幻头，一起生成你的专属头像",
      query,
    };
    if (this.data.shareCardUrl) {
      timelinePayload.imageUrl = this.data.shareCardUrl;
    }
    this.queueInviteReward();
    return timelinePayload;
  },

  noop() {},
});
