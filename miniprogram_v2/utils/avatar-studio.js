function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

const STYLE_TEMPLATES = [
  {
    id: "warm-illustration",
    name: "暖光插画",
    desc: "奶油光影和柔和笔触，更适合作为日常头像",
    badge: "主推",
    coverClass: "cover-cream",
  },
  {
    id: "pixar-heal",
    name: "3D 治愈",
    desc: "圆润立体、表情更亲和，适合社交头像",
    badge: "热门",
    coverClass: "cover-sunset",
  },
  {
    id: "retro-oil",
    name: "复古油画",
    desc: "暖棕复古氛围，人物层次更厚重",
    badge: "高级",
    coverClass: "cover-mocha",
  },
  {
    id: "forest-soft",
    name: "森系清透",
    desc: "轻氧绿色调，适合清新自然的人像",
    badge: "清新",
    coverClass: "cover-forest",
  },
  {
    id: "anime-soft",
    name: "二次元柔焦",
    desc: "线条细腻，适合偏年轻感的头像表达",
    badge: "轻漫",
    coverClass: "cover-peach",
  },
  {
    id: "night-fashion",
    name: "夜色质感",
    desc: "高对比夜景氛围，更有记忆点",
    badge: "个性",
    coverClass: "cover-night",
  },
];

const SHOWCASE_FALLBACK = [
  {
    id: "case-1",
    title: "暖光插画头像",
    author: "优秀案例",
    likes: "去生成",
    coverClass: "cover-cream",
    badge: "暖光插画",
  },
  {
    id: "case-2",
    title: "3D 治愈头像",
    author: "优秀案例",
    likes: "去生成",
    coverClass: "cover-sunset",
    badge: "3D 治愈",
  },
  {
    id: "case-3",
    title: "森系清透头像",
    author: "优秀案例",
    likes: "去生成",
    coverClass: "cover-forest",
    badge: "森系清透",
  },
  {
    id: "case-4",
    title: "夜色质感头像",
    author: "优秀案例",
    likes: "去生成",
    coverClass: "cover-night",
    badge: "夜色质感",
  },
];

const TEXT_STYLE_OPTIONS = [
  {
    id: "none",
    name: "无",
    desc: "只按描述生成，不额外套风格模板",
    coverClass: "cover-cream",
  },
  {
    id: "warm-illustration",
    name: "暖光插画",
    desc: "柔和奶油光感",
    coverClass: "cover-peach",
  },
  {
    id: "pixar-heal",
    name: "3D 治愈",
    desc: "圆润立体质感",
    coverClass: "cover-sunset",
  },
  {
    id: "forest-soft",
    name: "森系清透",
    desc: "轻氧绿色调",
    coverClass: "cover-forest",
  },
  {
    id: "anime-soft",
    name: "二次元柔焦",
    desc: "线条细致、偏年轻感",
    coverClass: "cover-cream",
  },
];

const TEXT_PROMPT_SAMPLES = [
  {
    id: "sample-1",
    title: "职场头像",
    prompt: "高级感商务头像，米白背景，干净构图，轻胶片质感，适合作为微信头像",
    styleName: "无",
    coverClass: "cover-cream",
  },
  {
    id: "sample-2",
    title: "温暖插画",
    prompt: "温暖阳光里的女生头像，柔和笑容，插画风，浅米色背景，适合作为社交头像",
    styleName: "暖光插画",
    coverClass: "cover-peach",
  },
  {
    id: "sample-3",
    title: "清新森系",
    prompt: "森系清透感头像，轻氧绿色调，人物居中，氛围自然治愈",
    styleName: "森系清透",
    coverClass: "cover-forest",
  },
  {
    id: "sample-4",
    title: "3D 治愈",
    prompt: "圆润 3D 治愈系头像，奶油光影，人物表情自然，适合头像展示",
    styleName: "3D 治愈",
    coverClass: "cover-sunset",
  },
];

const ADVANCED_FEATURES = [
  {
    key: "smart-edit",
    title: "智能修改",
    desc: "局部优化发型、补光、细节氛围",
    badge: "进阶",
  },
  {
    key: "background-replace",
    title: "背景替换",
    desc: "一键更换为更适合头像的场景",
    badge: "进阶",
  },
  {
    key: "reference-generate",
    title: "参考图生成",
    desc: "基于参考图继续延展更多版本",
    badge: "火山 API",
  },
  {
    key: "decorate",
    title: "贴纸 / 头像框 / 文本",
    desc: "节日挂件和头像装饰统一在这里",
    badge: "装饰",
  },
];

function getStyleTemplates() {
  return clone(STYLE_TEMPLATES);
}

function getShowcaseFallback() {
  return clone(SHOWCASE_FALLBACK);
}

function getTextStyleOptions() {
  return clone(TEXT_STYLE_OPTIONS);
}

function getTextPromptSamples() {
  return clone(TEXT_PROMPT_SAMPLES);
}

function getAdvancedFeatures() {
  return clone(ADVANCED_FEATURES);
}

module.exports = {
  getStyleTemplates,
  getShowcaseFallback,
  getTextStyleOptions,
  getTextPromptSamples,
  getAdvancedFeatures,
};
