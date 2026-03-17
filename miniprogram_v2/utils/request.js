const { getApiBaseUrl, API_PREFIX } = require("../config");
const { getToken, getRefreshToken, getUser, saveSession, clearSession } = require("./session");

let refreshPromise = null;

function classifyError(statusCode, data, errMsg) {
  if (statusCode === 401) {
    return "登录态失效，请重新登录";
  }
  if (statusCode === 0) {
    return "网络不可用，请检查连接";
  }
  if (statusCode >= 500) {
    return "服务器繁忙，请稍后重试";
  }
  if (data && data.detail) {
    return String(data.detail);
  }
  if (errMsg && errMsg.includes("timeout")) {
    return "请求超时，请重试";
  }
  return "请求失败";
}

function buildUrl(path) {
  return `${getApiBaseUrl()}${API_PREFIX}${path}`;
}

function isAuthPath(path) {
  return path.indexOf("/auth/") === 0;
}

function goLogin() {
  wx.reLaunch({ url: "/pages/login/index" });
}

function refreshSession() {
  if (refreshPromise) {
    return refreshPromise;
  }
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    return Promise.reject(new Error("登录态失效，请重新登录"));
  }

  refreshPromise = new Promise((resolve, reject) => {
    wx.request({
      url: buildUrl("/auth/refresh"),
      method: "POST",
      data: { refresh_token: refreshToken },
      timeout: 20000,
      header: {
        "Content-Type": "application/json",
      },
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          saveSession({
            ...res.data,
            user: getUser(),
          });
          resolve(res.data);
          return;
        }
        clearSession();
        reject(new Error(classifyError(res.statusCode, res.data)));
      },
      fail(err) {
        reject(new Error(classifyError(0, null, err.errMsg)));
      },
      complete() {
        refreshPromise = null;
      },
    });
  });

  return refreshPromise;
}

function request(path, options = {}) {
  const token = getToken();
  const retried = !!options._retried;
  const header = {
    "Content-Type": "application/json",
    ...(options.header || {}),
  };
  if (token) {
    header.Authorization = `Bearer ${token}`;
  }

  return new Promise((resolve, reject) => {
    wx.request({
      url: buildUrl(path),
      method: options.method || "GET",
      data: options.data || {},
      timeout: options.timeout || 20000,
      header,
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
          return;
        }

        if (res.statusCode === 401 && !retried && !isAuthPath(path) && getRefreshToken()) {
          refreshSession()
            .then(() => resolve(request(path, { ...options, _retried: true })))
            .catch((err) => {
              clearSession();
              goLogin();
              reject(err);
            });
          return;
        }

        if (res.statusCode === 401 && !isAuthPath(path)) {
          clearSession();
          goLogin();
        }
        reject(new Error(classifyError(res.statusCode, res.data)));
      },
      fail(err) {
        reject(new Error(classifyError(0, null, err.errMsg)));
      },
    });
  });
}

function upload(path, filePath, options = {}) {
  const token = getToken();
  const retried = !!options._retried;
  const header = {
    ...(options.header || {}),
  };
  if (token) {
    header.Authorization = `Bearer ${token}`;
  }

  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: buildUrl(path),
      filePath,
      name: options.name || "file",
      formData: options.formData || {},
      timeout: options.timeout || 30000,
      header,
      success(res) {
        let data = {};
        try {
          data = res.data ? JSON.parse(res.data) : {};
        } catch (err) {
          reject(new Error("上传结果解析失败"));
          return;
        }

        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(data);
          return;
        }

        if (res.statusCode === 401 && !retried && !isAuthPath(path) && getRefreshToken()) {
          refreshSession()
            .then(() => resolve(upload(path, filePath, { ...options, _retried: true })))
            .catch((err) => {
              clearSession();
              goLogin();
              reject(err);
            });
          return;
        }

        if (res.statusCode === 401 && !isAuthPath(path)) {
          clearSession();
          goLogin();
        }
        reject(new Error(classifyError(res.statusCode, data)));
      },
      fail(err) {
        reject(new Error(classifyError(0, null, err.errMsg)));
      },
    });
  });
}

function get(path, options = {}) {
  return request(path, { ...options, method: "GET" });
}

function post(path, data = {}, options = {}) {
  return request(path, { ...options, method: "POST", data });
}

function patch(path, data = {}, options = {}) {
  return request(path, { ...options, method: "PATCH", data });
}

function del(path, options = {}) {
  return request(path, { ...options, method: "DELETE" });
}

module.exports = {
  request,
  upload,
  get,
  post,
  patch,
  del,
  refreshSession,
};
