const STORAGE_KEY = "nomica-theme";
const DARK_QUERY = "(prefers-color-scheme: dark)";

export function currentTheme() {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const themeColor = document.querySelector('meta[name="theme-color"]');
  if (themeColor) themeColor.content = theme === "dark" ? "#101216" : "#4263EB";
  window.dispatchEvent(new Event("nomica-theme-change"));
}

export function setTheme(theme) {
  if (theme !== "light" && theme !== "dark") return;
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // Private browsing can block storage; the choice still applies for this page.
  }
  applyTheme(theme);
}

export function initTheme() {
  const media = window.matchMedia(DARK_QUERY);
  media.addEventListener("change", () => {
    try {
      if (localStorage.getItem(STORAGE_KEY) === "light" || localStorage.getItem(STORAGE_KEY) === "dark") return;
    } catch {
      // Follow the operating system when storage is unavailable.
    }
    applyTheme(media.matches ? "dark" : "light");
  });
}
