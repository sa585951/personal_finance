<template>
  <button
    class="theme-toggle"
    type="button"
    :aria-label="theme === 'dark' ? '切換為淺色模式' : '切換為深色模式'"
    :title="theme === 'dark' ? '切換為淺色模式' : '切換為深色模式'"
    @click="toggleTheme"
  >
    <Sunny v-if="theme === 'dark'" aria-hidden="true" />
    <Moon v-else aria-hidden="true" />
    <span v-if="showLabel">{{ theme === 'dark' ? '淺色模式' : '深色模式' }}</span>
  </button>
</template>

<script>
import { Moon, Sunny } from "@element-plus/icons-vue";
import { currentTheme, setTheme } from "@/theme";

export default {
  name: "ThemeToggle",
  components: { Moon, Sunny },
  props: {
    showLabel: { type: Boolean, default: false },
  },
  data() {
    return { theme: currentTheme() };
  },
  mounted() {
    window.addEventListener("nomica-theme-change", this.syncTheme);
  },
  beforeUnmount() {
    window.removeEventListener("nomica-theme-change", this.syncTheme);
  },
  methods: {
    syncTheme() {
      this.theme = currentTheme();
    },
    toggleTheme() {
      setTheme(this.theme === "dark" ? "light" : "dark");
    },
  },
};
</script>

<style scoped>
.theme-toggle {
  min-width: 44px;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 0 10px;
  color: var(--text-color);
  background: var(--secondary-color);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  box-shadow: none;
  white-space: nowrap;
}
.theme-toggle svg { width: 20px; height: 20px; flex: none; }
.theme-toggle span { font-size: 0.82rem; font-weight: 700; }
</style>
