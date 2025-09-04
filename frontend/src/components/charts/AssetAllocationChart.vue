<template>
  <div class="card">
    <div class="card-header">
      <h3 class="card-title">資產配置</h3>
    </div>
    <div class="card-body">
      <Pie
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
import { Pie } from "vue-chartjs";
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  CategoryScale,
} from "chart.js";
import axios from "axios";

ChartJS.register(Title, Tooltip, Legend, ArcElement, CategoryScale);

export default {
  name: "AssetAllocationChart",
  components: {
    Pie,
  },
  data() {
    return {
      chartData: null,
      chartOptions: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "right",
          },
          title: {
            display: false,
            text: "資產配置",
          },
        },
      },
    };
  },
  async created() {
    try {
      const response = await axios.get("/api/reports/asset_allocation");
      this.chartData = response.data.data;
    } catch (error) {
      console.error("Error fetching asset allocation data:", error);
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
