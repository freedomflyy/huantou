const { ensureLogin } = require("../../utils/guard");
const { get, post, del } = require("../../utils/request");
const { getCachedTaskResult, waitForTaskOutputs } = require("../../utils/task-chain");
const {
  formatDateLabel,
  getTaskFrom,
  getTaskOutputCount,
  getTaskRatio,
  getTaskStyleName,
  getTaskTypeLabel,
  pickCoverClass,
} = require("../../utils/view-models");

function sourcePage(from, taskType) {
  const finalFrom = from || getTaskFrom({ task_type: taskType });
  const map = {
    "text-generate": "/pages/text-generate/index",
    "image-edit": "/pages/image-edit/index",
    "image-reference": "/pages/image-reference/index",
    "quick-edit": "/pages/quick-edit/index",
  };
  return map[finalFrom] || "/pages/create-menu/index";
}

Page({
  data: {
    taskId: "",
    from: "",
    task: null,
    outputs: [],
    errorMsg: "",
  },

  onLoad(query) {
    this.setData({
      taskId: query.taskId || "",
      from: query.from || "",
    });
  },

  async onShow() {
    const ok = await ensureLogin();
    if (!ok) return;
    await this.loadData();
  },

  async loadData() {
    if (!this.data.taskId) return;
    try {
      const task = await get(`/tasks/${this.data.taskId}`);
      if (task.status === "queued" || task.status === "running") {
        wx.redirectTo({
          url: `/pages/loading/index?taskId=${encodeURIComponent(this.data.taskId)}&from=${encodeURIComponent(this.data.from || getTaskFrom(task))}`,
        });
        return;
      }

      let assetsRes = await get("/assets?limit=100");
      let outputs = (assetsRes.items || []).filter((item) => item.source_task_id === this.data.taskId);
      if (!outputs.length && task.status === "succeeded") {
        await waitForTaskOutputs(this.data.taskId, { maxPoll: 6, interval: 1200 });
        assetsRes = await get("/assets?limit=100");
        outputs = (assetsRes.items || []).filter((item) => item.source_task_id === this.data.taskId);
      }
      const heroImage = outputs[0] ? (outputs[0].thumbnail_url || outputs[0].file_url) : (task.input_image_url || "");
      const taskVm = {
        id: task.id,
        taskType: task.task_type,
        status: task.status,
        modeLabel: getTaskTypeLabel(task.task_type),
        styleName: getTaskStyleName(task),
        ratio: getTaskRatio(task),
        outputCount: getTaskOutputCount(task),
        prompt: task.prompt || "这次没有填写提示词",
        createdAtLabel: formatDateLabel(task.created_at),
        finishedAtLabel: formatDateLabel(task.finished_at),
        inputImageUrl: task.input_image_url || "",
        displayImageUrl: heroImage,
        coverClass: pickCoverClass(`${task.id}-${getTaskStyleName(task)}`),
        errorMessage: task.error_message || "",
      };
      const outputCards = outputs.map((item, index) => ({
        id: item.id,
        imageUrl: item.thumbnail_url || item.file_url,
        fileUrl: item.file_url,
        title: outputs.length > 1 ? `候选图 ${index + 1}` : "主推荐图",
        subtitle: getTaskStyleName(task),
        coverClass: pickCoverClass(`${item.id}-${index}`),
        badge: index === 0 ? "主推" : "版本",
        isFavorited: !!item.is_favorited,
      }));
      const cached = getCachedTaskResult(this.data.taskId);
      this.setData({
        task: taskVm,
        outputs: outputCards,
        errorMsg: task.status === "failed" ? (task.error_message || "这次生成失败了") : ((cached && cached.errorMessage) || ""),
        from: this.data.from || getTaskFrom(task),
      });
    } catch (err) {
      this.setData({
        task: null,
        outputs: [],
        errorMsg: err.message || "作品加载失败",
      });
    }
  },

  previewImage(e) {
    const current = e.currentTarget.dataset.url;
    if (!current) return;
    wx.previewImage({ current, urls: [current] });
  },

  async onFavoriteTap(e) {
    const outputId = e.currentTarget.dataset.id;
    const favorited = !!e.currentTarget.dataset.favorited;
    if (!outputId) return;
    try {
      if (favorited) {
        await del(`/assets/${outputId}/favorite`);
      } else {
        await post(`/assets/${outputId}/favorite`, {});
      }
      wx.showToast({
        title: favorited ? "已取消收藏" : "已收藏到作品集",
        icon: "none",
      });
      await this.loadData();
    } catch (err) {
      wx.showToast({
        title: err.message || "收藏失败",
        icon: "none",
      });
    }
  },

  goSource() {
    if (!this.data.task) {
      wx.navigateTo({ url: "/pages/create-menu/index" });
      return;
    }
    wx.navigateTo({ url: sourcePage(this.data.from, this.data.task.taskType) });
  },

  goAssets() {
    wx.reLaunch({ url: "/pages/assets/index" });
  },

  goDecorate() {
    if (!this.data.task || !this.data.task.displayImageUrl) return;
    wx.navigateTo({
      url: `/pages/avatar-decorate/index?taskId=${encodeURIComponent(this.data.taskId)}&imageUrl=${encodeURIComponent(this.data.task.displayImageUrl)}`,
    });
  },

  copyPrompt() {
    if (!this.data.task || !this.data.task.prompt) return;
    wx.setClipboardData({
      data: this.data.task.prompt,
    });
  },
});
