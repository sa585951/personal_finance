// Preset trip covers. Keys match COVER_THEMES in models/trip_manager.py.
// Every colour keeps white text at a contrast ratio of at least 5.6:1.
export const TRIP_COVERS = [
  { key: "ocean", label: "海", color: "#1F5A73" },
  { key: "sunset", label: "夕陽", color: "#A84B26" },
  { key: "forest", label: "森林", color: "#3A6438" },
  { key: "night", label: "夜晚", color: "#2D3C6B" },
  { key: "sakura", label: "櫻花", color: "#9E3F63" },
  { key: "sand", label: "沙漠", color: "#7A5C2E" },
  { key: "alpine", label: "山湖", color: "#2F6B6A" },
  { key: "stone", label: "石板", color: "#52575E" },
];

const BY_KEY = Object.fromEntries(TRIP_COVERS.map((cover) => [cover.key, cover]));

/** A trip without a chosen cover still gets a stable colour from its id. */
export function tripCover(trip) {
  if (trip?.cover_theme && BY_KEY[trip.cover_theme]) return BY_KEY[trip.cover_theme];
  const id = String(trip?.id || trip?.name || "");
  let hash = 0;
  for (const char of id) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return TRIP_COVERS[hash % TRIP_COVERS.length];
}

function dayNumber(key) {
  const [y, m, d] = key.split("-").map(Number);
  return Date.UTC(y, m - 1, d) / 86400000;
}

/** "第 2／4 天", "11 天後", "明天出發", "已結束" for a trip on a given local date. */
export function tripTimeLabel(trip, todayKey) {
  const today = dayNumber(todayKey);
  const start = dayNumber(trip.start_date);
  const end = dayNumber(trip.end_date);
  if (today < start) {
    const days = start - today;
    return days === 1 ? "明天出發" : `${days} 天後`;
  }
  if (today > end) return "已結束";
  return `第 ${today - start + 1}／${end - start + 1} 天`;
}
