const { ensureLogin } = require("../../utils/guard");
const { get, post } = require("../../utils/request");
const { normalizeTaskCreatePayload } = require("../../utils/view-models");

const inspirations = [
  "温暖阳光里的女生头像，米白背景，柔和笑容，插画风",
  "高级感商务头像，奶油光影，干净背景，轻胶片质感",
  "二次元治愈系头像，暖棕配色，眼神温柔，细腻笔触",
];

const DEFAULT_RULES = {
  txt2img_cost: 20,
  img2img_cost: 18,
  style_transfer_cost: 22,
};

Page({
  data: {
    prompt: "",
    negativePrompt: "",
    selectedRatio: "1:1",
    selectedOutputCount: 4,
    ratios: [
      { value: "1:1", label: "正方形", note: "头像最常用" },
      { value: "4:5", label: "竖构图", note: "更显人物" },
      { value: "3:4", label: "海报感", note: "留白更足" },
    ],
    outputCountOptions: [
      { value: 1, label: "1 张", note: "快速预览" },
      { value: 2, label: "2 张", note: "方便对比" },
      { value: 4, label: "4 张", note: "组图候选" },
    ],
    ideas: ["柔焦插画", "皮克斯风", "古典油画", "森系童话"],
    selectedIdea: "柔焦插画",
    rules: DEFAULT_RULES,
    submitting: false,
    errorMsg: "",
    inspirationText: inspirations[0],
  },

  onLoad(query) {
    if (query && query.idea) {
      this.setData({ selectedIdea: decodeURIComponent(query.idea) });
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

  onNegativePromptInput(e) {
    this.setData({ negativePrompt: e.detail.value });
  },

  onIdeaTap(e) {
    const idea = e.currentTarget.dataset.idea;
    if (!idea) return;
    this.setData({ selectedIdea: idea });
  },

  onRatioTap(e) {
    const ratio = e.currentTarget.dataset.ratio;
    if (!ratio) return;
    this.setData({ selectedRatio: ratio });
  },

  onOutputCountTap(e) {
    const count = Number(e.currentTarget.dataset.count || 0);
    if (!count) return;
    this.setData({ selectedOutputCount: count });
  },

  randomPrompt() {
    const next = inspirations[Math.floor(Math.random() * inspirations.length)];
    this.setData({
      prompt: next,
      inspirationText: next,
    });
  },

  async onCreateTask() {
    if (this.data.submitting) return;
    const prompt = this.data.prompt || this.data.inspirationText;
    this.setData({ submitting: true, errorMsg: "" });
    try {
      const payload = normalizeTaskCreatePayload({
        task_type: "txt2img",
        prompt,
        negative_prompt: this.data.negativePrompt,
        params: {
          style_name: this.data.selectedIdea,
          ratio: this.data.selectedRatio,
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
