<template>
  <div class="chart-panel">
    <div class="card-header">
      <div>
        <h3 class="card-title">分類比例</h3>
        <p>{{ effectiveMonth }} 支出類別分布</p>
      </div>
    </div>
    <div class="card-body">
      <div v-if="hasData">
        <Doughnut :data="chartData" :options="chartOptions" class="chart-instance" />
      </div>
      <div v-else class="no-data-message">
        <p>目前沒有支出資料。</p>
      </div>
    </div>
  </div>
</template>

<script>
import { Doughnut } from 'vue-chartjs';
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  CategoryScale
} from 'chart.js';
import apiClient from '../../api';

ChartJS.register(Title, Tooltip, Legend, ArcElement, CategoryScale);

export default {
  name: 'MonthlyExpensesChart',
  components: {
    Doughnut,
  },
  props: {
    month: {
      type: String,
      default: "",
    },
    transactions: {
      type: Array,
      default: null,
    },
  },
  data() {
    return {
      chartData: {
        labels: [],
        datasets: []
      },
      chartOptions: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "62%",
        plugins: {
          legend: {
            position: 'bottom',
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
          title: {
            display: false,
          },
        },
      },
    };
  },
  computed: {
    effectiveMonth() {
      return this.month || new Date().toISOString().slice(0, 7);
    },
    hasData() {
      return this.chartData.labels && this.chartData.labels.length > 0;
    }
  },
  watch: {
    effectiveMonth() {
      this.fetchChartData();
    },
    transactions: {
      deep: true,
      handler() {
        this.fetchChartData();
      },
    },
  },
  methods: {
    async fetchChartData() {
      if (Array.isArray(this.transactions)) {
        const totals = this.transactions
          .filter((transaction) => (
            transaction.type === "expense"
            && String(transaction.date || "").startsWith(this.effectiveMonth)
          ))
          .reduce((result, transaction) => {
            const category = transaction.budget_category || "未分類";
            result[category] = (result[category] || 0) + Number(
              transaction.converted_amount ?? transaction.amount ?? 0
            );
            return result;
          }, {});
        const rows = Object.entries(totals).sort((left, right) => right[1] - left[1]);
        const colors = ["#0f766e", "#2563eb", "#f59e0b", "#7c3aed", "#dc2626", "#64748b"];
        this.chartData = {
          labels: rows.map(([label]) => label),
          datasets: [{
            backgroundColor: rows.map((_, index) => colors[index % colors.length]),
            data: rows.map(([, amount]) => amount),
          }],
        };
        return;
      }
      try {
        const response = await apiClient.get(`/api/reports/monthly_expenses?month=${this.effectiveMonth}`);
        this.chartData = response.data.data;
      } catch (error) {
        console.error("無法載入圖表資料", error);
      }
    }
  },
  mounted() {
    this.fetchChartData();
  },
};
</script>

<style scoped>
.chart-panel {
  min-width: 0;
}

.card-header {
  margin-bottom: 12px;
}

.card-title {
  margin: 0;
  color: #1f2933;
  font-size: 1rem;
  letter-spacing: 0;
}

.card-header p {
  margin: 2px 0 0;
  color: #64748b;
  font-size: 0.84rem;
  font-weight: 700;
}

.card-body {
  min-height: 280px;
}

.chart-instance {
  height: 280px;
}

.no-data-message {
  text-align: center;
  color: #64748b;
  padding: 2rem;
}
</style>
