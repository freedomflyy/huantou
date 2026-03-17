const { ensureLogin } = require("../../utils/guard");
const { get, post, upload } = require("../../utils/request");
const { normalizeTaskCreatePayload } = require("../../utils/view-models");
const { getAdvancedFeatures } = require("../../utils/avatar-studio");
const { getUiMetrics } = require("../../utils/ui-metrics");

const DEFAULT_RULES = {
  txt2img_cost: 20,
  img2img_cost: 18,
  style_transfer_cost: 22,
};

const QUICK_ACTIONS = [
  {
    key: "hair",
    title: "更换发型",
    glyph: "发",
    feature: "smart-edit",
    preset: "修整发丝",
    prompt: "换成更适合头像的发型，发丝更利落自然",
  },
  {
    key: "expression",
    title: "切换表情",
    glyph: "笑",
    feature: "smart-edit",
    preset: "眼神更聚焦",
    prompt: "让表情更自然亲和，笑容更有感染力",
  },
  {
    key: "background",
    title: "更换背景",
    glyph: "景",
    feature: "background-replace",
    preset: "奶油色背景",
    prompt: "替换成更适合作为头像的干净背景",
  },
  {
    key: "glasses",
    title: "添加眼镜",
    glyph: "镜",
    feature: "smart-edit",
    preset: "自然补光",
    prompt: "添加一副适合脸型的眼镜，保持人物自然",
  },
];

const PROMPT_HINTS = [
  {
    id: "fresh",
    label: "更清新",
    prompt: "整体气质更清新自然，肤色更通透，背景更干净",
  },
  {
    id: "cute",
    label: "更可爱",
    prompt: "整体风格更可爱更亲和，表情更柔和",
  },
  {
    id: "formal",
    label: "正装风",
    prompt: "换成更适合头像展示的正装风格，整体更利落",
  },
  {
    id: "plain",
    label: "纯色背景",
    prompt: "背景换成简洁的纯色，突出人物主体",
  },
];

const FEATURE_PRESETS = {
  "smart-edit": ["自然补光", "修整发丝", "眼神更聚焦", "肤色更通透"],
  "background-replace": ["奶油色背景", "窗边自然光", "咖啡馆氛围", "极简纯色"],
};

function findFeature(key) {
  return getAdvancedFeatures().find((item) => item.key === key) || getAdvancedFeatures()[0];
}

function downloadRemoteFile(url) {
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

Page({
  data: {
    inputImageUrl: "",
    referenceImageUrl: "",
    prompt: "",
    selectedOutputCount: 2,
    pointsBalance: 0,
    rules: DEFAULT_RULES,
    currentFeature: "smart-edit",
    selectedPreset: FEATURE_PRESETS["smart-edit"][0],
    quickActions: QUICK_ACTIONS,
    selectedQuickAction: QUICK_ACTIONS[0].key,
    promptHints: PROMPT_HINTS,
    uploading: false,
    submitting: false,
    errorMsg: "",
    navStyle: "",
  },

  onLoad(query) {
    const metrics = getUiMetrics();
    this.setData({
      navStyle: `padding-top:${metrics.navContentTop}px;`,
    });
    if (query && query.preset) {
      this.setData({ inputImageUrl: decodeURIComponent(query.preset) });
    }
  },

  async onShow() {
    const ok = await ensureLogin();
    if (!ok) return;
    try {
      const balanceRes = await get("/points/balance");
      this.setData({
        rules: balanceRes.rules || DEFAULT_RULES,
        pointsBalance: balanceRes.points_balance || 0,
      });
    } catch (err) {
      this.setData({
        rules: DEFAULT_RULES,
        pointsBalance: 0,
      });
    }
  },

  onBack() {
    if (getCurrentPages().length > 1) {
      wx.navigateBack();
      return;
    }
    wx.reLaunch({ url: "/pages/create-menu/index" });
  },

  onHelpTap() {
    wx.navigateTo({ url: "/pages/service/index?type=about" });
  },

  onPromptInput(e) {
    this.setData({ prompt: e.detail.value });
  },

  onPromptHintTap(e) {
    const id = e.currentTarget.dataset.id;
    const hint = PROMPT_HINTS.find((item) => item.id === id);
    if (!hint) return;
    this.setData({ prompt: hint.prompt });
  },

  onQuickActionTap(e) {
    const key = e.currentTarget.dataset.key;
    const action = QUICK_ACTIONS.find((item) => item.key === key);
    if (!action) return;
    this.setData({
      selectedQuickAction: action.key,
      currentFeature: action.feature,
      selectedPreset: action.preset,
      prompt: action.prompt,
    });
  },

  uploadToTarget(filePath, targetField, successTitle) {
    this.setData({ uploading: true, errorMsg: "" });
    upload("/assets/upload", filePath)
      .then((uploaded) => {
        this.setData({ [targetField]: uploaded.file_url });
        wx.showToast({ title: successTitle, icon: "success" });
      })
      .catch((err) => {
        this.setData({ errorMsg: err.message || "图片上传失败" });
      })
      .finally(() => {
        this.setData({ uploading: false });
      });
  },

  openCropFlow(filePath) {
    wx.navigateTo({
      url: "/pages/avatar-crop/index?targetField=inputImageUrl&scene=image-edit",
      events: {
        cropped: ({ filePath: croppedFilePath }) => {
          this.uploadToTarget(croppedFilePath, "inputImageUrl", "头像已裁好");
        },
      },
      success: (navRes) => {
        navRes.eventChannel.emit("cropSource", {
          filePath,
          targetField: "inputImageUrl",
          scene: "image-edit",
        });
      },
    });
  },

  chooseAndUpload() {
    if (this.data.uploading) return;
    wx.chooseMedia({
      count: 1,
      mediaType: ["image"],
      sourceType: ["album", "camera"],
      success: (res) => {
        const filePath = res.tempFiles && res.tempFiles[0] ? res.tempFiles[0].tempFilePath : "";
        if (!filePath) return;
        this.openCropFlow(filePath);
      },
    });
  },

  async recropCurrent() {
    if (this.data.uploading) return;
    if (!this.data.inputImageUrl) {
      wx.showToast({ title: "请先上传一张头像", icon: "none" });
      return;
    }
    this.setData({ uploading: true, errorMsg: "" });
    try {
      const tempFilePath = await downloadRemoteFile(this.data.inputImageUrl);
      this.openCropFlow(tempFilePath);
    } catch (err) {
      this.setData({ errorMsg: err.message || "裁剪前准备失败" });
    } finally {
      this.setData({ uploading: false });
    }
  },

  chooseReferenceImage() {
    if (this.data.uploading) return;
    wx.chooseMedia({
      count: 1,
      mediaType: ["image"],
      sourceType: ["album", "camera"],
      success: (res) => {
        const filePath = res.tempFiles && res.tempFiles[0] ? res.tempFiles[0].tempFilePath : "";
        if (!filePath) return;
        this.uploadToTarget(filePath, "referenceImageUrl", "参考图已上传");
      },
    });
  },

  buildPrompt() {
    const quickAction = QUICK_ACTIONS.find((item) => item.key === this.data.selectedQuickAction);
    return (this.data.prompt || (quickAction && quickAction.prompt) || `请帮我做${this.data.selectedPreset}`).trim();
  },

  async onCreateTask() {
    if (this.data.submitting) return;
    if (!this.data.inputImageUrl) {
      this.setData({ errorMsg: "请先上传并裁好头像" });
      return;
    }

    this.setData({ submitting: true, errorMsg: "" });
    const feature = findFeature(this.data.currentFeature);
    try {
      const payload = normalizeTaskCreatePayload({
        task_type: "img2img",
        prompt: this.buildPrompt(),
        input_image_url: this.data.inputImageUrl,
        reference_image_url: this.data.referenceImageUrl || undefined,
        params: {
          tool: feature.title,
          preset: this.data.selectedPreset,
          ratio: "1:1",
          output_count: this.data.selectedOutputCount,
        },
      });
      const created = await post("/tasks", payload);
      wx.navigateTo({
        url: `/pages/loading/index?taskId=${encodeURIComponent(created.id)}&from=image-edit`,
      });
    } catch (err) {
      this.setData({ errorMsg: err.message || "任务创建失败" });
    } finally {
      this.setData({ submitting: false });
    }
  },
});
