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
  background: #ffffff;
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
  color: #334155;
  background: #e2e8f0;
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
  color: #1f2933;
  text-align: left;
  background: #ffffff;
  border: 1px solid #dbe4ee;
  border-left: 4px solid #94a3b8;
  border-radius: 8px;
  box-shadow: none;
}

.switcher-row.active {
  background: #f0fdfa;
  border-left-color: #0f766e;
}

.switcher-row > div {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.switcher-row strong {
  color: #1f2933;
  font-size: 1rem;
}

.switcher-row span {
  color: #64748b;
  font-size: 0.86rem;
}

.trip-state-badge {
  width: fit-content;
  padding: 4px 8px;
  color: #475569;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  font-size: 0.72rem !important;
  font-weight: 800;
}

.trip-state-badge.included {
  color: #166534;
  background: #dcfce7;
  border-color: #bbf7d0;
}

.trip-state-badge.pending {
  color: #92400e;
  background: #fffbeb;
  border-color: #fde68a;
}
</style>
