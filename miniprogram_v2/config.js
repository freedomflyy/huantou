const API_ENV = "tunnel";
const API_HOSTS = {
  local: "http://127.0.0.1:8000",
  tunnel: "https://828md02534xr.vicp.fun",
};

function getApiBaseUrl() {
  try {
    const info = wx.getSystemInfoSync ? wx.getSystemInfoSync() : null;
    if (info && info.platform === "devtools") {
      return API_HOSTS.local;
    }
  } catch (err) {
    // Ignore runtime detection failures and fall back to the configured host.
  }
  return API_HOSTS[API_ENV] || API_HOSTS.tunnel;
}

const API_BASE_URL = getApiBaseUrl();
const API_PREFIX = "/api/v1";
const ENABLE_DEMO_MODE = false;

module.exports = {
  API_ENV,
  API_HOSTS,
  API_BASE_URL,
  getApiBaseUrl,
  API_PREFIX,
  ENABLE_DEMO_MODE,
};
