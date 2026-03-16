const API_ENV = "tunnel";
const API_HOSTS = {
  local: "http://127.0.0.1:8000",
  tunnel: "https://828md02534xr.vicp.fun",
};

const API_BASE_URL = API_HOSTS[API_ENV] || API_HOSTS.tunnel;
const API_PREFIX = "/api/v1";
const ENABLE_DEMO_MODE = false;

module.exports = {
  API_ENV,
  API_HOSTS,
  API_BASE_URL,
  API_PREFIX,
  ENABLE_DEMO_MODE,
};
