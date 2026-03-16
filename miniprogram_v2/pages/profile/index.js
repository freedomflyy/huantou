const { ensureLogin } = require("../../utils/guard");
const { get } = require("../../utils/request");
const { getUser, updateUser } = require("../../utils/session");

Page({
  data: {
    user: {
      nickname: "微信用户",
      signature: "把日常瞬间，变成温柔头像。",
      pointsBalance: 0,
      works: 0,
      favorites: 0,
    },
    menus: [
      { key: "assets", glyph: "作", title: "我的作品", note: "生成记录和收藏都放在这里" },
      { key: "history", glyph: "史", title: "创作记录", note: "查看每一次生成过程" },
      { key: "points", glyph: "会", title: "会员中心", note: "积分、权益和套餐" },
      { key: "about", glyph: "关于", title: "关于幻头", note: "使用帮助与产品说明" },
    ],
  },

  async onShow() {
    const ok = await ensureLogin();
    if (!ok) return;
    await this.loadData();
  },

  async loadData() {
    const baseUser = getUser() || {};
    try {
      const [balanceRes, assetsRes, favoriteRes] = await Promise.all([
        get("/points/balance"),
        get("/assets?limit=1"),
        get("/assets/favorites?limit=1"),
      ]);
      const user = {
        nickname: baseUser.nickname || "微信用户",
        signature: "把日常瞬间，变成温柔头像。",
        pointsBalance: balanceRes.points_balance || 0,
        works: assetsRes.total || 0,
        favorites: favoriteRes.total || 0,
      };
      updateUser({
        ...baseUser,
        points_balance: balanceRes.points_balance || 0,
      });
      this.setData({ user });
    } catch (err) {
      this.setData({
        user: {
          nickname: baseUser.nickname || "微信用户",
          signature: "把日常瞬间，变成温柔头像。",
          pointsBalance: baseUser.points_balance || 0,
          works: 0,
          favorites: 0,
        },
      });
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

  goOnboarding() {
    wx.navigateTo({ url: "/pages/login/index" });
  },
});
