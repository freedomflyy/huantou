const { ensureFeatureLogin } = require("../../utils/guard");
const { get } = require("../../utils/request");
const { getUser, isLoggedIn, hasRealProfile } = require("../../utils/session");
const { toAssetCardViewModel, toShowcaseCardViewModel } = require("../../utils/view-models");
const { getStyleTemplates, getShowcaseFallback } = require("../../utils/avatar-studio");
const { getUiMetrics } = require("../../utils/ui-metrics");
const { fetchPublicAssets } = require("../../utils/public-assets");
const { orderShowcaseItems } = require("../../utils/showcase");
const QUICK_ACTIONS = [
  { key: "text-generate", title: "AI 文生图", glyph: "文" },
  { key: "smart-edit", title: "智能修改", glyph: "修" },
  { key: "decorate", title: "贴纸像框", glyph: "框" },
];

const PLAZA_TABS = ["热门", "最新"];
const FALLBACK_CREATORS = ["用户9527", "AvatarMaster", "桃桃同学", "暖光练习生"];

function getFallbackGallery() {
  return getShowcaseFallback().map((item, index) => ({
    ...item,
    creatorName: FALLBACK_CREATORS[index % FALLBACK_CREATORS.length],
    author: "广场精选",
  }));
}

function attachTemplateImages(templates, gallery) {
  const list = gallery && gallery.length ? gallery : getFallbackGallery();
  return templates.slice(0, 6).map((item, index) => ({
    ...item,
    imageUrl: list[index % list.length] ? list[index % list.length].imageUrl || "" : "",
  }));
}

function mapHomeStyles(materialItems, fallbackTemplates) {
  return materialItems.map((item, index) => {
    const fallback = fallbackTemplates[index % fallbackTemplates.length] || fallbackTemplates[0] || {};
    return {
      id: item.id,
      name: item.title,
      desc: item.subtitle || fallback.desc || "",
      badge: item.badge || fallback.badge || "",
      coverClass: fallback.coverClass || "cover-cream",
      imageUrl: item.file_url || "",
    };
  });
}

function decorateGallery(items) {
  const source = items && items.length ? items : getFallbackGallery();
  return source.map((item, index) => ({
    ...item,
    creatorName: item.creatorName || FALLBACK_CREATORS[index % FALLBACK_CREATORS.length],
  }));
}

function buildHeroSlides(templates, heroImageUrl = "") {
  const styleSlides = (templates || []).slice(0, 3).map((item) => ({
    id: `hero-${item.id}`,
    title: item.name,
    desc: item.desc,
    badge: item.badge || "人气风格",
    imageUrl: item.imageUrl || "",
    coverClass: item.coverClass || "cover-cream",
    ctaText: "立即创建",
    styleName: item.name,
  }));

  return [
    {
      id: "hero-style-transfer",
      title: "风格迁移",
      desc: "用50多款全新艺术模板转换你的照片。",
      badge: "新品上市",
      imageUrl: heroImageUrl,
      coverClass: "cover-night",
      ctaText: "立即创建",
      styleName: "",
    },
    ...styleSlides,
  ];
}

Page({
  data: {
    user: {
      nickname: "创作者",
    },
    quickActions: QUICK_ACTIONS,
    plazaTabs: PLAZA_TABS,
    currentPlazaTab: PLAZA_TABS[0],
    styleTemplates: attachTemplateImages(getStyleTemplates(), []),
    heroSlides: buildHeroSlides(attachTemplateImages(getStyleTemplates(), []), ""),
    currentHeroIndex: 0,
    gallery: getFallbackGallery(),
    displayGallery: getFallbackGallery().slice(0, 4),
    headerStyle: "",
    headerSpacerStyle: "",
    brandingLogoUrl: "",
    heroImageUrl: "",
  },

  onLoad() {
    const metrics = getUiMetrics();
    this.setData({
      headerStyle: `padding-top:${metrics.navContentTop}px;`,
      headerSpacerStyle: `height:${metrics.homeSpacerHeight}px;`,
    });
  },

  async onShow() {
    await this.loadData();
  },

  setDisplayGallery(tab = this.data.currentPlazaTab, gallery = this.data.gallery) {
    const list = orderShowcaseItems(gallery, tab);
    this.setData({
      currentPlazaTab: tab,
      displayGallery: list.slice(0, 4),
    });
  },

  async loadData() {
    const user = getUser() || {};
    const fallbackGallery = getFallbackGallery();
    const fallbackTemplates = getStyleTemplates();
    const loginReady = isLoggedIn() && hasRealProfile();
    let gallery = fallbackGallery;
    let styleTemplates = attachTemplateImages(fallbackTemplates, fallbackGallery);
    let publicAssets = null;

    this.setData({
      user: {
        nickname: user.nickname || "游客",
      },
    });

    try {
      const showcaseRes = await get("/showcase?limit=24");
      const galleryItems = decorateGallery((showcaseRes.items || []).map(toShowcaseCardViewModel));
      if (galleryItems.length) {
        gallery = galleryItems;
        styleTemplates = attachTemplateImages(fallbackTemplates, galleryItems);
      } else if (loginReady) {
        const [assetsRes, tasksRes] = await Promise.all([
          get("/assets?limit=12"),
          get("/tasks?limit=50"),
        ]);
        const taskMap = {};
        (tasksRes.items || []).forEach((task) => {
          taskMap[task.id] = task;
        });
        const assetGallery = decorateGallery((assetsRes.items || []).map((item) => toAssetCardViewModel(item, taskMap)));
        if (assetGallery.length) {
          gallery = assetGallery;
          styleTemplates = attachTemplateImages(fallbackTemplates, assetGallery);
        }
      }
    } catch (err) {
      if (loginReady) {
        try {
        const [assetsRes, tasksRes] = await Promise.all([
          get("/assets?limit=12"),
          get("/tasks?limit=50"),
        ]);
        const taskMap = {};
        (tasksRes.items || []).forEach((task) => {
          taskMap[task.id] = task;
        });
        const assetGallery = decorateGallery((assetsRes.items || []).map((item) => toAssetCardViewModel(item, taskMap)));
        if (assetGallery.length) {
          gallery = assetGallery;
          styleTemplates = attachTemplateImages(fallbackTemplates, assetGallery);
        }
        } catch (nestedErr) {
          // Keep fallback gallery.
        }
      }
    }

    try {
      publicAssets = await fetchPublicAssets();
    } catch (err) {
      // Keep static-only fallback when the public asset endpoint is unavailable.
    }

    try {
      const materialsRes = await get("/materials");
      if (materialsRes.home_styles && materialsRes.home_styles.length) {
        styleTemplates = mapHomeStyles(materialsRes.home_styles, fallbackTemplates);
      }
    } catch (err) {
      // Keep template fallback when materials are unavailable.
    }

    this.setData({
      gallery,
      styleTemplates,
      heroSlides: buildHeroSlides(styleTemplates, (publicAssets && publicAssets.homeHeroUrl) || ""),
      heroImageUrl: (publicAssets && publicAssets.homeHeroUrl) || "",
      brandingLogoUrl: (publicAssets && publicAssets.loginLogoUrl) || "",
    });
    this.setDisplayGallery(this.data.currentPlazaTab, gallery);
  },

  async goStyleTransfer(style = "") {
    const ok = await ensureFeatureLogin("登录后才可以开始头像生成");
    if (!ok) return;
    const url = style
      ? `/pages/image-reference/index?style=${encodeURIComponent(style)}`
      : "/pages/image-reference/index";
    wx.navigateTo({ url });
  },

  async goTextGenerate() {
    const ok = await ensureFeatureLogin("登录后才可以开始头像生成");
    if (!ok) return;
    wx.navigateTo({ url: "/pages/text-generate/index" });
  },

  goSquare() {
    wx.reLaunch({ url: "/pages/square/index" });
  },

  async goProfile() {
    const ok = await ensureFeatureLogin("登录后查看你的作品与积分");
    if (!ok) return;
    wx.reLaunch({ url: "/pages/profile/index" });
  },

  async onQuickActionTap(e) {
    const key = e.currentTarget.dataset.key;
    const routeMap = {
      "text-generate": "/pages/text-generate/index",
      "smart-edit": "/pages/image-edit/index",
      decorate: "/pages/avatar-decorate/index",
    };
    if (!routeMap[key]) return;
    if (key !== "decorate") {
      const ok = await ensureFeatureLogin("登录后才可以使用创作功能");
      if (!ok) return;
    }
    wx.navigateTo({ url: routeMap[key] });
  },

  onHeroChange(e) {
    this.setData({
      currentHeroIndex: e.detail.current || 0,
    });
  },

  async onHeroSlideTap(e) {
    const style = e.currentTarget.dataset.style || "";
    await this.goStyleTransfer(style);
  },

  async onHeroCtaTap(e) {
    const style = e.currentTarget.dataset.style || "";
    await this.goStyleTransfer(style);
  },

  async onTemplateTap(e) {
    const style = e.currentTarget.dataset.style;
    if (!style) {
      await this.goStyleTransfer();
      return;
    }
    await this.goStyleTransfer(style);
  },

  onPlazaTabTap(e) {
    const tab = e.currentTarget.dataset.tab;
    if (!tab) return;
    this.setDisplayGallery(tab, this.data.gallery);
  },

  async onGalleryTap(e) {
    const taskId = e.currentTarget.dataset.taskid;
    const style = e.currentTarget.dataset.style || "";
    if (taskId) {
      wx.navigateTo({ url: `/pages/result/index?taskId=${encodeURIComponent(taskId)}` });
      return;
    }
    if (style) {
      await this.goStyleTransfer(style);
      return;
    }
    this.goSquare();
  },
});
