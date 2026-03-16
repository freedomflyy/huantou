const { ensureLogin } = require("../../utils/guard");
const { get, post, upload } = require("../../utils/request");
const { normalizeTaskCreatePayload } = require("../../utils/view-models");

const DEFAULT_RULES = {
  txt2img_cost: 20,
  img2img_cost: 18,
  style_transfer_cost: 22,
};

Page({
  data: {
    inputImageUrl: "",
    prompt: "",
    selectedOutputCount: 4,
    rules: DEFAULT_RULES,
    tabs: ["AI 换背景", "贴纸库", "局部重绘", "高级工具"],
    currentTab: "AI 换背景",
    presets: ["夕阳暖阳", "森系童话", "惬意午后", "梦幻星空"],
    outputCountOptions: [
      { value: 1, label: "1 张", note: "快速修改" },
      { value: 2, label: "2 张", note: "主副版本" },
      { value: 4, label: "4 张", note: "多方案挑选" },
    ],
    selectedPreset: "夕阳暖阳",
    uploading: false,
    submitting: false,
    errorMsg: "",
  },

  onLoad(query) {
    if (query && query.preset) {
      this.setData({ inputImageUrl: decodeURIComponent(query.preset) });
    }
  },

  async onShow() {
    const ok = await ensureLogin();
    if (!ok) return;
    try {
      const balanceRes = await get("/points/balance");
      this.setData({ rules: balanceRes.rules || DEFAULT_RULES });
    } catch (err) {
      this.setData({ rules: DEFAULT_RULES });
    }
  },

  onPromptInput(e) {
    this.setData({ prompt: e.detail.value });
  },

  onTabTap(e) {
    const tab = e.currentTarget.dataset.tab;
    if (!tab) return;
    this.setData({ currentTab: tab });
  },

  onPresetTap(e) {
    const preset = e.currentTarget.dataset.preset;
    if (!preset) return;
    this.setData({ selectedPreset: preset });
  },

  onOutputCountTap(e) {
    const count = Number(e.currentTarget.dataset.count || 0);
    if (!count) return;
    this.setData({ selectedOutputCount: count });
  },

  chooseAndUpload() {
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
          this.setData({ inputImageUrl: uploaded.file_url });
          wx.showToast({ title: "上传成功", icon: "success" });
        } catch (err) {
          this.setData({ errorMsg: err.message || "图片上传失败" });
        } finally {
          this.setData({ uploading: false });
        }
      },
    });
  },

  async onCreateTask() {
    if (this.data.submitting) return;
    if (!this.data.inputImageUrl) {
      this.setData({ errorMsg: "请先上传一张头像" });
      return;
    }
    this.setData({ submitting: true, errorMsg: "" });
    try {
      const payload = normalizeTaskCreatePayload({
        task_type: "img2img",
        prompt: this.data.prompt || `请帮我做${this.data.currentTab}，预设为${this.data.selectedPreset}`,
        input_image_url: this.data.inputImageUrl,
        params: {
          tool: this.data.currentTab,
          preset: this.data.selectedPreset,
          ratio: "4:5",
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
