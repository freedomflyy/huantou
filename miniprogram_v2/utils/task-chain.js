const { get } = require("./request");
const { getTaskOutputCount, getTaskTypeLabel, toTaskExecutionViewModel } = require("./view-models");

const TERMINAL_STATUS = {
  succeeded: true,
  failed: true,
  canceled: true,
};

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function parseDate(value) {
  if (!value) return 0;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 0 : date.getTime();
}

function isTaskFinished(task) {
  return !!(task && TERMINAL_STATUS[task.status]);
}

async function findOutputsByTaskId(taskId) {
  const list = await get("/assets?limit=100");
  const assets = (list.items || []).filter((a) => a.source_task_id === taskId);
  return assets.map((a) => a.file_url).filter(Boolean);
}

function getTaskElapsedSeconds(task) {
  if (!task) return 0;
  const baseTime = parseDate(task.started_at) || parseDate(task.queued_at) || parseDate(task.created_at);
  if (!baseTime) return 0;
  return Math.max(0, Math.round((Date.now() - baseTime) / 1000));
}

function getExpectedSeconds(task) {
  if (!task) return 24;
  const outputCount = Math.max(1, getTaskOutputCount(task));
  const baseMap = {
    txt2img: 24,
    img2img: 28,
    style_transfer: 34,
    quick_edit: 10,
  };
  return (baseMap[task.task_type] || 24) + Math.max(0, outputCount - 1) * 12;
}

function getRunningText(task) {
  const typeLabel = getTaskTypeLabel(task.task_type);
  const outputCount = Math.max(1, getTaskOutputCount(task));
  if (outputCount > 1) {
    return `${typeLabel}正在生成 ${outputCount} 张候选图`;
  }
  return `${typeLabel}正在绘制中`;
}

function getTaskProgressMeta(task, pollCount = 0) {
  const elapsedSeconds = getTaskElapsedSeconds(task);
  const expectedSeconds = getExpectedSeconds(task);
  let progress = 10;
  let statusLabel = "准备中";
  let statusClass = "status-running";
  let statusText = "任务已创建，正在接入绘制服务";

  if (!task) {
    return {
      progress,
      statusLabel,
      statusClass,
      statusText,
      waitText: "请保持当前页面开启",
      elapsedSeconds: 0,
      expectedSeconds,
    };
  }

  if (task.status === "queued") {
    progress = Math.min(12 + pollCount * 4 + Math.floor(elapsedSeconds / 2), 32);
    statusLabel = "排队中";
    statusText = "任务已经进入队列，正在等待空闲算力";
  } else if (task.status === "running") {
    progress = Math.min(38 + Math.floor((elapsedSeconds / Math.max(1, expectedSeconds)) * 52), 94);
    statusLabel = "生成中";
    statusText = getRunningText(task);
  } else if (task.status === "succeeded") {
    progress = 100;
    statusLabel = "已完成";
    statusClass = "status-succeeded";
    statusText = "作品已经生成完成，正在整理展示";
  } else if (task.status === "failed") {
    progress = Math.max(24, Math.min(95, 24 + pollCount * 3));
    statusLabel = "失败";
    statusClass = "status-failed";
    statusText = task.error_message || "这次生成没有成功";
  } else if (task.status === "canceled") {
    progress = Math.max(24, Math.min(95, 24 + pollCount * 3));
    statusLabel = "已取消";
    statusClass = "status-failed";
    statusText = "任务已取消";
  }

  return {
    progress,
    statusLabel,
    statusClass,
    statusText,
    waitText: task.status === "succeeded" ? "正在同步作品库" : `已等待 ${elapsedSeconds} 秒`,
    elapsedSeconds,
    expectedSeconds,
  };
}

async function waitForTaskOutputs(taskId, opts = {}) {
  const maxPoll = opts.maxPoll || 12;
  const interval = opts.interval || 1200;
  let outputs = [];
  let count = 0;
  while (!outputs.length && count < maxPoll) {
    count += 1;
    outputs = await findOutputsByTaskId(taskId);
    if (outputs.length) {
      return outputs;
    }
    await delay(interval);
  }
  return outputs;
}

function cacheTaskResult(taskId, payload) {
  wx.setStorageSync(`task_result_${taskId}`, payload);
}

async function pollTaskUntilFinal(taskId, opts = {}) {
  const maxPoll = opts.maxPoll || 120;
  const interval = opts.interval || 2000;
  let pollCount = 0;
  let taskData = await get(`/tasks/${taskId}`);

  while (taskData && !isTaskFinished(taskData) && pollCount < maxPoll) {
    pollCount += 1;
    await delay(interval);
    taskData = await get(`/tasks/${taskId}`);
  }

  let outputUrls = [];
  if (taskData && taskData.status === "succeeded") {
    outputUrls = await waitForTaskOutputs(taskId, opts);
  }

  const vm = toTaskExecutionViewModel(taskData, outputUrls);
  cacheTaskResult(taskId, vm);
  return vm;
}

function getCachedTaskResult(taskId) {
  return wx.getStorageSync(`task_result_${taskId}`) || null;
}

module.exports = {
  cacheTaskResult,
  pollTaskUntilFinal,
  getCachedTaskResult,
  findOutputsByTaskId,
  waitForTaskOutputs,
  isTaskFinished,
  getTaskProgressMeta,
};
