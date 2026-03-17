const { ensureLogin } = require("../../utils/guard");
const { get, post } = require("../../utils/request");
const { normalizeTaskCreatePayload } = require("../../utils/view-models");
const { getTextStyleOptions, getTextPromptSamples } = require("../../utils/avatar-studio");
const { getUiMetrics } = require("../../utils/ui-metrics");

const DEFAULT_RULES = {
  txt2img_cost: 20,
  img2img_cost: 18,
  style_transfer_cost: 22,
};

const PROMPT_TAGS = [
  {
    id: "fresh",
    label: "小清新",
    prompt: "小清新头像，柔和自然光，背景干净，适合作为微信头像",
    styleName: "无",
  },
  {
    id: "k-style",
    label: "韩系风格",
    prompt: "韩系质感头像，清透妆面，柔光人像，适合作为社交头像",
    styleName: "无",
  },
  {
    id: "3d",
    label: "3D Q版",
    prompt: "3D Q版头像，圆润可爱，人物居中，奶油光影",
    styleName: "3D萌趣",
  },
  {
    id: "cyber",
    label: "赛博朋克",
    prompt: "赛博朋克头像，霓虹氛围，未来感强，人物特写",
    styleName: "赛博风",
  },
  {
    id: "healing",
    label: "治愈插画",
    prompt: "治愈系插画头像，暖色调，柔和笔触，适合作为微信头像",
    styleName: "清新插画",
  },
];

const GENDER_OPTIONS = ["中性", "男生", "女生"];
const HAIR_COLORS = [
  { value: "自然黑", color: "#2d2a28" },
  { value: "栗棕", color: "#7b4b32" },
  { value: "亚麻金", color: "#d6ae63" },
  { value: "雾粉", color: "#df8ea6" },
];

function getFallbackStyleOptions() {
  return getTextStyleOptions().map((item) => ({
    ...item,
    imageUrl: "",
    isNone: item.name === "无",
  }));
}

function mapMaterialStyles(items, fallback) {
  const list = fallback && fallback.length ? fallback : getFallbackStyleOptions();
  const noneOption = list.find((item) => item.isNone) || {
    id: "none",
    name: "无",
    desc: "不额外套风格模板",
    coverClass: "cover-cream",
    imageUrl: "",
    isNone: true,
  };
  const mapped = (items || []).map((item, index) => {
    const base = list[(index % Math.max(list.length - 1, 1)) + 1] || list[0] || {};
    return {
      id: item.id,
      name: item.title,
      desc: item.subtitle || base.desc || "",
      coverClass: base.coverClass || "cover-cream",
      imageUrl: item.file_url || "",
      isNone: false,
    };
  });
  return [noneOption].concat(mapped);
}

function mapRecentHistory(assets, tasks) {
  const taskMap = {};
  (tasks || []).forEach((task) => {
    taskMap[task.id] = task;
  });
  return (assets || [])
    .filter((asset) => {
      if (!asset.source_task_id) return false;
      const task = taskMap[asset.source_task_id];
      return task && task.task_type === "txt2img";
    })
    .sort((a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime())
    .slice(0, 4)
    .map((asset, index) => ({
      id: asset.id,
      taskId: asset.source_task_id,
      imageUrl: asset.thumbnail_url || asset.file_url,
      fileUrl: asset.file_url,
      title: `候选图 ${index + 1}`,
    }));
}

function downloadFile(url) {
  return new Promise((resolve, reject) => {
    wx.downloadFile({
      url,
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300 && res.tempFilePath) {
          resolve(res.tempFilePath);
          return;
        }
        reject(new Error("图片下载失败"));
      },
      fail(err) {
        reject(new Error((err && err.errMsg) || "图片下载失败"));
      },
    });
  });
}

function saveToAlbum(filePath) {
  return new Promise((resolve, reject) => {
    wx.saveImageToPhotosAlbum({
      filePath,
      success() {
        resolve();
      },
      fail(err) {
        reject(err || new Error("保存失败"));
      },
    });
  });
}

Page({
  data: {
    prompt: "",
    negativePrompt: "",
    promptTags: PROMPT_TAGS,
    styleOptions: getFallbackStyleOptions(),
    selectedStyle: "无",
    selectedOutputCount: 4,
    outputCountOptions: [
      { value: 1, label: "1 张" },
      { value: 2, label: "2 张" },
      { value: 4, label: "4 张" },
    ],
    promptSamples: getTextPromptSamples(),
    inspirationText: getTextPromptSamples()[0].prompt,
    genderOptions: GENDER_OPTIONS,
    selectedGender: "中性",
    hairColors: HAIR_COLORS,
    selectedHairColor: "",
    characterExpanded: false,
    advancedExpanded: false,
    recentHistory: [],
    selectedHistoryId: "",
    pointsBalance: 0,
    rules: DEFAULT_RULES,
    submitting: false,
    errorMsg: "",
    navStyle: "",
  },

  onLoad(query) {
    const metrics = getUiMetrics();
    this.setData({
      navStyle: `padding-top:${metrics.navContentTop}px;`,
    });
    if (query && query.style) {
      this.setData({ selectedStyle: decodeURIComponent(query.style) });
    }
  },

  async onShow() {
    const ok = await ensureLogin();
    if (!ok) return;
    await this.loadPageData();
  },

  async loadPageData() {
    const fallbackStyles = getFallbackStyleOptions();
    const results = await Promise.allSettled([
      get("/points/balance"),
      get("/materials"),
      get("/tasks?limit=60"),
      get("/assets?limit=30"),
    ]);

    const balanceRes = results[0].status === "fulfilled" ? results[0].value : null;
    const materialsRes = results[1].status === "fulfilled" ? results[1].value : null;
    const tasksRes = results[2].status === "fulfilled" ? results[2].value : null;
    const assetsRes = results[3].status === "fulfilled" ? results[3].value : null;

    const styleOptions = materialsRes && materialsRes.home_styles && materialsRes.home_styles.length
      ? mapMaterialStyles(materialsRes.home_styles, fallbackStyles)
      : fallbackStyles;

    const recentHistory = mapRecentHistory(
      assetsRes && assetsRes.items ? assetsRes.items : [],
      tasksRes && tasksRes.items ? tasksRes.items : []
    );

    const currentSelected = recentHistory.find((item) => item.id === this.data.selectedHistoryId);

    this.setData({
      styleOptions,
      recentHistory,
      selectedHistoryId: currentSelected ? currentSelected.id : (recentHistory[0] ? recentHistory[0].id : ""),
      rules: (balanceRes && balanceRes.rules) || DEFAULT_RULES,
      pointsBalance: (balanceRes && balanceRes.points_balance) || 0,
    });
  },

  onBack() {
    if (getCurrentPages().length > 1) {
      wx.navigateBack();
      return;
    }
    wx.reLaunch({ url: "/pages/create-menu/index" });
  },

  onPromptInput(e) {
    this.setData({ prompt: e.detail.value });
  },

  onNegativePromptInput(e) {
    this.setData({ negativePrompt: e.detail.value });
  },

  onPromptTagTap(e) {
    const id = e.currentTarget.dataset.id;
    const target = PROMPT_TAGS.find((item) => item.id === id);
    if (!target) return;
    this.setData({
      prompt: target.prompt,
      inspirationText: target.prompt,
      selectedStyle: target.styleName || "无",
    });
  },

  onStyleTap(e) {
    const style = e.currentTarget.dataset.style;
    if (!style) return;
    this.setData({ selectedStyle: style });
  },

  toggleCharacterPanel() {
    this.setData({ characterExpanded: !this.data.characterExpanded });
  },

  toggleAdvancedPanel() {
    this.setData({ advancedExpanded: !this.data.advancedExpanded });
  },

  onGenderTap(e) {
    const gender = e.currentTarget.dataset.gender;
    if (!gender) return;
    this.setData({ selectedGender: gender });
  },

  onHairColorTap(e) {
    const color = e.currentTarget.dataset.color;
    if (!color) return;
    this.setData({
      selectedHairColor: this.data.selectedHairColor === color ? "" : color,
    });
  },

  onOutputCountTap(e) {
    const count = Number(e.currentTarget.dataset.count || 0);
    if (!count) return;
    this.setData({ selectedOutputCount: count });
  },

  onHistoryTap(e) {
    const id = e.currentTarget.dataset.id;
    if (!id) return;
    this.setData({ selectedHistoryId: id });
  },

  findSelectedHistory() {
    const { selectedHistoryId, recentHistory } = this.data;
    return recentHistory.find((item) => item.id === selectedHistoryId) || recentHistory[0] || null;
  },

  goAllHistory() {
    wx.navigateTo({ url: "/pages/assets/index" });
  },

  async onSaveSelected() {
    const target = this.findSelectedHistory();
    if (!target || !target.fileUrl) {
      wx.showToast({ title: "请先选择一张历史头像", icon: "none" });
      return;
    }

    wx.showLoading({ title: "正在保存" });
    try {
      const tempFilePath = await downloadFile(target.fileUrl);
      await saveToAlbum(tempFilePath);
      wx.showToast({ title: "已保存到相册", icon: "success" });
    } catch (err) {
      const msg = (err && err.errMsg) || err.message || "";
      if (msg.indexOf("auth deny") >= 0 || msg.indexOf("scope.writePhotosAlbum") >= 0) {
        wx.showModal({
          title: "需要相册权限",
          content: "保存头像到相册需要开启相册权限，请在设置中允许后重试。",
          confirmText: "去设置",
          success: (res) => {
            if (res.confirm) {
              wx.openSetting();
            }
          },
        });
      } else {
        wx.showToast({ title: err.message || "保存失败", icon: "none" });
      }
    } finally {
      wx.hideLoading();
    }
  },

  onDeepEdit() {
    const target = this.findSelectedHistory();
    if (!target || !target.fileUrl) {
      wx.showToast({ title: "请先选择一张历史头像", icon: "none" });
      return;
    }
    wx.navigateTo({
      url: `/pages/image-edit/index?preset=${encodeURIComponent(target.fileUrl)}`,
    });
  },

  buildPrompt() {
    const basePrompt = (this.data.prompt || this.data.inspirationText || "").trim();
    const parts = [];
    if (basePrompt) {
      parts.push(basePrompt);
    }
    if (this.data.selectedGender === "男生") {
      parts.push("人物偏男生气质");
    } else if (this.data.selectedGender === "女生") {
      parts.push("人物偏女生气质");
    }
    if (this.data.selectedHairColor) {
      parts.push(`${this.data.selectedHairColor}发色`);
    }
    return parts.join("，");
  },

  async onCreateTask() {
    if (this.data.submitting) return;
    const prompt = this.buildPrompt();
    if (!prompt) {
      this.setData({ errorMsg: "请先输入一句描述" });
      return;
    }

    this.setData({ submitting: true, errorMsg: "" });
    try {
      const payload = normalizeTaskCreatePayload({
        task_type: "txt2img",
        prompt,
        negative_prompt: this.data.negativePrompt,
        params: {
          style_name: this.data.selectedStyle === "无" ? undefined : this.data.selectedStyle,
          ratio: "1:1",
          output_count: this.data.selectedOutputCount,
        },
      });
      const created = await post("/tasks", payload);
      wx.navigateTo({
        url: `/pages/loading/index?taskId=${encodeURIComponent(created.id)}&from=text-generate`,
      });
    } catch (err) {
      this.setData({ errorMsg: err.message || "任务创建失败" });
    } finally {
      this.setData({ submitting: false });
    }
  },
});
