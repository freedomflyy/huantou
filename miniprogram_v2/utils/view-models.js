function normalizeTaskCreatePayload(payload) {
  const clean = {
    task_type: payload.task_type,
    provider: payload.provider || "volcengine",
    prompt: payload.prompt || undefined,
    negative_prompt: payload.negative_prompt || undefined,
    input_image_url: payload.input_image_url || undefined,
    reference_image_url: payload.reference_image_url || undefined,
    params: payload.params || {},
  };

  if (clean.task_type === "img2img" || clean.task_type === "quick_edit") {
    if (!clean.input_image_url) {
      throw new Error("该任务类型需要输入图");
    }
  }
  if (clean.task_type === "style_transfer") {
    if (!clean.input_image_url || !clean.reference_image_url) {
      throw new Error("参考图生成需要主图和参考图");
    }
  }
  return clean;
}

function formatDateLabel(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const month = `${date.getMonth() + 1}`.padStart(2, "0");
  const day = `${date.getDate()}`.padStart(2, "0");
  const hour = `${date.getHours()}`.padStart(2, "0");
  const minute = `${date.getMinutes()}`.padStart(2, "0");
  return `${month}-${day} ${hour}:${minute}`;
}

function hashCode(text) {
  const raw = String(text || "");
  let hash = 0;
  for (let i = 0; i < raw.length; i += 1) {
    hash = (hash << 5) - hash + raw.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
}

function pickCoverClass(seed) {
  const covers = ["cover-sunset", "cover-cream", "cover-mocha", "cover-forest", "cover-night", "cover-peach"];
  return covers[hashCode(seed) % covers.length];
}

function getTaskTypeLabel(taskType) {
  const map = {
    txt2img: "AI 绘画",
    img2img: "AI 精修",
    style_transfer: "风格迁移",
    quick_edit: "快速编辑",
  };
  return map[taskType] || "创作任务";
}

function getTaskFrom(task) {
  const map = {
    txt2img: "text-generate",
    img2img: "image-edit",
    style_transfer: "image-reference",
    quick_edit: "quick-edit",
  };
  return map[task.task_type] || "";
}

function getTaskRatio(task) {
  const params = task.params || {};
  return params.ratio || params.aspect_ratio || (task.task_type === "txt2img" ? "1:1" : "4:5");
}

function getTaskOutputCount(task) {
  const params = task.params || {};
  const direct = params.output_count;
  if (direct !== undefined && direct !== null && direct !== "") {
    const parsed = Number(direct);
    if (!Number.isNaN(parsed) && parsed > 0) return parsed;
  }
  const sequential = params.sequential_image_generation_options;
  if (sequential && sequential.max_images !== undefined) {
    const parsed = Number(sequential.max_images);
    if (!Number.isNaN(parsed) && parsed > 0) return parsed;
  }
  return 1;
}

function getTaskStyleName(task) {
  const params = task.params || {};
  if (params.style_name) return params.style_name;
  if (params.styleName) return params.styleName;
  if (params.preset) return params.preset;
  if (params.tool) return params.tool;
  if (task.task_type === "style_transfer") return "参考图转绘";
  if (task.task_type === "img2img") return "精修工作台";
  if (task.task_type === "quick_edit") return "基础编辑";
  return "自定义风格";
}

function toTaskExecutionViewModel(task, outputUrls) {
  const statusMap = {
    queued: "排队中",
    running: "生成中",
    succeeded: "生成成功",
    failed: "生成失败",
    canceled: "已取消",
  };
  return {
    id: task.id,
    taskType: task.task_type,
    provider: task.provider || "",
    status: task.status,
    statusText: statusMap[task.status] || task.status,
    prompt: task.prompt || "",
    outputUrls: outputUrls || [],
    errorMessage: task.error_message || "",
    costPoints: task.cost_points || 0,
  };
}

function toAssetViewModel(asset) {
  return {
    id: asset.id,
    sourceTaskId: asset.source_task_id || "",
    fileUrl: asset.file_url,
    thumbUrl: asset.thumbnail_url || asset.file_url,
    isFavorited: !!asset.is_favorited,
    expiresAt: asset.expires_at || "",
    provider: asset.storage_provider || "",
  };
}

function toTaskCardViewModel(task) {
  const statusMap = {
    queued: { label: "排队中", className: "status-running" },
    running: { label: "处理中", className: "status-running" },
    succeeded: { label: "已完成", className: "status-succeeded" },
    failed: { label: "失败", className: "status-failed" },
    canceled: { label: "已取消", className: "status-failed" },
  };
  const statusMeta = statusMap[task.status] || { label: task.status, className: "status-running" };
  return {
    id: task.id,
    from: getTaskFrom(task),
    taskType: task.task_type,
    modeLabel: getTaskTypeLabel(task.task_type),
    styleName: getTaskStyleName(task),
    ratio: getTaskRatio(task),
    outputCount: getTaskOutputCount(task),
    prompt: task.prompt || "",
    status: task.status,
    statusLabel: statusMeta.label,
    statusClass: statusMeta.className,
    createdAtLabel: formatDateLabel(task.created_at || task.queued_at),
    finishedAtLabel: formatDateLabel(task.finished_at),
    coverClass: pickCoverClass(`${task.id}-${getTaskStyleName(task)}`),
    inputImageUrl: task.input_image_url || "",
    referenceImageUrl: task.reference_image_url || "",
    errorMessage: task.error_message || "",
    costPoints: task.cost_points || 0,
  };
}

function toAssetCardViewModel(asset, taskMap = {}) {
  const task = asset.source_task_id ? taskMap[asset.source_task_id] : null;
  const modeLabel = task ? getTaskTypeLabel(task.task_type) : "上传素材";
  const styleName = task ? getTaskStyleName(task) : "我的作品";
  return {
    id: asset.id,
    assetId: asset.id,
    taskId: asset.source_task_id || "",
    sourceTaskId: asset.source_task_id || "",
    title: task ? `${modeLabel}作品` : "上传图片",
    subtitle: styleName,
    author: modeLabel,
    likes: formatDateLabel(asset.created_at),
    coverClass: pickCoverClass(`${asset.id}-${styleName}`),
    imageUrl: asset.thumbnail_url || asset.file_url,
    fileUrl: asset.file_url,
    badge: styleName,
    isFavorite: !!asset.is_favorited,
    isFavorited: !!asset.is_favorited,
    createdAtLabel: formatDateLabel(asset.created_at),
    publishedAt: asset.created_at || "",
    creatorName: "",
    styleName,
  };
}

function toShowcaseCardViewModel(item) {
  const styleName = item.style_name || item.badge || item.subtitle || "";
  return {
    id: item.id,
    assetId: "",
    taskId: "",
    sourceTaskId: "",
    title: item.title || styleName || "官方精选",
    subtitle: item.subtitle || styleName,
    author: "官方精选",
    likes: "",
    coverClass: pickCoverClass(`${item.id}-${styleName}`),
    imageUrl: item.thumbnail_url || item.file_url,
    fileUrl: item.file_url,
    badge: item.badge || styleName,
    isFavorite: false,
    isFavorited: false,
    createdAtLabel: "",
    publishedAt: item.published_at || "",
    creatorName: item.creator_name || "幻头官方",
    styleName,
    isOfficial: true,
  };
}

module.exports = {
  normalizeTaskCreatePayload,
  formatDateLabel,
  pickCoverClass,
  getTaskTypeLabel,
  getTaskFrom,
  getTaskRatio,
  getTaskOutputCount,
  getTaskStyleName,
  toTaskExecutionViewModel,
  toAssetViewModel,
  toTaskCardViewModel,
  toAssetCardViewModel,
  toShowcaseCardViewModel,
};
