const { getServiceContent } = require("../../utils/demo-data");

Page({
  data: {
    pageTitle: "服务说明",
    pageSubtitle: "功能说明页",
    blocks: [],
  },

  onLoad(query) {
    const type = (query && query.type) || "about";
    const data = getServiceContent(type);
    this.setData({
      pageTitle: data.title,
      pageSubtitle: data.subtitle,
      blocks: data.blocks,
    });
  },
});
