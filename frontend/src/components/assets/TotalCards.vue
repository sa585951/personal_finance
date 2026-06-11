<template>
  <section class="totals-section">
    <div class="section-heading">
      <h2>資金總覽</h2>
      <span>依幣別統計</span>
    </div>

    <div v-if="currencyTotals.length === 0" class="empty-total">
      尚未建立帳戶
    </div>

    <div class="overview-grid">
      <article
        v-for="currencyTotal in currencyTotals"
        :key="currencyTotal.currency"
        class="currency-card"
      >
        <button
          type="button"
          class="total-primary"
          @click="toggleAllocation(currencyTotal.currency)"
        >
          <span>{{ currencyTotal.currency }} 總金額</span>
          <strong>{{ formatMoney(currencyTotal.total, currencyTotal.currency) }}</strong>
          <small>{{ currencyTotal.accountCount || 0 }} 個帳戶 · 以可用資金 100% 計</small>
          <small>{{ isAllocationCollapsed(currencyTotal.currency) ? "點擊展開資金分配" : "點擊收合資金分配" }}</small>
        </button>

        <div class="allocation-panel">
          <div
            v-if="!isAllocationCollapsed(currencyTotal.currency) && visibleTypeTotals(currencyTotal).length > 0"
            class="allocation-card"
          >
            <div class="stacked-bar" aria-label="資金分配比例">
              <div
                v-for="item in visibleTypeTotals(currencyTotal)"
                :key="`${currencyTotal.currency}-${item.type}-segment`"
                class="stacked-segment"
                :style="{
                  width: percentage(item.amount, currencyTotal.allocationTotal) + '%',
                  backgroundColor: typeColor(item.type),
                }"
                :title="`${item.type} ${percentage(item.amount, currencyTotal.allocationTotal)}%`"
              ></div>
            </div>

            <div class="allocation-legend">
              <div
                v-for="item in visibleTypeTotals(currencyTotal)"
                :key="`${currencyTotal.currency}-${item.type}-legend`"
                class="legend-item"
              >
                <span
                  class="legend-swatch"
                  :style="{ backgroundColor: typeColor(item.type) }"
                ></span>
                <span class="legend-name">{{ item.type }}</span>
                <strong>{{ percentage(item.amount, currencyTotal.allocationTotal) }}%</strong>
                <small>{{ formatMoney(item.amount, currencyTotal.currency) }}</small>
              </div>
            </div>
          </div>

          <div
            v-else-if="!isAllocationCollapsed(currencyTotal.currency)"
            class="empty-allocation"
          >
            目前沒有可分配資金
          </div>
        </div>
      </article>
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
  data() {
    return {
      collapsedAllocations: {},
      typeColors: {
        銀行: "#0f766e",
        現金: "#2563eb",
        信用卡: "#dc2626",
        電子錢包: "#7c3aed",
        投資: "#ca8a04",
        其他: "#64748b",
      },
    };
  },
  computed: {
    currencyTotals() {
      return this.totals || [];
    },
  },
  methods: {
    toggleAllocation(currency) {
      this.collapsedAllocations = {
        ...this.collapsedAllocations,
        [currency]: !this.isAllocationCollapsed(currency),
      };
    },
    isAllocationCollapsed(currency) {
      return this.collapsedAllocations[currency] !== false;
    },
    visibleTypeTotals(currencyTotal) {
      return Object.entries(currencyTotal.byType || {})
        .map(([type, amount]) => ({ type, amount: Number(amount || 0) }))
        .filter((item) => item.amount > 0);
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
      return Math.min(100, (Number(amount || 0) / total) * 100).toFixed(1);
    },
    typeColor(type) {
      return this.typeColors[type] || this.typeColors.其他;
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

.overview-grid {
  display: grid;
  gap: 12px;
}

.currency-card {
  display: grid;
  gap: 12px;
  min-width: 0;
}

.currency-card + .currency-card {
  padding-top: 12px;
  border-top: 1px solid #e2e8f0;
}

.total-primary {
  width: 100%;
  padding: 18px;
  border: 0;
  border-radius: 10px;
  background: #0f766e;
  color: #ffffff;
  box-shadow: none;
  text-align: left;
}

.total-primary:hover {
  transform: none;
  box-shadow: none;
}

.total-primary:focus-visible {
  outline: 3px solid #99f6e4;
  outline-offset: 2px;
}

.total-primary span,
.total-primary small {
  display: block;
  font-weight: 700;
  opacity: 0.86;
}

.total-primary strong {
  display: block;
  margin: 4px 0;
  font-size: 1.85rem;
  line-height: 1.15;
  word-break: break-word;
}

.allocation-panel {
  display: grid;
  gap: 10px;
}

.allocation-card {
  display: grid;
  gap: 14px;
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
}

.stacked-bar {
  display: flex;
  width: 100%;
  height: 26px;
  overflow: hidden;
  border-radius: 8px;
  background: #e2e8f0;
}

.stacked-segment {
  height: 100%;
  min-width: 4px;
}

.allocation-legend {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.legend-item {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 6px 8px;
  min-width: 0;
  padding: 10px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
}

.legend-swatch {
  width: 12px;
  height: 12px;
  border-radius: 999px;
}

.legend-name {
  overflow: hidden;
  color: #1f2933;
  font-size: 0.9rem;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.legend-item strong {
  color: #1f2933;
  font-size: 0.9rem;
}

.legend-item small {
  grid-column: 2 / -1;
  color: #64748b;
  font-size: 0.82rem;
  text-align: right;
  word-break: break-word;
}

.empty-total,
.empty-allocation {
  padding: 18px;
  border: 1px dashed #cbd5e1;
  border-radius: 10px;
  color: #64748b;
  text-align: center;
}

.empty-allocation {
  padding: 12px;
  font-size: 0.9rem;
}

@media (max-width: 420px) {
  .allocation-card {
    padding: 12px;
  }

  .allocation-legend {
    grid-template-columns: 1fr;
  }
}
</style>
