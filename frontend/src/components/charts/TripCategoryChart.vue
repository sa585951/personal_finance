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
import { chartPalette, chartThemeColor, observeChartTheme } from "@/constants/chartPalette";
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
    categoryTotals: {
      type: Array,
      default: () => [],
    },
    currency: {
      type: String,
      default: "TWD",
    },
  },
  data() {
    return { themeRevision: 0 };
  },
  computed: {
    normalizedCategoryTotals() {
      return this.categoryTotals
        .map((item) => ({
          category: item.category || "其他",
          amount: Number(item.amount || 0),
        }))
        .filter((item) => item.amount > 0)
        .sort((left, right) => right.amount - left.amount);
    },
    hasData() {
      return this.normalizedCategoryTotals.length > 0;
    },
    totalAmount() {
      return this.normalizedCategoryTotals.reduce((sum, item) => sum + item.amount, 0);
    },
    totalText() {
      if (!this.hasData) {
        return "依旅行支出類別統計";
      }
      return `總計 ${this.formatMoney(this.totalAmount)}`;
    },
    chartData() {
      const colors = chartPalette(this.themeRevision);
      return {
        labels: this.normalizedCategoryTotals.map((item) => item.category),
        datasets: [
          {
            data: this.normalizedCategoryTotals.map((item) => item.amount),
            backgroundColor: this.normalizedCategoryTotals.map((_, index) => colors[index % colors.length]),
            borderColor: chartThemeColor("--card-bg", this.themeRevision),
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
              color: chartThemeColor("--light-text-color", this.themeRevision),
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
  mounted() {
    this.stopThemeObserver = observeChartTheme(() => { this.themeRevision += 1; });
  },
  beforeUnmount() {
    this.stopThemeObserver?.();
  },
};
</script>

<style scoped>
.trip-category-chart {
  display: grid;
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  background: var(--card-bg);
}

.chart-header h3 {
  margin: 0;
  color: var(--text-color);
  font-size: 1rem;
  letter-spacing: 0;
}

.chart-header p {
  margin: 2px 0 0;
  color: var(--light-text-color);
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
  border: 1px dashed var(--border-color);
  border-radius: 8px;
  color: var(--light-text-color);
  text-align: center;
}
</style>
