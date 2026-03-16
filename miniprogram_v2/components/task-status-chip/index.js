Component({
  properties: {
    status: { type: String, value: "" },
  },
  methods: {
    textFor(status) {
      const map = {
        queued: "排队",
        running: "生成中",
        succeeded: "成功",
        failed: "失败",
        canceled: "取消",
      };
      return map[status] || status || "-";
    },
  },
});
