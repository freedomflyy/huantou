const { ensureLogin } = require("../../utils/guard");
const { get } = require("../../utils/request");

const OUTPUT_SIZE = 1024;
const PREVIEW_RPX = 356;
const STICKER_SIZE_RPX = 92;
const TEXT_BOX_HEIGHT_RPX = 58;
const TEXT_BOX_MIN_WIDTH_RPX = 132;
const TEXT_BOX_PADDING_RPX = 22;
const TEXT_FONT_RPX = 28;
const FRAME_SCALE = 1.12;

const TABS = [
  { key: "stickers", label: "贴纸", glyph: "贴" },
  { key: "text", label: "文字", glyph: "字" },
  { key: "frames", label: "边框", glyph: "框" },
];

const DEFAULT_TEXT_COLORS = [
  { label: "奶油白", value: "#fff8f0" },
  { label: "蜜桃橙", value: "#f56a21" },
  { label: "暖棕色", value: "#8a5f47" },
  { label: "夜空蓝", value: "#334a69" },
];

function pxFromRpx(rpx) {
  const systemInfo = wx.getSystemInfoSync();
  return (systemInfo.windowWidth / 750) * rpx;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function buildPlaceholders(prefix, count, type) {
  return Array.from({ length: count }).map((_, index) => ({
    id: `${prefix}-${index + 1}`,
    title: type === "frame" ? `边框 ${index + 1}` : `贴纸 ${index + 1}`,
  }));
}

function isLocalPath(value) {
  if (!value) return false;
  return (
    value.indexOf("wxfile://") === 0 ||
    value.indexOf("http://tmp/") === 0 ||
    value.indexOf("/") === 0
  );
}

function downloadFile(url) {
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

function saveToAlbum(filePath) {
  return new Promise((resolve, reject) => {
    wx.saveImageToPhotosAlbum({
      filePath,
      success() {
        resolve();
      },
      fail(err) {
        reject(err || new Error("保存失败"));
      },
    });
  });
}

function buildInstanceId(materialId) {
  return `${materialId}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

function buildTextLayout(text, previewSize, currentPosition) {
  const safePreview = previewSize || pxFromRpx(PREVIEW_RPX);
  const textValue = (text || "").trim();
  const height = pxFromRpx(TEXT_BOX_HEIGHT_RPX);
  const minWidth = pxFromRpx(TEXT_BOX_MIN_WIDTH_RPX);
  const paddingX = pxFromRpx(TEXT_BOX_PADDING_RPX);
  const approxFont = pxFromRpx(TEXT_FONT_RPX);
  const width = clamp(
    Math.max(minWidth, textValue.length * approxFont + paddingX * 2),
    minWidth,
    safePreview * 0.8
  );
  const maxX = Math.max(0, safePreview - width);
  const maxY = Math.max(0, safePreview - height);
  const hasCurrent = currentPosition && typeof currentPosition.x === "number" && typeof currentPosition.y === "number";
  const x = hasCurrent ? clamp(currentPosition.x, 0, maxX) : Math.round((safePreview - width) / 2);
  const y = hasCurrent
    ? clamp(currentPosition.y, 0, maxY)
    : clamp(safePreview - height - pxFromRpx(26), 0, maxY);
  return {
    textBoxWidth: width,
    textBoxHeight: height,
    textX: x,
    textY: y,
  };
}

function roundRect(ctx, x, y, width, height, radius) {
  const safeRadius = Math.min(radius, width / 2, height / 2);
  ctx.beginPath();
  ctx.moveTo(x + safeRadius, y);
  ctx.lineTo(x + width - safeRadius, y);
  ctx.arcTo(x + width, y, x + width, y + safeRadius, safeRadius);
  ctx.lineTo(x + width, y + height - safeRadius);
  ctx.arcTo(x + width, y + height, x + width - safeRadius, y + height, safeRadius);
  ctx.lineTo(x + safeRadius, y + height);
  ctx.arcTo(x, y + height, x, y + height - safeRadius, safeRadius);
  ctx.lineTo(x, y + safeRadius);
  ctx.arcTo(x, y, x + safeRadius, y, safeRadius);
  ctx.closePath();
}

Page({
  data: {
    taskId: "",
    imageUrl: "",
    previewSize: 0,
    activeTab: "stickers",
    activeCategory: "动物",
    tabs: TABS,
    categories: ["动物", "植物", "几何", "表情", "装饰", "日常"],
    stickerGroups: [],
    recentStickers: buildPlaceholders("recent", 4, "sticker"),
    stickerItems: buildPlaceholders("sticker", 8, "sticker"),
    lastStickerMaterialId: "",
    placedStickers: [],
    selectedStickerId: "",
    textContent: "",
    textColorOptions: DEFAULT_TEXT_COLORS,
    activeTextColor: DEFAULT_TEXT_COLORS[1].label,
    activeTextColorValue: DEFAULT_TEXT_COLORS[1].value,
    textBoxWidth: 0,
    textBoxHeight: 0,
    textX: 0,
    textY: 0,
    frameItems: buildPlaceholders("frame", 6, "frame"),
    selectedFrameId: "",
    selectedFrameUrl: "",
    selectedFrameTitle: "",
    statusText: "贴纸可拖拽，边框点击即切换，导出会生成完整装饰图。",
    exporting: false,
  },

  onLoad(query) {
    const previewSize = pxFromRpx(PREVIEW_RPX);
    this.setData({
      previewSize,
      taskId: query.taskId || "",
      imageUrl: query.imageUrl ? decodeURIComponent(query.imageUrl) : "",
      ...buildTextLayout("", previewSize),
    });
  },

  async onShow() {
    const ok = await ensureLogin();
    if (!ok) return;
    await this.loadMaterials();
    if (this.data.taskId && !isLocalPath(this.data.imageUrl)) {
      await this.loadPreview();
    }
  },

  setStatusText() {
    const stickerCount = this.data.placedStickers.length;
    const parts = [];
    if (!this.data.imageUrl) {
      parts.push("点击头像预览区上传一张头像，再开始装饰");
    }
    if (this.data.selectedFrameTitle) {
      parts.push(`当前边框：${this.data.selectedFrameTitle}`);
    }
    if (stickerCount) {
      parts.push(`已添加 ${stickerCount} 个贴纸，可直接拖拽调整位置`);
    }
    if (this.data.textContent) {
      parts.push(`文字已启用：${this.data.textContent}`);
    }
    this.setData({
      statusText: parts.length ? parts.join("，") : "贴纸和文字都可拖拽，边框点击即切换，导出会生成完整装饰图。",
    });
  },

  async loadMaterials() {
    try {
      const res = await get("/materials");
      const stickerGroups = (res.sticker_groups || []).map((group) => ({
        id: group.id,
        title: group.title,
        items: (group.items || []).map((item) => ({
          id: item.id,
          title: item.title,
          fileUrl: item.file_url,
        })),
      }));
      const categories = stickerGroups.length ? stickerGroups.map((group) => group.title) : this.data.categories;
      const activeCategory = categories.includes(this.data.activeCategory) ? this.data.activeCategory : categories[0];
      const currentGroup = stickerGroups.find((group) => group.title === activeCategory) || stickerGroups[0];
      const frameItems = (res.frame_items || []).map((item) => ({
        id: item.id,
        title: item.title,
        fileUrl: item.file_url,
      }));
      const recentStickers = stickerGroups.flatMap((group) => group.items).slice(0, 4);

      this.setData({
        stickerGroups,
        categories,
        activeCategory,
        recentStickers: recentStickers.length ? recentStickers : this.data.recentStickers,
        stickerItems: currentGroup && currentGroup.items.length ? currentGroup.items : this.data.stickerItems,
        frameItems: frameItems.length ? frameItems : this.data.frameItems,
      });
      this.setStatusText();
    } catch (err) {
      this.setStatusText();
    }
  },

  async loadPreview() {
    try {
      const [task, assetsRes] = await Promise.all([
        get(`/tasks/${this.data.taskId}`),
        get("/assets?limit=100"),
      ]);
      const outputs = (assetsRes.items || []).filter((item) => item.source_task_id === this.data.taskId);
      const imageUrl = outputs[0]
        ? (outputs[0].thumbnail_url || outputs[0].file_url)
        : (task.input_image_url || "");
      if (imageUrl) {
        this.setData({ imageUrl });
      }
    } catch (err) {
      // Keep current imageUrl when preview refresh fails.
    }
  },

  findStickerMaterial(id) {
    const groups = this.data.stickerGroups || [];
    for (let i = 0; i < groups.length; i += 1) {
      const item = (groups[i].items || []).find((entry) => entry.id === id);
      if (item) return item;
    }
    return (this.data.recentStickers || []).find((entry) => entry.id === id)
      || (this.data.stickerItems || []).find((entry) => entry.id === id)
      || null;
  },

  addRecentSticker(material) {
    if (!material) return;
    const recent = [material].concat((this.data.recentStickers || []).filter((item) => item.id !== material.id)).slice(0, 4);
    this.setData({ recentStickers: recent });
  },

  onTabTap(e) {
    const tab = e.currentTarget.dataset.tab;
    if (!tab) return;
    this.setData({ activeTab: tab });
  },

  syncTextLayout(text, preservePosition) {
    const currentPosition = preservePosition ? { x: this.data.textX, y: this.data.textY } : null;
    return buildTextLayout(text, this.data.previewSize || pxFromRpx(PREVIEW_RPX), currentPosition);
  },

  openCropFlow(filePath) {
    if (!filePath) return;
    wx.navigateTo({
      url: "/pages/avatar-crop/index?targetField=imageUrl&scene=avatar-decorate",
      events: {
        cropped: ({ filePath: croppedFilePath }) => {
          if (!croppedFilePath) return;
          this.setData({
            imageUrl: croppedFilePath,
            taskId: "",
          });
          this.setStatusText();
          wx.showToast({ title: "头像已更新", icon: "success" });
        },
      },
      success: (navRes) => {
        navRes.eventChannel.emit("cropSource", {
          filePath,
          targetField: "imageUrl",
          scene: "avatar-decorate",
        });
      },
    });
  },

  chooseAvatarImage() {
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

  onCategoryTap(e) {
    const category = e.currentTarget.dataset.category;
    if (!category) return;
    const currentGroup = (this.data.stickerGroups || []).find((group) => group.title === category);
    this.setData({
      activeCategory: category,
      stickerItems: currentGroup && currentGroup.items.length ? currentGroup.items : this.data.stickerItems,
    });
  },

  onTextInput(e) {
    const value = e.detail.value || "";
    this.setData({
      textContent: value,
      ...this.syncTextLayout(value, Boolean(this.data.textContent)),
    });
    this.setStatusText();
  },

  onTextLayerChange(e) {
    this.setData({
      textX: e.detail.x,
      textY: e.detail.y,
    });
  },

  onTextColorTap(e) {
    const label = e.currentTarget.dataset.label;
    const value = e.currentTarget.dataset.value;
    if (!label || !value) return;
    this.setData({
      activeTextColor: label,
      activeTextColorValue: value,
    });
  },

  onStickerTileTap(e) {
    if (!this.data.imageUrl) {
      wx.showToast({ title: "请先生成或上传头像", icon: "none" });
      return;
    }
    const id = e.currentTarget.dataset.id;
    const material = this.findStickerMaterial(id);
    if (!material || !material.fileUrl) return;
    const previewSize = this.data.previewSize || pxFromRpx(PREVIEW_RPX);
    const stickerSize = pxFromRpx(STICKER_SIZE_RPX);
    const nextSticker = {
      instanceId: buildInstanceId(material.id),
      materialId: material.id,
      title: material.title,
      fileUrl: material.fileUrl,
      x: Math.round((previewSize - stickerSize) / 2),
      y: Math.round((previewSize - stickerSize) / 2),
      size: stickerSize,
      scale: 1,
    };
    const placedStickers = (this.data.placedStickers || []).concat(nextSticker);
    this.addRecentSticker(material);
    this.setData({
      placedStickers,
      selectedStickerId: nextSticker.instanceId,
      lastStickerMaterialId: material.id,
      activeTab: "stickers",
    });
    this.setStatusText();
  },

  onStickerTap(e) {
    const id = e.currentTarget.dataset.id;
    if (!id) return;
    this.setData({ selectedStickerId: id });
  },

  onStickerChange(e) {
    const id = e.currentTarget.dataset.id;
    const placedStickers = (this.data.placedStickers || []).slice();
    const index = placedStickers.findIndex((item) => item.instanceId === id);
    if (index < 0) return;
    placedStickers[index] = {
      ...placedStickers[index],
      x: e.detail.x,
      y: e.detail.y,
    };
    this.setData({ placedStickers });
  },

  onStickerScale(e) {
    const id = e.currentTarget.dataset.id;
    const placedStickers = (this.data.placedStickers || []).slice();
    const index = placedStickers.findIndex((item) => item.instanceId === id);
    if (index < 0) return;
    placedStickers[index] = {
      ...placedStickers[index],
      scale: clamp(Number(e.detail.scale || 1), 0.6, 2.4),
    };
    this.setData({ placedStickers });
  },

  onRemoveSticker(e) {
    const targetId = (e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.id) || this.data.selectedStickerId;
    if (!targetId) return;
    const placedStickers = (this.data.placedStickers || []).filter((item) => item.instanceId !== targetId);
    this.setData({
      placedStickers,
      selectedStickerId: placedStickers[0] ? placedStickers[0].instanceId : "",
    });
    this.setStatusText();
  },

  onFrameTap(e) {
    if (!this.data.imageUrl) {
      wx.showToast({ title: "请先生成或上传头像", icon: "none" });
      return;
    }
    const id = e.currentTarget.dataset.id;
    const item = (this.data.frameItems || []).find((entry) => entry.id === id);
    if (!item) return;
    const isSame = this.data.selectedFrameId === id;
    this.setData({
      selectedFrameId: isSame ? "" : id,
      selectedFrameUrl: isSame ? "" : (item.fileUrl || ""),
      selectedFrameTitle: isSame ? "" : item.title,
      activeTab: "frames",
    });
    this.setStatusText();
  },

  onResetTap() {
    this.setData({
      placedStickers: [],
      selectedStickerId: "",
      lastStickerMaterialId: "",
      selectedFrameId: "",
      selectedFrameUrl: "",
      selectedFrameTitle: "",
      textContent: "",
      activeTextColor: DEFAULT_TEXT_COLORS[1].label,
      activeTextColorValue: DEFAULT_TEXT_COLORS[1].value,
      ...this.syncTextLayout("", false),
    });
    this.setStatusText();
  },

  async ensureLocalPath(src) {
    if (!src) return "";
    if (isLocalPath(src)) return src;
    return downloadFile(src);
  },

  async onSaveTap() {
    if (this.data.exporting) return;
    if (!this.data.imageUrl) {
      wx.showToast({ title: "请先准备一张头像", icon: "none" });
      return;
    }

    this.setData({ exporting: true });
    wx.showLoading({ title: "正在导出", mask: true });

    try {
      const imagePath = await this.ensureLocalPath(this.data.imageUrl);
      const framePath = this.data.selectedFrameUrl ? await this.ensureLocalPath(this.data.selectedFrameUrl) : "";
      const stickerPaths = await Promise.all(
        (this.data.placedStickers || []).map((item) => this.ensureLocalPath(item.fileUrl))
      );

      const ctx = wx.createCanvasContext("decorateCanvas", this);
      ctx.clearRect(0, 0, OUTPUT_SIZE, OUTPUT_SIZE);

      ctx.save();
      ctx.beginPath();
      ctx.arc(OUTPUT_SIZE / 2, OUTPUT_SIZE / 2, OUTPUT_SIZE / 2, 0, Math.PI * 2);
      ctx.clip();
      ctx.drawImage(imagePath, 0, 0, OUTPUT_SIZE, OUTPUT_SIZE);
      ctx.restore();

      const previewSize = this.data.previewSize || pxFromRpx(PREVIEW_RPX);
      (this.data.placedStickers || []).forEach((item, index) => {
        const localPath = stickerPaths[index];
        const drawSize = ((item.size * item.scale) / previewSize) * OUTPUT_SIZE;
        const drawX = (item.x / previewSize) * OUTPUT_SIZE;
        const drawY = (item.y / previewSize) * OUTPUT_SIZE;
        if (localPath) {
          ctx.drawImage(localPath, drawX, drawY, drawSize, drawSize);
        }
      });

      if (this.data.textContent) {
        const textDrawX = (this.data.textX / previewSize) * OUTPUT_SIZE;
        const textDrawY = (this.data.textY / previewSize) * OUTPUT_SIZE;
        const textDrawWidth = (this.data.textBoxWidth / previewSize) * OUTPUT_SIZE;
        const textDrawHeight = (this.data.textBoxHeight / previewSize) * OUTPUT_SIZE;
        ctx.save();
        roundRect(ctx, textDrawX, textDrawY, textDrawWidth, textDrawHeight, textDrawHeight / 2);
        ctx.setFillStyle("rgba(255, 255, 255, 0.72)");
        ctx.fill();
        ctx.setFillStyle(this.data.activeTextColorValue);
        ctx.setTextAlign("center");
        ctx.setTextBaseline("middle");
        ctx.setFontSize(Math.max(42, Math.round(textDrawHeight * 0.44)));
        ctx.fillText(
          this.data.textContent,
          textDrawX + textDrawWidth / 2,
          textDrawY + textDrawHeight / 2
        );
        ctx.restore();
      }

      if (framePath) {
        const frameSize = OUTPUT_SIZE * FRAME_SCALE;
        const frameOffset = (frameSize - OUTPUT_SIZE) / 2;
        ctx.drawImage(framePath, -frameOffset, -frameOffset, frameSize, frameSize);
      }

      await new Promise((resolve) => ctx.draw(false, resolve));

      const tempFilePath = await new Promise((resolve, reject) => {
        wx.canvasToTempFilePath(
          {
            canvasId: "decorateCanvas",
            fileType: "png",
            quality: 1,
            destWidth: OUTPUT_SIZE,
            destHeight: OUTPUT_SIZE,
            success: (res) => resolve(res.tempFilePath),
            fail: reject,
          },
          this
        );
      });

      await saveToAlbum(tempFilePath);
      wx.showToast({ title: "已导出到相册", icon: "success" });
    } catch (err) {
      const msg = (err && err.errMsg) || err.message || "";
      if (msg.indexOf("auth deny") >= 0 || msg.indexOf("scope.writePhotosAlbum") >= 0) {
        wx.showModal({
          title: "需要相册权限",
          content: "保存装饰头像需要开启相册权限，请在设置中允许后重试。",
          confirmText: "去设置",
          success: (res) => {
            if (res.confirm) {
              wx.openSetting();
            }
          },
        });
      } else {
        wx.showToast({ title: err.message || "导出失败", icon: "none" });
      }
    } finally {
      wx.hideLoading();
      this.setData({ exporting: false });
    }
  },

  previewImage() {
    if (!this.data.imageUrl) return;
    wx.previewImage({
      current: this.data.imageUrl,
      urls: [this.data.imageUrl],
    });
  },
});
