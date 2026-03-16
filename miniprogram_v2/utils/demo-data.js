const STORAGE_KEYS = {
  tasks: "huantou_demo_tasks_v1",
  favorites: "huantou_demo_favorites_v1",
};

const RULES = {
  signup_bonus: 100,
  daily_bonus: 12,
  txt2img_cost: 20,
  img2img_cost: 18,
  style_transfer_cost: 22,
};

const USER = {
  id: "HT-2026",
  nickname: "桃桃同学",
  signature: "把日常瞬间，变成温柔头像。",
  level: "暖光会员",
  pointsBalance: 1250,
};

const QUICK_ACTIONS = [
  { key: "image-edit", glyph: "换", label: "换头像", desc: "上传后微调" },
  { key: "create-menu", glyph: "灵", label: "灵感集", desc: "看风格趋势" },
  { key: "text-generate", glyph: "绘", label: "AI绘画", desc: "一句话生成" },
  { key: "profile", glyph: "我", label: "个人页", desc: "作品与会员" },
];

const HOME_TAGS = ["推荐", "二次元", "3D艺术", "复古油画"];

const STYLE_CARDS = [
  { id: "cyber", name: "赛博肖像", desc: "霓虹科技感", coverClass: "cover-night", hot: true },
  { id: "pixar", name: "皮克斯风", desc: "治愈系 3D 动画", coverClass: "cover-cream" },
  { id: "sketch", name: "艺术素描", desc: "极简炭笔线条", coverClass: "cover-mocha" },
  { id: "oil", name: "古典油画", desc: "暖棕复古质感", coverClass: "cover-sunset" },
];

const POINT_PACKAGES = [
  { id: "welcome", name: "新人礼包", points: 500, bonus: 100, price: "¥9.9", highlight: true },
  { id: "basic", name: "基础版", points: 1200, bonus: 180, price: "¥19.9" },
  { id: "pro", name: "专业版", points: 3000, bonus: 600, price: "¥49.9" },
];

const SERVICE_CONTENT = {
  help: {
    title: "使用帮助",
    subtitle: "3 步做出好看的头像",
    blocks: [
      { title: "提示词尽量具体", text: "人物、服装、背景、光线、风格写清楚，结果会稳定很多。" },
      { title: "先从灵感卡片开始", text: "先挑一个你喜欢的风格，再补充角色细节，成功率更高。" },
      { title: "结果页可以继续细修", text: "后续接入后端后，你可以在结果页继续走精修和二次创作。" },
    ],
  },
  about: {
    title: "关于幻头",
    subtitle: "温暖、轻巧、专注头像创作",
    blocks: [
      { title: "产品定位", text: "一个弱社交、强创作的小程序，帮助用户快速产出好看的个人头像。" },
      { title: "设计风格", text: "米白底色、暖橙强调、柔和圆角和插画感卡片，尽量让创作过程无压力。" },
      { title: "当前状态", text: "这版前端先跑通完整视觉和交互流程，后面再平滑接入你现有的后端接口。" },
    ],
  },
  feedback: {
    title: "意见反馈",
    subtitle: "这页先保留给后续接入",
    blocks: [
      { title: "问题记录", text: "后面可接入图片审核、失败反馈、补偿积分和客服追踪。" },
      { title: "灵感收集", text: "也适合沉淀用户最想要的新风格、新模板和新玩法。" },
    ],
  },
  quota: {
    title: "额度说明",
    subtitle: "积分规则一眼看懂",
    blocks: [
      { title: "文生图", text: "默认消耗 20 积分，适合从零开始做头像概念。" },
      { title: "风格迁移", text: "默认消耗 22 积分，适合保留人物信息换风格。" },
      { title: "精修编辑", text: "默认消耗 18 积分，适合补背景、修局部和微调表达。" },
    ],
  },
};

function clone(data) {
  return JSON.parse(JSON.stringify(data));
}

function formatDate(ts) {
  const d = new Date(ts);
  const month = `${d.getMonth() + 1}`.padStart(2, "0");
  const day = `${d.getDate()}`.padStart(2, "0");
  const hour = `${d.getHours()}`.padStart(2, "0");
  const minute = `${d.getMinutes()}`.padStart(2, "0");
  return `${month}-${day} ${hour}:${minute}`;
}

function getFavoriteMap() {
  return wx.getStorageSync(STORAGE_KEYS.favorites) || {};
}

function setFavoriteMap(map) {
  wx.setStorageSync(STORAGE_KEYS.favorites, map);
}

function seedDemoState() {
  const current = wx.getStorageSync(STORAGE_KEYS.tasks);
  if (current && current.length) return;
  const now = Date.now();
  const seedTasks = [
    {
      id: "HT24031501",
      from: "text-generate",
      modeLabel: "AI 绘画",
      prompt: "暖色治愈感女生头像，米白背景，轻微胶片颗粒",
      styleName: "柔焦插画",
      ratio: "1:1",
      status: "succeeded",
      coverClass: "cover-sunset",
      createdAt: now - 1000 * 60 * 60 * 18,
      finishedAt: now - 1000 * 60 * 60 * 18 + 3200,
      outputs: [
        { id: "HT24031501-1", title: "暖阳头像", subtitle: "柔焦插画", coverClass: "cover-sunset", badge: "精选" },
        { id: "HT24031501-2", title: "晨雾微光", subtitle: "柔和奶油底", coverClass: "cover-cream" },
      ],
    },
    {
      id: "HT24031502",
      from: "image-reference",
      modeLabel: "风格迁移",
      prompt: "保留人物神态，换成童话油画风",
      styleName: "古典油画",
      ratio: "4:5",
      status: "succeeded",
      coverClass: "cover-mocha",
      createdAt: now - 1000 * 60 * 60 * 8,
      finishedAt: now - 1000 * 60 * 60 * 8 + 3800,
      outputs: [
        { id: "HT24031502-1", title: "午后油画", subtitle: "古典油画", coverClass: "cover-mocha", badge: "热门" },
        { id: "HT24031502-2", title: "森系回眸", subtitle: "复古暖调", coverClass: "cover-forest" },
      ],
    },
  ];
  wx.setStorageSync(STORAGE_KEYS.tasks, seedTasks);
  wx.setStorageSync(STORAGE_KEYS.favorites, {
    "HT24031501-1": true,
  });
}

function listTasks() {
  seedDemoState();
  const tasks = wx.getStorageSync(STORAGE_KEYS.tasks) || [];
  return clone(tasks).sort((a, b) => b.createdAt - a.createdAt).map((task) => ({
    ...task,
    createdAtLabel: formatDate(task.createdAt),
    finishedAtLabel: task.finishedAt ? formatDate(task.finishedAt) : "",
  }));
}

function saveTasks(tasks) {
  wx.setStorageSync(STORAGE_KEYS.tasks, tasks);
}

function createDemoTask(payload) {
  seedDemoState();
  const now = Date.now();
  const id = `HT${String(now).slice(-8)}`;
  const task = {
    id,
    from: payload.from,
    modeLabel: payload.modeLabel,
    prompt: payload.prompt || "",
    negativePrompt: payload.negativePrompt || "",
    styleName: payload.styleName || "暖色插画",
    ratio: payload.ratio || "1:1",
    status: "running",
    coverClass: payload.coverClass || "cover-sunset",
    createdAt: now,
    finishedAt: 0,
    inputImageUrl: payload.inputImageUrl || "",
    referenceImageUrl: payload.referenceImageUrl || "",
    editTool: payload.editTool || "",
    outputs: buildOutputs({
      from: payload.from,
      styleName: payload.styleName,
      coverClass: payload.coverClass,
      inputImageUrl: payload.inputImageUrl,
    }, id),
  };
  const tasks = listTasks();
  tasks.unshift(task);
  saveTasks(tasks);
  return task;
}

function buildOutputs(payload, id) {
  const coverClass = payload.coverClass || "cover-sunset";
  const styleName = payload.styleName || "暖色插画";
  const outputs = [
    {
      id: `${id}-1`,
      title: "主推荐图",
      subtitle: styleName,
      coverClass,
      badge: "主推",
      imageUrl: payload.inputImageUrl || "",
    },
    {
      id: `${id}-2`,
      title: "柔光版本",
      subtitle: "更适合作为社交头像",
      coverClass: coverClass === "cover-sunset" ? "cover-cream" : "cover-sunset",
    },
    {
      id: `${id}-3`,
      title: "故事感版本",
      subtitle: "背景氛围更强",
      coverClass: payload.from === "image-reference" ? "cover-forest" : "cover-night",
    },
  ];
  return outputs;
}

function completeDemoTask(taskId) {
  const tasks = listTasks();
  const target = tasks.find((item) => item.id === taskId);
  if (!target) return null;
  target.status = "succeeded";
  target.finishedAt = Date.now();
  saveTasks(tasks);
  return {
    ...target,
    createdAtLabel: formatDate(target.createdAt),
    finishedAtLabel: formatDate(target.finishedAt),
  };
}

function getTaskById(taskId) {
  const tasks = listTasks();
  return tasks.find((item) => item.id === taskId) || null;
}

function listPortfolioItems() {
  const favorites = getFavoriteMap();
  const baseItems = [
    { id: "seed-1", title: "初雪的森林", author: "画师小桃", likes: "1.2k", coverClass: "cover-peach", badge: "推荐" },
    { id: "seed-2", title: "怀旧午后", author: "暖阳", likes: "2.1k", coverClass: "cover-forest" },
    { id: "seed-3", title: "星空下的少年", author: "梦旅人", likes: "1.5k", coverClass: "cover-night" },
    { id: "seed-4", title: "奶油晨光", author: "阿和", likes: "980", coverClass: "cover-cream", badge: "新作" },
  ];

  const taskItems = listTasks()
    .filter((task) => task.status === "succeeded")
    .map((task) => ({
      id: task.outputs[0].id,
      taskId: task.id,
      title: task.outputs[0].title,
      author: "幻头生成",
      likes: "收藏",
      coverClass: task.outputs[0].coverClass,
      imageUrl: task.outputs[0].imageUrl || "",
      badge: task.styleName,
      isFavorite: !!favorites[task.outputs[0].id],
    }));

  return [...taskItems, ...baseItems].map((item) => ({
    ...item,
    isFavorite: !!favorites[item.id],
  }));
}

function toggleFavorite(id) {
  const favorites = getFavoriteMap();
  favorites[id] = !favorites[id];
  setFavoriteMap(favorites);
  return !!favorites[id];
}

function getUserProfile() {
  const works = listTasks().filter((item) => item.status === "succeeded").length + 4;
  const favorites = Object.values(getFavoriteMap()).filter(Boolean).length;
  return {
    ...clone(USER),
    works,
    favorites,
  };
}

function getPointsViewModel() {
  return {
    balance: USER.pointsBalance,
    rules: clone(RULES),
    packages: clone(POINT_PACKAGES),
    ledgers: [
      { id: "l1", title: "每日签到", reason: "连续签到奖励", delta: +12, time: "今天 09:10" },
      { id: "l2", title: "风格迁移", reason: "童话油画头像", delta: -22, time: "昨天 21:06" },
      { id: "l3", title: "文本生成", reason: "暖色插画头像", delta: -20, time: "昨天 18:24" },
      { id: "l4", title: "开屏赠送", reason: "新人礼包", delta: +100, time: "03-12 10:03" },
    ],
  };
}

function getHomeViewModel() {
  return {
    user: clone(USER),
    quickActions: clone(QUICK_ACTIONS),
    tags: clone(HOME_TAGS),
    gallery: listPortfolioItems().slice(0, 4),
  };
}

function getCreateModes() {
  return [
    {
      key: "text",
      title: "AI 文生图",
      subtitle: "输入一句描述，快速生成新头像",
      glyph: "绘",
      page: "/pages/text-generate/index",
      coverClass: "cover-sunset",
    },
    {
      key: "transfer",
      title: "风格迁移",
      subtitle: "上传照片，切换成油画、3D 或赛博风格",
      glyph: "转",
      page: "/pages/image-reference/index",
      coverClass: "cover-mocha",
    },
    {
      key: "retouch",
      title: "AI 精修",
      subtitle: "补背景、修局部、加氛围，一页完成",
      glyph: "修",
      page: "/pages/image-edit/index",
      coverClass: "cover-cream",
    },
  ];
}

function getStyleCards() {
  return clone(STYLE_CARDS);
}

function getServiceContent(type) {
  return clone(SERVICE_CONTENT[type] || SERVICE_CONTENT.about);
}

module.exports = {
  RULES,
  USER,
  seedDemoState,
  getHomeViewModel,
  getCreateModes,
  getStyleCards,
  createDemoTask,
  completeDemoTask,
  getTaskById,
  listTasks,
  listPortfolioItems,
  toggleFavorite,
  getUserProfile,
  getPointsViewModel,
  getServiceContent,
};
