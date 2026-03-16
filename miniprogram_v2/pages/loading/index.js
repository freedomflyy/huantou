const { ensureLogin } = require("../../utils/guard");
const { get } = require("../../utils/request");
const {
  cacheTaskResult,
  getTaskProgressMeta,
  isTaskFinished,
  waitForTaskOutputs,
} = require("../../utils/task-chain");
const { getTaskTypeLabel, toTaskExecutionViewModel } = require("../../utils/view-models");

Page({
  data: {
    taskId: "",
    from: "",
    statusText: "任务已创建，正在接入绘制服务",
    statusLabel: "准备中",
    statusClass: "status-running",
    loading: true,
    progress: 10,
    waitText: "请保持当前页面开启",
    taskTitle: "AI 正在绘制你的头像",
  },

  onLoad(query) {
    this.pollCount = 0;
    this.currentTask = null;
    this.requesting = false;
    this.finished = false;
    this.setData({
      taskId: query.taskId || "",
      from: query.from || "",
    });
  },

  async onShow() {
    if (!this.data.taskId) {
      wx.redirectTo({ url: "/pages/create-menu/index" });
      return;
    }
    const ok = await ensureLogin();
    if (!ok) return;
    this.start();
  },

  onHide() {
    this.clearTimer();
  },

  onUnload() {
    this.clearTimer();
  },

  start() {
    this.clearTimer();
    this.finished = false;
    this.pollCount = 0;
    this.currentTask = null;

    this.setData({
      loading: true,
      progress: 10,
      waitText: "请保持当前页面开启",
      statusText: "任务已创建，正在接入绘制服务",
      statusLabel: "准备中",
      statusClass: "status-running",
    });

    this.refreshTask();
    this.timer = setInterval(() => {
      if (this.finished) return;
      if (this.currentTask && !isTaskFinished(this.currentTask)) {
        this.applyTaskState(this.currentTask);
      }
    }, 1000);
    this.pollTimer = setInterval(() => {
      this.refreshTask();
    }, 2500);
  },

  async refreshTask() {
    if (this.requesting || !this.data.taskId || this.finished) return;
    this.requesting = true;
    try {
      const task = await get(`/tasks/${this.data.taskId}`);
      this.currentTask = task;
      this.applyTaskState(task);
      if (isTaskFinished(task)) {
        await this.finishTask(task);
      } else {
        this.pollCount += 1;
      }
    } catch (err) {
      this.setData({
        statusText: err.message || "网络波动，正在重试",
        waitText: "稍后会自动继续查询任务状态",
      });
    } finally {
      this.requesting = false;
    }
  },

  applyTaskState(task) {
    const meta = getTaskProgressMeta(task, this.pollCount);
    this.setData({
      taskTitle: `${getTaskTypeLabel(task.task_type)}${task.status === "succeeded" ? " 已完成" : " 生成中"}`,
      progress: meta.progress,
      statusText: meta.statusText,
      statusLabel: meta.statusLabel,
      statusClass: meta.statusClass,
      waitText: meta.waitText,
    });
  },

  async finishTask(task) {
    if (this.finished) return;
    this.finished = true;
    this.clearTimer();

    let outputUrls = [];
    if (task.status === "succeeded") {
      outputUrls = await waitForTaskOutputs(task.id, { maxPoll: 12, interval: 1500 });
    }

    const result = toTaskExecutionViewModel(task, outputUrls);
    cacheTaskResult(task.id, result);

    this.setData({
      progress: task.status === "succeeded" ? 100 : this.data.progress,
      statusText: task.status === "succeeded"
        ? (outputUrls.length ? "作品已经准备好了，马上为你打开" : "图片已生成，正在同步作品库")
        : (task.error_message || "这次生成没有成功"),
      waitText: task.status === "succeeded"
        ? `共生成 ${Math.max(1, outputUrls.length)} 张候选图`
        : "可以返回创作页重新发起任务",
    });

    this.redirectTimer = setTimeout(() => {
      wx.redirectTo({
        url: `/pages/result/index?taskId=${encodeURIComponent(this.data.taskId)}&from=${encodeURIComponent(this.data.from)}`,
      });
    }, task.status === "succeeded" ? 600 : 900);
  },

  clearTimer() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
    if (this.redirectTimer) {
      clearTimeout(this.redirectTimer);
      this.redirectTimer = null;
    }
  },
});
