<template>
  <section class="trip-category-chart">
    <div class="chart-header">
      <div>
        <h3>旅行類別比例</h3>
        <p>{{ totalText }}</p>
      </div>
    </div>

    <div v-if="hasData" class="chart-body">
      <Doughnut :data="chartData" :options="chartOptions" class="chart-instance" />
    </div>
    <div v-else class="empty-chart">
      尚無旅行支出類別資料
    </div>
  </section>
</template>

<script>
import { Doughnut } from "vue-chartjs";
import {
  Chart as ChartJS,
  ArcElement,
  Legend,
  Tooltip,
} from "chart.js";

ChartJS.register(ArcElement, Legend, Tooltip);

export default {
  name: "TripCategoryChart",
  components: {
    Doughnut,
  },
  props: {
    transactions: {
      type: Array,
      default: () => [],
    },
    currency: {
      type: String,
      default: "TWD",
    },
  },
  computed: {
    categoryTotals() {
      const totals = new Map();
      this.transactions
        .filter((transaction) => transaction.type === "expense")
        .forEach((transaction) => {
          const category = transaction.budget_category || transaction.category || "其他";
          const amount = Number(transaction.converted_amount ?? transaction.amount ?? 0);
          if (amount <= 0) return;
          totals.set(category, (totals.get(category) || 0) + amount);
        });

      return Array.from(totals.entries())
        .map(([category, amount]) => ({ category, amount }))
        .sort((left, right) => right.amount - left.amount);
    },
    hasData() {
      return this.categoryTotals.length > 0;
    },
    totalAmount() {
      return this.categoryTotals.reduce((sum, item) => sum + item.amount, 0);
    },
    totalText() {
      if (!this.hasData) {
        return "依旅行支出類別統計";
      }
      return `總計 ${this.formatMoney(this.totalAmount)}`;
    },
    chartData() {
      return {
        labels: this.categoryTotals.map((item) => item.category),
        datasets: [
          {
            data: this.categoryTotals.map((item) => item.amount),
            backgroundColor: [
              "#0f766e",
              "#2563eb",
              "#ca8a04",
              "#7c3aed",
              "#dc2626",
              "#64748b",
              "#0891b2",
              "#16a34a",
            ],
            borderColor: "#ffffff",
            borderWidth: 2,
          },
        ],
      };
    },
    chartOptions() {
      return {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "62%",
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              boxWidth: 10,
              boxHeight: 10,
              color: "#475569",
              padding: 12,
              font: {
                size: 12,
                weight: "700",
              },
            },
          },
        },
      };
    },
  },
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
.trip-category-chart {
  display: grid;
  gap: 12px;
  padding: 14px;
  border: 1px solid #dbe4ee;
  border-radius: 10px;
  background: #ffffff;
}

.chart-header h3 {
  margin: 0;
  color: #1f2933;
  font-size: 1rem;
  letter-spacing: 0;
}

.chart-header p {
  margin: 2px 0 0;
  color: #64748b;
  font-size: 0.84rem;
  font-weight: 700;
}

.chart-body {
  min-height: 260px;
}

.chart-instance {
  height: 260px;
}

.empty-chart {
  padding: 18px;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  color: #64748b;
  text-align: center;
}
</style>
