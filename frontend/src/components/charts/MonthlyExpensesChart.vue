<template>
  <div class="chart-panel">
    <div class="card-header">
      <div>
        <h3 class="card-title">分類比例</h3>
        <p>{{ currentMonth }} 支出類別分布</p>
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
    hasData() {
      return this.chartData.labels && this.chartData.labels.length > 0;
    }
  },
  methods: {
    async fetchChartData() {
      try {
        const response = await apiClient.get(`/api/reports/monthly_expenses?month=${this.currentMonth}`);
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
