<template>
  <div class="trip-summary-panel">
    <button class="trip-summary-compact" type="button" @click="$emit('toggle')">
      <span>我的成本 {{ formatMoney(myShareAmount) }}</span>
      <strong :class="netStatus.amountClass">
        {{ netStatus.label }} {{ formatMoney(Math.abs(netAmount)) }}
      </strong>
    </button>

    <div class="trip-summary-grid" :class="{ expanded }">
      <div class="summary-card share">
        <span>我的成本</span>
        <strong>{{ formatMoney(myShareAmount) }}</strong>
        <small>分帳後歸屬於你的支出</small>
      </div>
      <div class="summary-card group">
        <span>整團花費</span>
        <strong>{{ formatMoney(expenseTotal) }}</strong>
        <small>整趟旅行總額</small>
      </div>
      <div class="summary-card" :class="netStatus.tone">
        <span>{{ netStatus.label }}</span>
        <strong :class="netStatus.amountClass">{{ formatMoney(Math.abs(netAmount)) }}</strong>
        <small>{{ netStatus.hint }}</small>
      </div>
    </div>

    <div class="trip-category-panel" :class="{ expanded }">
      <TripCategoryChart :category-totals="categoryTotals" :currency="currency" />
    </div>
  </div>
</template>

<script>
import TripCategoryChart from "@/components/charts/TripCategoryChart.vue";

export default {
  name: "TripSummaryPanel",
  components: { TripCategoryChart },
  props: {
    currency: { type: String, required: true },
    myShareAmount: { type: Number, default: 0 },
    expenseTotal: { type: Number, default: 0 },
    netAmount: { type: Number, default: 0 },
    netStatus: { type: Object, required: true },
    categoryTotals: { type: Array, default: () => [] },
    expanded: { type: Boolean, default: false },
  },
  emits: ["toggle"],
  methods: {
    formatMoney(amount) {
      const minorUnit = ["TWD", "JPY", "KRW"].includes(this.currency) ? 0 : 2;
      return `${this.currency} ${Number(amount || 0).toLocaleString("zh-TW", {
        minimumFractionDigits: minorUnit,
        maximumFractionDigits: minorUnit,
      })}`;
    },
  },
};
</script>

<style scoped>
.trip-summary-panel {
  display: grid;
  gap: 16px;
}

.trip-summary-grid {
  display: grid;
  grid-template-columns: 1.15fr 1fr 1fr;
  gap: 10px;
}

.trip-summary-compact {
  display: none;
}

.summary-card {
  display: grid;
  gap: 4px;
  min-height: 72px;
  padding: 12px;
  color: var(--light-text-color);
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-left: 4px solid var(--border-color);
  border-radius: 8px;
}

.summary-card.share {
  color: #0e7490;
  background: var(--travel-soft);
  border-color: #bae6fd;
  border-left-color: #0891b2;
}

.summary-card.group {
  color: var(--text-color);
  background: var(--secondary-color);
  border-color: var(--border-color);
  border-left-color: var(--light-text-color);
}

.summary-card.positive {
  background: var(--income-soft);
  border-color: var(--income-color);
  border-left-color: var(--income-color);
}

.summary-card.negative {
  background: var(--expense-soft);
  border-color: var(--expense-color);
  border-left-color: var(--expense-color);
}

.summary-card.balanced {
  background: var(--secondary-color);
  border-color: var(--border-color);
  border-left-color: #94a3b8;
}

.summary-card span {
  font-size: 0.86rem;
  font-weight: 700;
}

.summary-card strong {
  color: var(--text-color);
  font-size: 1.08rem;
  line-height: 1.25;
}

.summary-card small {
  color: var(--light-text-color);
  font-size: 0.76rem;
  font-weight: 700;
}

.trip-category-panel {
  display: block;
}

@media (max-width: 820px) {
  .trip-summary-compact {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    min-height: 46px;
    padding: 10px 12px;
    color: var(--text-color);
    text-align: left;
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-left: 4px solid var(--primary-color);
    border-radius: 8px;
    box-shadow: none;
  }

  .trip-summary-compact span,
  .trip-summary-compact strong {
    overflow: hidden;
    font-size: 0.9rem;
    line-height: 1.25;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .trip-summary-compact span {
    min-width: 0;
    color: var(--light-text-color);
    font-weight: 800;
  }

  .trip-summary-compact strong {
    flex: 0 0 auto;
    max-width: 46%;
  }

  .trip-summary-grid,
  .trip-category-panel {
    display: none;
  }

  .trip-summary-grid.expanded {
    display: grid;
    grid-template-columns: 1fr;
  }

  .trip-category-panel.expanded {
    display: block;
  }
}
</style>
