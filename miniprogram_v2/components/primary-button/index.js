Component({
  properties: {
    text: { type: String, value: "按钮" },
    loading: { type: Boolean, value: false },
    disabled: { type: Boolean, value: false },
  },
  methods: {
    onTap() {
      if (this.data.disabled || this.data.loading) return;
      this.triggerEvent("tap");
    },
  },
});
