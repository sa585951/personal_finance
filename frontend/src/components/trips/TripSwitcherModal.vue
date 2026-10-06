<template>
  <div class="modal-backdrop" @click.self="$emit('close')">
    <section class="trip-switcher" role="dialog" aria-modal="true" aria-labelledby="trip-switcher-title">
      <div class="switcher-header">
        <h2 id="trip-switcher-title">切換旅行</h2>
        <button class="quiet-action" type="button" @click="$emit('close')">關閉</button>
      </div>
      <div class="trip-switcher-list">
        <button
          v-for="item in items"
          :key="item.id"
          class="switcher-row"
          :class="{ active: item.id === selectedId }"
          type="button"
          @click="$emit('select', item.id)"
        >
          <div>
            <span class="trip-state-badge" :class="item.reportClass">{{ item.reportLabel }}</span>
            <strong>{{ item.name }}</strong>
            <span>{{ item.description }}</span>
          </div>
        </button>
      </div>
    </section>
  </div>
</template>

<script>
export default {
  name: "TripSwitcherModal",
  props: {
    items: { type: Array, default: () => [] },
    selectedId: { type: String, default: "" },
  },
  emits: ["close", "select"],
};
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: grid;
  align-items: end;
  padding: 16px;
  background: rgba(15, 23, 42, 0.42);
}

.trip-switcher {
  width: min(520px, 100%);
  max-height: 78vh;
  margin: 0 auto;
  padding: 16px;
  overflow: auto;
  background: var(--card-bg);
  border-radius: 10px;
}

.switcher-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.switcher-header h2 {
  margin: 0;
  letter-spacing: 0;
}

.quiet-action {
  min-height: 38px;
  padding: 0 12px;
  color: var(--text-color);
  background: var(--border-color);
  border-radius: 8px;
  box-shadow: none;
  font-weight: 800;
}

.trip-switcher-list {
  display: grid;
  gap: 8px;
}

.switcher-row {
  width: 100%;
  min-height: 82px;
  padding: 12px;
  color: var(--text-color);
  text-align: left;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-left: 4px solid #94a3b8;
  border-radius: 8px;
  box-shadow: none;
}

.switcher-row.active {
  background: var(--primary-soft);
  border-left-color: var(--primary-color);
}

.switcher-row > div {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.switcher-row strong {
  color: var(--text-color);
  font-size: 1rem;
}

.switcher-row span {
  color: var(--light-text-color);
  font-size: 0.86rem;
}

.trip-state-badge {
  width: fit-content;
  padding: 4px 8px;
  color: var(--light-text-color);
  background: var(--secondary-color);
  border: 1px solid var(--border-color);
  border-radius: 999px;
  font-size: 0.72rem !important;
  font-weight: 800;
}

.trip-state-badge.included {
  color: var(--income-color);
  background: var(--income-soft);
  border-color: var(--income-color);
}

.trip-state-badge.pending {
  color: var(--warning-color);
  background: var(--warning-soft);
  border-color: var(--warning-color);
}
</style>
