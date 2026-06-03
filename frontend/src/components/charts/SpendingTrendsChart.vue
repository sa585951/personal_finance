<template>
  <div class="card">
    <div class="card-header">
      <h3 class="card-title">月報支出趨勢</h3>
      <div class="controls">
        <label for="interval">時間間隔:</label>
        <select id="interval" v-model="selectedInterval" @change="fetchChartData">
          <option value="month">月</option>
          <option value="year">年</option>
        </select>
        <!-- 可以添加日期選擇器 -->
      </div>
    </div>
    <div class="card-body">
      <Bar
        v-if="chartData && chartData.labels.length > 0"
        :data="chartData"
        :options="chartOptions"
        class="chart-instance"
      />
      <div v-else class="no-data-message">
        <p>目前沒有足夠的交易資料來顯示趨勢。</p>
      </div>
    </div>
  </div>
</template>

<script>
import { Bar } from "vue-chartjs";
import apiClient from "@/api";
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  BarElement,
  CategoryScale,
  LinearScale,
} from "chart.js";

ChartJS.register(
  Title,
  Tooltip,
  Legend,
  BarElement,
  CategoryScale,
  LinearScale
);

export default {
  name: "SpendingTrendsChart",
  components: {
    Bar,
  },
  data() {
    return {
      chartData: null,
      selectedInterval: "month", // 預設為月
      chartOptions: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "top",
          },
          title: {
            display: false,
            text: "月報支出趨勢",
          },
        },
        scales: {
          x: {
            stacked: false, // 可以改為 true 顯示堆疊長條圖
          },
          y: {
            stacked: false,
            beginAtZero: true,
          },
        },
      },
    };
  },
  methods: {
    async fetchChartData() {
      try {
        const response = await apiClient.get(
          `/api/reports/transactions_by_category_over_time?interval=${this.selectedInterval}`
        );
        this.chartData = response.data.data;
      } catch (error) {
        console.error("Error fetching spending trends data:", error);
        this.chartData = null;
      }
    },
  },
  created() {
    this.fetchChartData();
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
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: 1.5rem;
  color: var(--light-text-color);
  margin: 0;
}

.controls label {
  margin-right: 10px;
  color: var(--text-color);
}

.controls select {
  padding: 5px 10px;
  border-radius: 5px;
  border: 1px solid #ccc;
}

.chart-instance {
  max-height: 300px; /* Adjust as needed */
}

.no-data-message {
  text-align: center;
  color: #888;
  font-style: italic;
  padding: 2rem;
}
</style>
