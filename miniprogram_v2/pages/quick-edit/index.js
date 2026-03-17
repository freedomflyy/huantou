const { post, upload } = require("../../utils/request");
const { ensureLogin } = require("../../utils/guard");
const { normalizeTaskCreatePayload } = require("../../utils/view-models");

Page({
  data: {
    providerOptions: ["volcengine"],
    providerIndex: 0,
    inputImageUrl: "",
    rotate: "0",
    brightness: "1.0",
    saturation: "1.0",
    contrast: "1.0",
    format: "jpeg",
    quality: "90",
    uploading: false,
    submitting: false,
    errorMsg: "",
  },

  onShow() {
    ensureLogin();
  },

  onProviderChange(e) {
    this.setData({ providerIndex: Number(e.detail.value || 0) });
  },

  onInputUrlInput(e) {
    this.setData({ inputImageUrl: e.detail.value });
  },

  onFieldInput(e) {
    const field = e.currentTarget.dataset.field;
    if (!field) return;
    this.setData({ [field]: e.detail.value });
  },

  pickFromAssets() {
    wx.navigateTo({
      url: "/pages/assets/index?select=1&target=input",
      success: (res) => {
        res.eventChannel.on("assetSelected", (payload) => {
          if (payload && payload.url) this.setData({ inputImageUrl: payload.url });
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
      success: async (res) => {
        const filePath = res.tempFiles && res.tempFiles[0] ? res.tempFiles[0].tempFilePath : "";
        if (!filePath) return;
        this.setData({ uploading: true, errorMsg: "" });
        try {
          const uploaded = await upload("/assets/upload", filePath);
          this.setData({ inputImageUrl: uploaded.file_url });
          wx.showToast({ title: "上传成功", icon: "success" });
        } catch (err) {
          this.setData({ errorMsg: err.message || "上传失败" });
        } finally {
          this.setData({ uploading: false });
        }
      },
    });
  },

  async onCreateTask() {
    if (this.data.submitting) return;
    this.setData({ submitting: true, errorMsg: "" });
    try {
      const payload = normalizeTaskCreatePayload({
        task_type: "quick_edit",
        provider: this.data.providerOptions[this.data.providerIndex],
        input_image_url: this.data.inputImageUrl,
        params: {
          operations: {
            rotate: Number(this.data.rotate || 0),
            brightness: Number(this.data.brightness || 1),
            saturation: Number(this.data.saturation || 1),
            contrast: Number(this.data.contrast || 1),
          },
          output: {
            format: this.data.format || "jpeg",
            quality: Number(this.data.quality || 90),
          },
        },
      });
      const created = await post("/tasks", payload);
      wx.navigateTo({
        url: `/pages/loading/index?taskId=${encodeURIComponent(created.id)}&from=quick-edit`,
      });
    } catch (err) {
      this.setData({ errorMsg: err.message || "任务创建失败" });
    } finally {
      this.setData({ submitting: false });
    }
  },
});
