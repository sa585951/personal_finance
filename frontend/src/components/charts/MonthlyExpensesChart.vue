<template>
  <div class="card">
    <div class="card-header">
      <h3 class="card-title">{{ currentMonth }} 支出類別分佈</h3>
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
import axios from 'axios';

ChartJS.register(Title, Tooltip, Legend, ArcElement, CategoryScale);

export default {
  name: 'MonthlyExpensesChart',
  components: {
    Doughnut,
  },
  data() {
    return {
      currentMonth: new Date().toISOString().slice(0, 7),
      chartData: {
        labels: [],
        datasets: []
      },
      chartOptions: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top',
          },
          title: {
            display: false,
          },
        },
      },
    };
  },
  computed: {
    hasData() {
      return this.chartData.labels && this.chartData.labels.length > 0;
    }
  },
  methods: {
    async fetchChartData() {
      try {
        const response = await axios.get(`/api/reports/monthly_expenses?month=${this.currentMonth}`);
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

.no-data-message {
  text-align: center;
  color: #888;
  font-style: italic;
  padding: 2rem;
}
</style>
