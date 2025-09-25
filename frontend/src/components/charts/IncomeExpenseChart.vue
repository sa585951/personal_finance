<template>
  <div class="card">
    <div class="card-header">
      <h3 class="card-title">收入與支出</h3>
    </div>
    <div class="card-body">
      <Bar
        v-if="chartData"
        :data="chartData"
        :options="chartOptions"
        class="chart-instance"
      />
      <p v-else>載入中...</p>
    </div>
  </div>
</template>

<script>
import { Bar } from 'vue-chartjs';
import apiClient from "../../api";

ChartJS.register(
  Title,
  Tooltip,
  Legend,
  BarElement,
  CategoryScale,
  LinearScale
);

export default {
  name: "IncomeExpenseChart",
  components: {
    Bar,
  },
  data() {
    return {
      chartData: null,
      chartOptions: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false,
          },
          title: {
            display: false,
            text: "收入與支出",
          },
        },
        scales: {
          y: {
            beginAtZero: true,
          },
        },
      },
    };
  },
  async created() {
    try {

      const response = await apiClient.get(`/api/reports/income_expense_summary`);
      this.chartData = response.data.data;
    } catch (error) {
      console.error("Error fetching income/expense data:", error);
      this.chartData = null; // Set to null to show loading or error message
    }
  },
};
</script>

<style scoped>
.card {
  background-color: var(--secondary-color);
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  padding: 20px;
  margin-bottom: 20px;
}

.card-header {
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 15px;
  margin-bottom: 15px;
}

.card-title {
  font-size: 1.5rem;
  color: var(--light-text-color);
  margin: 0;
}

.chart-instance {
  max-height: 300px; /* Adjust as needed */
}
</style>
