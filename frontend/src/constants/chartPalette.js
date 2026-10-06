export function chartPalette() {
  const styles = getComputedStyle(document.documentElement);
  return Array.from({ length: 8 }, (_, index) => styles.getPropertyValue(`--chart-${index + 1}`).trim());
}

export function chartThemeColor(token) {
  return getComputedStyle(document.documentElement).getPropertyValue(token).trim();
}

export function observeChartTheme(callback) {
  window.addEventListener("nomica-theme-change", callback);
  return () => window.removeEventListener("nomica-theme-change", callback);
}

export function applyCategoryPalette(data) {
  if (!data) return { labels: [], datasets: [] };
  const colors = chartPalette();
  return {
    ...data,
    datasets: (data.datasets || []).map((dataset) => ({
      ...dataset,
      backgroundColor: (dataset.data || []).map((_, index) => colors[index % colors.length]),
    })),
  };
}

export function applySeriesPalette(data) {
  if (!data) return { labels: [], datasets: [] };
  const colors = chartPalette();
  return {
    ...data,
    datasets: (data.datasets || []).map((dataset, index) => ({
      ...dataset,
      backgroundColor: colors[index % colors.length],
      borderColor: colors[index % colors.length],
    })),
  };
}
