<template>
  <section class="trip-status-center" aria-label="旅行狀態中心">
    <div class="trip-status-heading">
      <div>
        <span>Trip Check</span>
        <h2>旅行狀態中心</h2>
      </div>
      <p>快速核對這趟旅行目前需要處理的地方。</p>
    </div>
    <div class="trip-status-grid">
      <button
        v-for="card in cards"
        :key="card.key"
        class="trip-status-card"
        :class="card.tone"
        type="button"
        @click="$emit('select', card.action)"
      >
        <span>{{ card.label }}</span>
        <strong>{{ card.value }}</strong>
        <small>{{ card.hint }}</small>
      </button>
    </div>
  </section>
</template>

<script>
export default {
  name: "TripStatusCenter",
  props: {
    cards: {
      type: Array,
      default: () => [],
    },
  },
  emits: ["select"],
};
</script>

<style scoped>
.trip-status-center {
  display: grid;
  gap: 12px;
  padding: 14px;
  background: #f8fafc;
  border: 1px solid #dbe4ee;
  border-radius: 10px;
}

.trip-status-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 14px;
}

.trip-status-heading span {
  color: #0f766e;
  font-size: 0.76rem;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.trip-status-heading h2 {
  margin: 2px 0 0;
  color: #1f2933;
  font-size: 1.02rem;
  letter-spacing: 0;
}

.trip-status-heading p {
  max-width: 300px;
  margin: 0;
  color: #64748b;
  font-size: 0.82rem;
  font-weight: 700;
  line-height: 1.45;
  text-align: right;
}

.trip-status-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.trip-status-card {
  display: grid;
  gap: 5px;
  min-height: 112px;
  padding: 12px;
  color: #475569;
  text-align: left;
  background: #ffffff;
  border: 1px solid #dbe4ee;
  border-left: 4px solid #94a3b8;
  border-radius: 8px;
  cursor: pointer;
}

.trip-status-card:hover {
  border-color: #99f6e4;
  box-shadow: 0 10px 24px rgba(15, 118, 110, 0.09);
}

.trip-status-card.success {
  background: #f0fdf4;
  border-color: #bbf7d0;
  border-left-color: #16a34a;
}

.trip-status-card.warning {
  background: #fffbeb;
  border-color: #fde68a;
  border-left-color: #f59e0b;
}

.trip-status-card.info {
  background: #eff6ff;
  border-color: #bfdbfe;
  border-left-color: #2563eb;
}

.trip-status-card span {
  font-size: 0.78rem;
  font-weight: 900;
}

.trip-status-card strong {
  color: #111827;
  font-size: 1rem;
  line-height: 1.25;
}

.trip-status-card small {
  color: #64748b;
  font-size: 0.76rem;
  font-weight: 700;
  line-height: 1.35;
}

@media (max-width: 820px) {
  .trip-status-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .trip-status-heading p {
    max-width: none;
    text-align: left;
  }

  .trip-status-grid {
    grid-template-columns: 1fr;
  }
}
</style>
