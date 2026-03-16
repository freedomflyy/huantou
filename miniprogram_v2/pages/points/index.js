const { ensureLogin } = require("../../utils/guard");
const { get, post } = require("../../utils/request");
const { formatDateLabel } = require("../../utils/view-models");

const POINT_PACKAGES = [
  { id: "welcome", name: "新人礼包", points: 500, bonus: 100, price: "¥9.9", highlight: true },
  { id: "basic", name: "基础版", points: 1200, bonus: 180, price: "¥19.9" },
  { id: "pro", name: "进阶版", points: 3000, bonus: 600, price: "¥49.9" },
];

function ledgerTitle(changeType, reason) {
  if (changeType === "admin_adjust" && reason && reason.indexOf("redeem_code:") === 0) {
    return "激活码兑换";
  }
  const map = {
    signup_bonus: "新人奖励",
    daily_bonus: "每日签到",
    generation_cost: "创作消耗",
    refund: "失败返还",
    admin_adjust: "后台调整",
  };
  return map[changeType] || "积分变动";
}

function ledgerSummary(changeType, reason, operator) {
  if (changeType === "admin_adjust" && reason && reason.indexOf("redeem_code:") === 0) {
    return "激活码兑换奖励";
  }
  return reason || operator || "系统记录";
}

function isSameDay(value) {
  if (!value) return false;
  const date = new Date(value);
  const now = new Date();
  if (Number.isNaN(date.getTime())) return false;
  return (
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()
  );
}

Page({
  data: {
    pointsBalance: 0,
    rules: {},
    ledgers: [],
    checkInToday: false,
    checkInReward: 0,
    checkInTimeLabel: "",
    checkInLoading: false,
    redeemCode: "",
    redeemLoading: false,
    packages: POINT_PACKAGES,
  },

  async onShow() {
    const ok = await ensureLogin();
    if (!ok) return;
    await this.loadData();
  },

  async loadData() {
    try {
      const [balanceRes, ledgersRes] = await Promise.all([
        get("/points/balance"),
        get("/points/ledgers?limit=50"),
      ]);
      const ledgers = (ledgersRes.items || []).map((item) => ({
        id: item.id,
        changeType: item.change_type,
        createdAt: item.created_at,
        title: ledgerTitle(item.change_type, item.reason),
        reason: ledgerSummary(item.change_type, item.reason, item.operator),
        delta: item.delta,
        time: formatDateLabel(item.created_at),
      }));
      const todayCheckIn = ledgers.find((item) => item.changeType === "daily_bonus" && isSameDay(item.createdAt));
      this.setData({
        pointsBalance: balanceRes.points_balance || 0,
        rules: balanceRes.rules || {},
        ledgers,
        checkInToday: !!todayCheckIn,
        checkInReward: (balanceRes.rules && balanceRes.rules.daily_bonus) || 0,
        checkInTimeLabel: todayCheckIn ? todayCheckIn.time : "",
      });
    } catch (err) {
      wx.showToast({
        title: err.message || "积分信息加载失败",
        icon: "none",
      });
    }
  },

  async onSignTap() {
    if (this.data.checkInLoading) return;
    if (this.data.checkInToday) {
      wx.showToast({ title: "今天已经签到过了", icon: "none" });
      return;
    }
    this.setData({ checkInLoading: true });
    try {
      const res = await post("/points/check-in", {});
      wx.showToast({
        title: res.granted ? `签到成功 +${res.reward_points}` : "今天已经签到过了",
        icon: "none",
      });
      await this.loadData();
    } catch (err) {
      wx.showToast({
        title: err.message || "签到失败，请稍后重试",
        icon: "none",
      });
    } finally {
      this.setData({ checkInLoading: false });
    }
  },

  onRedeemCodeInput(e) {
    this.setData({
      redeemCode: (e.detail && e.detail.value) || "",
    });
  },

  async onRedeemTap() {
    const code = (this.data.redeemCode || "").trim();
    if (this.data.redeemLoading || !code) return;
    this.setData({ redeemLoading: true });
    try {
      const res = await post("/points/redeem-code", { code });
      wx.showToast({
        title: res.granted ? `兑换成功 +${res.reward_points}` : "这个账号已经兑换过了",
        icon: "none",
      });
      this.setData({ redeemCode: "" });
      await this.loadData();
    } catch (err) {
      wx.showToast({
        title: err.message || "兑换失败，请稍后重试",
        icon: "none",
      });
    } finally {
      this.setData({ redeemLoading: false });
    }
  },
});
