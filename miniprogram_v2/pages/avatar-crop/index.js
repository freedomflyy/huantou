const OUTPUT_SIZE = 1024;
const STAGE_RPX = 620;
const INITIAL_CROP_RATIO = 0.72;
const MIN_CROP_RPX = 180;

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function pxFromRpx(rpx) {
  const systemInfo = wx.getSystemInfoSync();
  return (systemInfo.windowWidth / 750) * rpx;
}

Page({
  data: {
    scene: "",
    targetField: "inputImageUrl",
    sourceFilePath: "",
    stageSize: 0,
    imageWidth: 0,
    imageHeight: 0,
    displayWidth: 0,
    displayHeight: 0,
    imageLeft: 0,
    imageTop: 0,
    cropX: 0,
    cropY: 0,
    cropSize: 0,
    minCropSize: 0,
    ready: false,
    processing: false,
    cropSizeLabel: "0 x 0",
  },

  onLoad(query) {
    this.touchState = null;
    this.eventChannel = this.getOpenerEventChannel();
    if (this.eventChannel) {
      this.eventChannel.on("cropSource", (payload = {}) => {
        this.initSource({
          filePath: payload.filePath || "",
          targetField: payload.targetField || query.targetField || "inputImageUrl",
          scene: payload.scene || query.scene || "",
        });
      });
    }
    this.setData({
      stageSize: pxFromRpx(STAGE_RPX),
      targetField: query.targetField || "inputImageUrl",
      scene: query.scene || "",
    });
  },

  async initSource({ filePath, targetField, scene }) {
    if (!filePath) {
      wx.showToast({ title: "图片读取失败", icon: "none" });
      return;
    }

    try {
      const info = await new Promise((resolve, reject) => {
        wx.getImageInfo({
          src: filePath,
          success: resolve,
          fail: reject,
        });
      });

      const stageSize = this.data.stageSize || pxFromRpx(STAGE_RPX);
      const imageWidth = info.width || 1;
      const imageHeight = info.height || 1;
      const aspect = imageWidth / imageHeight;

      let displayWidth = stageSize;
      let displayHeight = stageSize;
      if (aspect >= 1) {
        displayHeight = stageSize / aspect;
      } else {
        displayWidth = stageSize * aspect;
      }

      const imageLeft = (stageSize - displayWidth) / 2;
      const imageTop = (stageSize - displayHeight) / 2;
      const minDimension = Math.min(displayWidth, displayHeight);
      const minCropSize = Math.min(minDimension, Math.max(pxFromRpx(MIN_CROP_RPX), minDimension * 0.35));
      const cropSize = clamp(minDimension * INITIAL_CROP_RATIO, minCropSize, minDimension);
      const cropX = imageLeft + (displayWidth - cropSize) / 2;
      const cropY = imageTop + (displayHeight - cropSize) / 2;

      this.setData({
        scene: scene || "",
        targetField: targetField || "inputImageUrl",
        sourceFilePath: filePath,
        imageWidth,
        imageHeight,
        displayWidth,
        displayHeight,
        imageLeft,
        imageTop,
        cropX,
        cropY,
        cropSize,
        minCropSize,
        ready: true,
      });
      this.updateCropLabel(cropSize);
    } catch (err) {
      wx.showToast({ title: "图片加载失败", icon: "none" });
    }
  },

  updateCropLabel(size) {
    const rounded = Math.round(size || this.data.cropSize || 0);
    this.setData({
      cropSizeLabel: `${rounded} x ${rounded}`,
    });
  },

  beginTouch(mode, touch) {
    this.touchState = {
      mode,
      startX: touch.pageX,
      startY: touch.pageY,
      originX: this.data.cropX,
      originY: this.data.cropY,
      originSize: this.data.cropSize,
    };
  },

  onCropTouchStart(e) {
    if (!this.data.ready) return;
    const touch = e.touches && e.touches[0];
    if (!touch) return;
    this.beginTouch("move", touch);
  },

  onResizeTouchStart(e) {
    if (!this.data.ready) return;
    const touch = e.touches && e.touches[0];
    if (!touch) return;
    this.beginTouch("resize", touch);
  },

  onTouchMove(e) {
    if (!this.touchState || !this.data.ready) return;
    const touch = e.touches && e.touches[0];
    if (!touch) return;

    const deltaX = touch.pageX - this.touchState.startX;
    const deltaY = touch.pageY - this.touchState.startY;

    if (this.touchState.mode === "move") {
      const maxX = this.data.imageLeft + this.data.displayWidth - this.data.cropSize;
      const maxY = this.data.imageTop + this.data.displayHeight - this.data.cropSize;
      this.setData({
        cropX: clamp(this.touchState.originX + deltaX, this.data.imageLeft, maxX),
        cropY: clamp(this.touchState.originY + deltaY, this.data.imageTop, maxY),
      });
      return;
    }

    if (this.touchState.mode === "resize") {
      const delta = Math.abs(deltaX) > Math.abs(deltaY) ? deltaX : deltaY;
      const maxSize = Math.min(
        this.data.imageLeft + this.data.displayWidth - this.data.cropX,
        this.data.imageTop + this.data.displayHeight - this.data.cropY
      );
      const nextSize = clamp(this.touchState.originSize + delta, this.data.minCropSize, maxSize);
      this.setData({ cropSize: nextSize });
      this.updateCropLabel(nextSize);
    }
  },

  onTouchEnd() {
    this.touchState = null;
  },

  async onConfirm() {
    if (this.data.processing || !this.data.ready || !this.data.sourceFilePath) return;
    this.setData({ processing: true });
    wx.showLoading({ title: "裁剪中", mask: true });

    try {
      const sourceX = clamp(
        ((this.data.cropX - this.data.imageLeft) / this.data.displayWidth) * this.data.imageWidth,
        0,
        this.data.imageWidth - 1
      );
      const sourceY = clamp(
        ((this.data.cropY - this.data.imageTop) / this.data.displayHeight) * this.data.imageHeight,
        0,
        this.data.imageHeight - 1
      );
      const sourceSize = clamp(
        (this.data.cropSize / this.data.displayWidth) * this.data.imageWidth,
        1,
        this.data.imageWidth - sourceX
      );
      const sourceHeight = clamp(
        (this.data.cropSize / this.data.displayHeight) * this.data.imageHeight,
        1,
        this.data.imageHeight - sourceY
      );

      const ctx = wx.createCanvasContext("cropCanvas", this);
      ctx.clearRect(0, 0, OUTPUT_SIZE, OUTPUT_SIZE);
      ctx.drawImage(
        this.data.sourceFilePath,
        sourceX,
        sourceY,
        sourceSize,
        sourceHeight,
        0,
        0,
        OUTPUT_SIZE,
        OUTPUT_SIZE
      );

      await new Promise((resolve) => ctx.draw(false, resolve));

      const tempFilePath = await new Promise((resolve, reject) => {
        wx.canvasToTempFilePath(
          {
            canvasId: "cropCanvas",
            fileType: "jpg",
            quality: 0.95,
            destWidth: OUTPUT_SIZE,
            destHeight: OUTPUT_SIZE,
            success: (res) => resolve(res.tempFilePath),
            fail: reject,
          },
          this
        );
      });

      if (this.eventChannel) {
        this.eventChannel.emit("cropped", {
          filePath: tempFilePath,
          targetField: this.data.targetField,
          scene: this.data.scene,
        });
      }
      wx.navigateBack();
    } catch (err) {
      wx.showToast({
        title: "裁剪失败，请重试",
        icon: "none",
      });
    } finally {
      wx.hideLoading();
      this.setData({ processing: false });
    }
  },

  onReset() {
    if (!this.data.ready) return;
    const minDimension = Math.min(this.data.displayWidth, this.data.displayHeight);
    const cropSize = clamp(minDimension * INITIAL_CROP_RATIO, this.data.minCropSize, minDimension);
    const cropX = this.data.imageLeft + (this.data.displayWidth - cropSize) / 2;
    const cropY = this.data.imageTop + (this.data.displayHeight - cropSize) / 2;
    this.setData({
      cropX,
      cropY,
      cropSize,
    });
    this.updateCropLabel(cropSize);
  },
});
