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
      <TripCategoryChart :transactions="transactions" :currency="currency" />
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
    transactions: { type: Array, default: () => [] },
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
  color: #475569;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-left: 4px solid #cbd5e1;
  border-radius: 8px;
}

.summary-card.share {
  color: #0e7490;
  background: #f8feff;
  border-color: #bae6fd;
  border-left-color: #0891b2;
}

.summary-card.group {
  color: #334155;
  background: #f8fafc;
  border-color: #cbd5e1;
  border-left-color: #475569;
}

.summary-card.positive {
  background: #f0fdf4;
  border-color: #bbf7d0;
  border-left-color: #16a34a;
}

.summary-card.negative {
  background: #fff1f2;
  border-color: #fecdd3;
  border-left-color: #e11d48;
}

.summary-card.balanced {
  background: #f8fafc;
  border-color: #cbd5e1;
  border-left-color: #94a3b8;
}

.summary-card span {
  font-size: 0.86rem;
  font-weight: 700;
}

.summary-card strong {
  color: #111827;
  font-size: 1.08rem;
  line-height: 1.25;
}

.summary-card small {
  color: #64748b;
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
    color: #334155;
    text-align: left;
    background: #ffffff;
    border: 1px solid #dbe4ee;
    border-left: 4px solid #0f766e;
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
    color: #475569;
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
