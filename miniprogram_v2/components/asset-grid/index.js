Component({
  properties: {
    items: { type: Array, value: [] },
    showFavorite: { type: Boolean, value: true },
    selectMode: { type: Boolean, value: false },
  },
  methods: {
    onPreview(e) {
      this.triggerEvent("preview", { item: e.currentTarget.dataset.item });
    },
    onFavorite(e) {
      this.triggerEvent("favorite", { item: e.currentTarget.dataset.item });
    },
    onSelect(e) {
      this.triggerEvent("select", { item: e.currentTarget.dataset.item });
    },
  },
});
