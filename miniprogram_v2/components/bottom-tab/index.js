const tabs = [
  { key: "home", text: "首页", glyph: "首", url: "/pages/home/index" },
  { key: "create", text: "创作", glyph: "＋", url: "/pages/create-menu/index", primary: true },
  { key: "assets", text: "作品集", glyph: "集", url: "/pages/assets/index" },
  { key: "profile", text: "我的", glyph: "我", url: "/pages/profile/index" },
];

Component({
  properties: {
    current: { type: String, value: "home" },
  },
  data: {
    tabs,
  },
  methods: {
    onTabTap(e) {
      const key = e.currentTarget.dataset.key;
      const tab = tabs.find((item) => item.key === key);
      if (!tab) return;
      wx.reLaunch({ url: tab.url });
    },
  },
});
