const { get } = require("./request");

const CACHE_TTL_MS = 5 * 60 * 1000;

let cachedAssets = null;
let cachedAt = 0;

function normalizeAssets(payload = {}) {
  return {
    loginLogoUrl: payload.login_logo_url || "",
    homeHeroUrl: payload.home_hero_url || "",
    shareCardUrl: payload.share_card_url || "",
    reviewLoginIconUrl: payload.review_login_icon_url || "",
  };
}

async function fetchPublicAssets(force = false) {
  const now = Date.now();
  if (!force && cachedAssets && now - cachedAt < CACHE_TTL_MS) {
    return cachedAssets;
  }
  const payload = await get("/public-assets");
  cachedAssets = normalizeAssets(payload);
  cachedAt = now;
  return cachedAssets;
}

function clearPublicAssetsCache() {
  cachedAssets = null;
  cachedAt = 0;
}

module.exports = {
  fetchPublicAssets,
  clearPublicAssetsCache,
};
