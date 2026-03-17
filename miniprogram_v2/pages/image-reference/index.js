const { ensureLogin } = require("../../utils/guard");
const { get, post, upload } = require("../../utils/request");
const { normalizeTaskCreatePayload } = require("../../utils/view-models");
const { getStyleTemplates } = require("../../utils/avatar-studio");

const DEFAULT_RULES = {
  txt2img_cost: 20,
  img2img_cost: 18,
  style_transfer_cost: 22,
};

function getFallbackStyleCards() {
  return getStyleTemplates().map((item) => ({
    id: item.id,
    name: item.name,
    desc: item.desc,
    badge: item.badge,
    coverClass: item.coverClass,
    imageUrl: "",
    referenceImageUrl: "",
  }));
}

function mapMaterialStyles(items, fallbackItems) {
  const fallback = fallbackItems && fallbackItems.length ? fallbackItems : getFallbackStyleCards();
  return (items || []).map((item, index) => {
    const base = fallback[index % fallback.length] || fallback[0] || {};
    return {
      id: item.id,
      name: item.title,
      desc: item.subtitle || base.desc || "",
      badge: item.badge || base.badge || "",
      coverClass: base.coverClass || "cover-cream",
      imageUrl: item.file_url || "",
      referenceImageUrl: item.file_url || "",
    };
  });
}

function resolveSelectedStyle(styleCards, preferredStyle) {
  const list = styleCards || [];
  const current = list.find((item) => item.name === preferredStyle) || list[0] || null;
  return {
    selectedStyle: current ? current.name : "",
    selectedStyleDesc: current ? current.desc : "",
    referenceImageUrl: current ? (current.referenceImageUrl || current.imageUrl || "") : "",
  };
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
    styleCards: getFallbackStyleCards(),
    selectedStyle: "",
    selectedStyleDesc: "",
    selectedOutputCount: 4,
    styleStrength: 85,
    preserveFace: true,
    rules: DEFAULT_RULES,
    uploading: false,
    submitting: false,
    errorMsg: "",
  },

  onLoad(query) {
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
    const fallbackCards = getFallbackStyleCards();
    const results = await Promise.allSettled([
      get("/points/balance"),
      get("/materials"),
    ]);
    const balanceRes = results[0].status === "fulfilled" ? results[0].value : null;
    const materialsRes = results[1].status === "fulfilled" ? results[1].value : null;
    const styleCards = materialsRes && materialsRes.home_styles && materialsRes.home_styles.length
      ? mapMaterialStyles(materialsRes.home_styles, fallbackCards)
      : fallbackCards;
    const selected = resolveSelectedStyle(styleCards, this.data.selectedStyle);

    this.setData({
      rules: (balanceRes && balanceRes.rules) || DEFAULT_RULES,
      styleCards,
      selectedStyle: selected.selectedStyle,
      selectedStyleDesc: selected.selectedStyleDesc,
      referenceImageUrl: selected.referenceImageUrl,
    });
  },

  onBack() {
    if (getCurrentPages().length > 1) {
      wx.navigateBack();
      return;
    }
    wx.reLaunch({ url: "/pages/create-menu/index" });
  },

  onPortraitTap() {
    if (!this.data.inputImageUrl) {
      this.uploadInput();
    }
  },

  onStyleTap(e) {
    const style = e.currentTarget.dataset.style;
    if (!style) return;
    const matched = (this.data.styleCards || []).find((item) => item.name === style);
    this.setData({
      selectedStyle: style,
      selectedStyleDesc: matched ? matched.desc : "",
      referenceImageUrl: matched ? (matched.referenceImageUrl || matched.imageUrl || "") : "",
    });
  },

  onStrengthChange(e) {
    this.setData({ styleStrength: Number(e.detail.value || 85) });
  },

  onPreserveFaceChange(e) {
    this.setData({ preserveFace: !!e.detail.value });
  },

  uploadToTarget(filePath) {
    this.setData({ uploading: true, errorMsg: "" });
    upload("/assets/upload", filePath)
      .then((uploaded) => {
        this.setData({ inputImageUrl: uploaded.file_url });
        wx.showToast({ title: "头像已裁好", icon: "success" });
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
      url: "/pages/avatar-crop/index?targetField=inputImageUrl&scene=image-reference",
      events: {
        cropped: ({ filePath: croppedFilePath }) => {
          this.uploadToTarget(croppedFilePath);
        },
      },
      success: (res) => {
        res.eventChannel.emit("cropSource", {
          filePath,
          targetField: "inputImageUrl",
          scene: "image-reference",
        });
      },
    });
  },

  uploadInput() {
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

  buildPrompt() {
    const parts = [
      `保留人物神态，转成${this.data.selectedStyle}`,
      `风格强度约${this.data.styleStrength}%`,
    ];
    if (this.data.selectedStyleDesc) {
      parts.push(this.data.selectedStyleDesc);
    }
    if (this.data.preserveFace) {
      parts.push("尽量保留面部特征和本人辨识度");
    }
    return parts.join("，");
  },

  async onCreateTask() {
    if (this.data.submitting) return;
    if (!this.data.inputImageUrl) {
      this.setData({ errorMsg: "请先上传并裁好头像主图" });
      return;
    }
    if (!this.data.referenceImageUrl) {
      this.setData({ errorMsg: "当前风格模板的参考图还未准备好，请稍后重试" });
      return;
    }

    this.setData({ submitting: true, errorMsg: "" });
    try {
      const payload = normalizeTaskCreatePayload({
        task_type: "style_transfer",
        prompt: this.buildPrompt(),
        input_image_url: this.data.inputImageUrl,
        reference_image_url: this.data.referenceImageUrl,
        params: {
          style_name: this.data.selectedStyle,
          ratio: "1:1",
          output_count: this.data.selectedOutputCount,
        },
      });
      const created = await post("/tasks", payload);
      wx.navigateTo({
        url: `/pages/loading/index?taskId=${encodeURIComponent(created.id)}&from=image-reference`,
      });
    } catch (err) {
      this.setData({ errorMsg: err.message || "任务创建失败" });
    } finally {
      this.setData({ submitting: false });
    }
  },
});
