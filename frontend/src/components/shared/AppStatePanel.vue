<template>
  <section class="app-state-panel" :class="tone" role="status">
    <span v-if="loading" class="state-spinner" aria-hidden="true"></span>
    <div class="state-copy">
      <strong>{{ title }}</strong>
      <p v-if="message">{{ message }}</p>
    </div>
    <button v-if="actionLabel && !loading" type="button" @click="$emit('action')">
      {{ actionLabel }}
    </button>
  </section>
</template>

<script>
export default {
  name: "AppStatePanel",
  props: {
    title: { type: String, required: true },
    message: { type: String, default: "" },
    actionLabel: { type: String, default: "" },
    tone: { type: String, default: "neutral" },
    loading: { type: Boolean, default: false },
  },
  emits: ["action"],
};
</script>

<style scoped>
.app-state-panel {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 88px;
  padding: 16px;
  color: var(--text-color);
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 10px;
}

.app-state-panel.error {
  color: var(--expense-color);
  background: var(--expense-soft);
  border-color: var(--expense-color);
}

.app-state-panel.empty {
  background: var(--secondary-color);
  border-style: dashed;
}

.state-copy {
  display: grid;
  flex: 1;
  min-width: 0;
  gap: 4px;
}

.state-copy strong {
  color: inherit;
  font-size: 0.96rem;
}

.state-copy p {
  margin: 0;
  color: var(--light-text-color);
  font-size: 0.84rem;
  line-height: 1.45;
}

.app-state-panel.error .state-copy p {
  color: var(--expense-color);
}

.app-state-panel button {
  flex: 0 0 auto;
  min-height: 44px;
  padding: 0 12px;
  color: var(--primary-color);
  background: var(--card-bg);
  border: 1px solid var(--brand-border);
  border-radius: 8px;
  box-shadow: none;
  font-weight: 800;
}

.state-spinner {
  width: 22px;
  height: 22px;
  border: 3px solid var(--primary-soft);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: state-spin 0.8s linear infinite;
}

@keyframes state-spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 420px) {
  .app-state-panel {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .app-state-panel button {
    width: 100%;
  }
}
</style>
