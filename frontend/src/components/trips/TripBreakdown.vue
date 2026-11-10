<template>
  <section v-if="rows.length" class="trip-breakdown" aria-label="這趟花在哪裡">
    <p class="head">
      <strong>這趟花在哪裡</strong>
      <span v-if="perDay">每天平均 {{ currency }} {{ format(perDay) }}</span>
    </p>
    <div class="bar" role="img" :aria-label="summary">
      <i
        v-for="(row, index) in rows"
        :key="row.category"
        :style="{ width: `${row.percent}%`, background: `var(--chart-${(index % 8) + 1})` }"
      ></i>
    </div>
    <ul class="legend">
      <li v-for="(row, index) in rows" :key="row.category">
        <i class="dot" :style="{ background: `var(--chart-${(index % 8) + 1})` }"></i>
        {{ row.category }} {{ row.percent }}%
        <small>{{ currency }} {{ format(row.amount) }}</small>
      </li>
    </ul>
  </section>
</template>

<script>
import { formatAmount } from "@/utils/money";

const MAX_SLICES = 5;

export default {
  name: "TripBreakdown",
  props: {
    categoryTotals: { type: Array, default: () => [] },
    currency: { type: String, default: "TWD" },
    // Days of the trip that have passed (including today); 0 before departure.
    daysElapsed: { type: Number, default: 0 },
  },
  computed: {
    total() {
      return this.cleaned.reduce((sum, item) => sum + item.amount, 0);
    },
    cleaned() {
      return this.categoryTotals
        .map((item) => ({ category: item.category || "其他", amount: Number(item.amount || 0) }))
        .filter((item) => item.amount > 0)
        .sort((a, b) => b.amount - a.amount);
    },
    rows() {
      if (!this.total) return [];
      const shown = this.cleaned.slice(0, MAX_SLICES - 1);
      const rest = this.cleaned.slice(MAX_SLICES - 1);
      const items = rest.length > 1
        ? [...shown, { category: "其他", amount: rest.reduce((sum, item) => sum + item.amount, 0) }]
        : this.cleaned.slice(0, MAX_SLICES);
      return items.map((item) => ({ ...item, percent: Math.max(1, Math.round((item.amount / this.total) * 100)) }));
    },
    perDay() {
      return this.daysElapsed > 0 ? this.total / this.daysElapsed : 0;
    },
    summary() {
      return this.rows.map((row) => `${row.category} ${row.percent}%`).join("，");
    },
  },
  methods: {
    format(amount) {
      return formatAmount(amount, this.currency);
    },
  },
};
</script>

<style scoped>
.trip-breakdown {
  display: grid;
  gap: 8px;
  padding: 4px 0 12px;
}

.head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin: 0;
}

.head span {
  color: var(--light-text-color);
  font-size: 0.85rem;
}

.bar {
  display: flex;
  height: 10px;
  overflow: hidden;
  border-radius: 5px;
  background: var(--secondary-color);
}

.bar i {
  display: block;
  height: 100%;
}

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 14px;
  margin: 0;
  padding: 0;
  list-style: none;
  color: var(--light-text-color);
  font-size: 0.82rem;
}

.dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  margin-right: 5px;
  border-radius: 50%;
}

.legend small {
  margin-left: 4px;
  font-variant-numeric: tabular-nums;
}
</style>
