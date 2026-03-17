const { getUiMetrics } = require("../../utils/ui-metrics");

Component({
  properties: {
    title: { type: String, value: "" },
    subtitle: { type: String, value: "" },
    showBack: { type: Boolean, value: true },
    backUrl: { type: String, value: "" },
    rightText: { type: String, value: "" },
  },
  data: {
    topBarStyle: "",
  },
  attached() {
    const metrics = getUiMetrics();
    this.setData({
      topBarStyle: `padding-top:${metrics.navContentTop}px;`,
    });
  },
  methods: {
    onBack() {
      if (this.data.backUrl) {
        wx.navigateTo({ url: this.data.backUrl });
        return;
      }
      if (getCurrentPages().length > 1) {
        wx.navigateBack();
      }
    },
    onRightTap() {
      this.triggerEvent("righttap");
    },
  },
});
