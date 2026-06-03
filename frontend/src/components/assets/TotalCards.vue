<template>
  <section class="totals-section">
    <div class="section-heading">
      <h2>帳戶餘額</h2>
      <span>依幣別分組</span>
    </div>

    <div v-if="currencyTotals.length === 0" class="empty-total">
      尚未建立帳戶
    </div>

    <div
      v-for="currencyTotal in currencyTotals"
      :key="currencyTotal.currency"
      class="currency-group"
    >
      <div class="total-primary">
        <span>{{ currencyTotal.currency }} 合計</span>
        <strong>{{ formatMoney(currencyTotal.total, currencyTotal.currency) }}</strong>
      </div>
      <div class="totals-grid">
        <div
          class="total-card"
          v-for="item in visibleTypeTotals(currencyTotal)"
          :key="`${currencyTotal.currency}-${item.type}`"
        >
          <div class="card-title">{{ item.type }}</div>
          <div class="card-amount">{{ formatMoney(item.amount, currencyTotal.currency) }}</div>
          <div
            v-if="currencyTotal.total > 0"
            class="progress-bar-container"
          >
            <div
              class="progress-bar"
              :style="{ width: percentage(item.amount, currencyTotal.total) + '%' }"
            ></div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script>
export default {
  name: "TotalCards",
  props: {
    totals: {
      type: Array,
      default: () => [],
    },
  },
  computed: {
    currencyTotals() {
      return this.totals || [];
    },
  },
  methods: {
    visibleTypeTotals(currencyTotal) {
      return Object.entries(currencyTotal.byType || {})
        .map(([type, amount]) => ({ type, amount }))
        .filter((item) => Number(item.amount || 0) > 0);
    },
    formatMoney(amount, currency) {
      const minorUnit = ["TWD", "JPY", "KRW"].includes(currency) ? 0 : 2;
      return `${currency} ${Number(amount || 0).toLocaleString("zh-TW", {
        minimumFractionDigits: minorUnit,
        maximumFractionDigits: minorUnit,
      })}`;
    },
    percentage(amount, totalAmount) {
      const total = Number(totalAmount || 0);
      if (total <= 0) {
        return 0;
      }
      return Math.min(100, (Number(amount || 0) / total) * 100);
    },
  },
};
</script>
<style scoped>
.totals-section {
  padding: 16px;
  border: 1px solid #dbe4ee;
  border-radius: 10px;
  background: #ffffff;
}

.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.section-heading h2 {
  margin: 0;
  color: #1f2933;
  font-size: 1.15rem;
  letter-spacing: 0;
}

.section-heading span {
  color: #64748b;
  font-size: 0.9rem;
}

.currency-group + .currency-group {
  margin-top: 14px;
}

.total-primary {
  padding: 18px;
  border-radius: 10px;
  background: #0f766e;
  color: #ffffff;
}

.total-primary span {
  display: block;
  margin-bottom: 4px;
  font-weight: 700;
  opacity: 0.86;
}

.total-primary strong {
  display: block;
  font-size: 1.85rem;
  line-height: 1.15;
}

.totals-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 12px;
}

.total-card {
  min-width: 0;
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background-color: #f8fafc;
}

.card-title {
  margin-bottom: 4px;
  color: #64748b;
  font-size: 0.85rem;
  font-weight: bold;
}

.card-amount {
  font-size: 1.1rem;
  font-weight: bold;
  color: #1f2933;
  word-break: break-word;
}

.empty-total {
  padding: 18px;
  border: 1px dashed #cbd5e1;
  border-radius: 10px;
  color: #64748b;
  text-align: center;
}

.progress-bar-container {
  width: 100%;
  height: 6px;
  margin-top: 8px;
  background-color: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: #14b8a6;
  transition: width 0.5s ease;
  border-radius: 4px;
}
</style>
