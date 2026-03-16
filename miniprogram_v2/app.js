const { getToken, getUser } = require("./utils/session");

App({
  globalData: {
    token: "",
    user: null,
    selectedAssetTarget: "",
  },

  onLaunch() {
    this.syncSession();
  },

  syncSession() {
    this.globalData.token = getToken();
    this.globalData.user = getUser() || null;
  },
});
