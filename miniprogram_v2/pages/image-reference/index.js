const { ensureLogin } = require("../../utils/guard");
const { get, post, upload } = require("../../utils/request");
const { normalizeTaskCreatePayload } = require("../../utils/view-models");

const DEFAULT_RULES = {
  txt2img_cost: 20,
  img2img_cost: 18,
  style_transfer_cost: 22,
};

const STYLE_CARDS = [
  { id: "cyber", name: "赛博肖像", desc: "霓虹科技感", coverClass: "cover-night", hot: true },
  { id: "pixar", name: "皮克斯风", desc: "治愈系 3D 动画", coverClass: "cover-cream" },
  { id: "sketch", name: "艺术素描", desc: "极简炭笔线条", coverClass: "cover-mocha" },
  { id: "oil", name: "古典油画", desc: "暖棕复古质感", coverClass: "cover-sunset" },
];

Page({
  data: {
    inputImageUrl: "",
    referenceImageUrl: "",
    prompt: "",
    selectedOutputCount: 4,
    styleCards: STYLE_CARDS,
    outputCountOptions: [
      { value: 1, label: "1 张", note: "单张出图" },
      { value: 2, label: "2 张", note: "主副版本" },
      { value: 4, label: "4 张", note: "更多候选" },
    ],
    selectedStyle: "赛博肖像",
    rules: DEFAULT_RULES,
    uploading: false,
    submitting: false,
    errorMsg: "",
  },

  async onShow() {
    const ok = await ensureLogin();
    if (!ok) return;
    try {
      const balanceRes = await get("/points/balance");
      this.setData({
        rules: balanceRes.rules || DEFAULT_RULES,
        styleCards: STYLE_CARDS,
      });
    } catch (err) {
      this.setData({
        rules: DEFAULT_RULES,
        styleCards: STYLE_CARDS,
      });
    }
  },

  onPromptInput(e) {
    this.setData({ prompt: e.detail.value });
  },

  onStyleTap(e) {
    const style = e.currentTarget.dataset.style;
    if (!style) return;
    this.setData({ selectedStyle: style });
  },

  onOutputCountTap(e) {
    const count = Number(e.currentTarget.dataset.count || 0);
    if (!count) return;
    this.setData({ selectedOutputCount: count });
  },

  chooseImage(targetField) {
    if (this.data.uploading) return;
    wx.chooseMedia({
      count: 1,
      mediaType: ["image"],
      sourceType: ["album", "camera"],
      success: async (res) => {
        const filePath = res.tempFiles && res.tempFiles[0] ? res.tempFiles[0].tempFilePath : "";
        if (!filePath) return;
        this.setData({ uploading: true, errorMsg: "" });
        try {
          const uploaded = await upload("/assets/upload", filePath);
          this.setData({ [targetField]: uploaded.file_url });
          wx.showToast({ title: "上传成功", icon: "success" });
        } catch (err) {
          this.setData({ errorMsg: err.message || "图片上传失败" });
        } finally {
          this.setData({ uploading: false });
        }
      },
    });
  },

  uploadInput() {
    this.chooseImage("inputImageUrl");
  },

  uploadReference() {
    this.chooseImage("referenceImageUrl");
  },

  async onCreateTask() {
    if (this.data.submitting) return;
    if (!this.data.inputImageUrl) {
      this.setData({ errorMsg: "请先上传主图" });
      return;
    }
    if (!this.data.referenceImageUrl) {
      this.setData({ errorMsg: "当前后端的风格迁移需要一张参考图，请再上传一张风格图" });
      return;
    }
    this.setData({ submitting: true, errorMsg: "" });
    try {
      const payload = normalizeTaskCreatePayload({
        task_type: "style_transfer",
        prompt: this.data.prompt || `保留人物神态，转成${this.data.selectedStyle}`,
        input_image_url: this.data.inputImageUrl,
        reference_image_url: this.data.referenceImageUrl,
        params: {
          style_name: this.data.selectedStyle,
          ratio: "4:5",
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
