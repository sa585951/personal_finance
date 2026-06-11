<template>
  <div class="chart-panel">
    <div class="card-header">
      <div>
        <h3 class="card-title">月年趨勢</h3>
        <p>依分類查看支出變化</p>
      </div>
      <div class="controls">
        <label for="interval">間隔</label>
        <select id="interval" v-model="selectedInterval" @change="fetchChartData">
          <option value="month">月</option>
          <option value="year">年</option>
        </select>
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
          title: {
            display: false,
            text: "月報支出趨勢",
          },
        },
        scales: {
          x: {
            stacked: false, // 可以改為 true 顯示堆疊長條圖
            grid: {
              display: false,
            },
            ticks: {
              color: "#64748b",
              font: {
                size: 11,
                weight: "700",
              },
            },
          },
          y: {
            stacked: false,
            beginAtZero: true,
            grid: {
              color: "#e2e8f0",
            },
            ticks: {
              color: "#64748b",
              font: {
                size: 11,
                weight: "700",
              },
            },
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
.chart-panel {
  min-width: 0;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
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

.controls {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.controls label {
  color: #64748b;
  font-size: 0.82rem;
  font-weight: 800;
}

.controls select {
  min-height: 36px;
  padding: 0 10px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  color: #1f2933;
  font-weight: 800;
}

.card-body {
  min-height: 300px;
}

.chart-instance {
  height: 300px;
}

.no-data-message {
  text-align: center;
  color: #64748b;
  padding: 2rem;
}

@media (max-width: 420px) {
  .card-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .controls {
    width: 100%;
    justify-content: space-between;
  }

  .controls select {
    min-width: 96px;
  }
}
</style>
