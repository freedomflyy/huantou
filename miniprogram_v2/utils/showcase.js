function hashCode(text) {
  const raw = String(text || "");
  let hash = 0;
  for (let i = 0; i < raw.length; i += 1) {
    hash = (hash << 5) - hash + raw.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
}

function getDayKey() {
  const now = new Date();
  const y = now.getFullYear();
  const m = `${now.getMonth() + 1}`.padStart(2, "0");
  const d = `${now.getDate()}`.padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function seededShuffle(items, seedText) {
  const list = (items || []).slice();
  let seed = hashCode(seedText);
  for (let i = list.length - 1; i > 0; i -= 1) {
    seed = (seed * 9301 + 49297) % 233280;
    const j = seed % (i + 1);
    [list[i], list[j]] = [list[j], list[i]];
  }
  return list;
}

function orderShowcaseItems(items, tab = "热门") {
  const list = (items || []).slice();
  if (!list.length) return list;
  const dayKey = getDayKey();
  if (tab === "最新") {
    return list.sort((a, b) => {
      const aTime = new Date(a.publishedAt || 0).getTime();
      const bTime = new Date(b.publishedAt || 0).getTime();
      return bTime - aTime;
    });
  }
  return seededShuffle(list, `hot-${dayKey}`);
}

module.exports = {
  orderShowcaseItems,
};
