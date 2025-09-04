<template>
  <div class="card goal-summary-card">
    <div class="card-header">
      <h3 class="card-title">目標總覽</h3>
    </div>
    <div class="card-body" v-if="summary">
      <div class="summary-item">
        <span class="label">總目標數:</span>
        <span class="value">{{ summary.total_goals }}</span>
      </div>
      <div class="summary-item">
        <span class="label">已完成目標:</span>
        <span class="value">{{ summary.completed_goals }}</span>
      </div>
      <div class="summary-item">
        <span class="label">進行中目標:</span>
        <span class="value">{{ summary.active_goals }}</span>
      </div>
      <div class="summary-item">
        <span class="label">總目標金額:</span>
        <span class="value">${{ summary.total_target_amount.toLocaleString() }}</span>
      </div>
      <div class="summary-item">
        <span class="label">已達成金額:</span>
        <span class="value">${{ summary.total_current_amount.toLocaleString() }}</span>
      </div>
      <div class="summary-item">
        <span class="label">整體進度:</span>
        <span class="value">{{ summary.overall_progress_percentage.toFixed(1) }}%</span>
      </div>
      <div class="progress-bar-container">
        <div class="progress-bar" :style="{ width: summary.overall_progress_percentage + '%' }"></div>
      </div>
    </div>
    <div v-else class="no-data-message">
      <p>載入中...</p>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
const API_URL = import.meta.env.VITE_APP_API_URL;

export default {
  name: 'GoalSummaryCard',
  data() {
    return {
      summary: null,
    };
  },
  methods: {
    async fetchGoalSummary() {
      try {
        const response = await axios.get(`${API_URL}/api/reports/goal_summary`);
        this.summary = response.data.data;
      } catch (error) {
        console.error("Error fetching goal summary:", error);
        this.summary = null;
      }
    },
  },
  created() {
    this.fetchGoalSummary();
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

.summary-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px dashed #eee;
}

.summary-item:last-child {
  border-bottom: none;
}

.label {
  font-weight: bold;
  color: var(--text-color);
}

.value {
  color: var(--primary-color);
  font-weight: bold;
}

.progress-bar-container {
  width: 100%;
  height: 10px;
  background-color: #e0e0e0;
  border-radius: 5px;
  overflow: hidden;
  margin-top: 15px;
}

.progress-bar {
  height: 100%;
  background-color: var(--primary-color);
  transition: width 0.3s ease-in-out;
}

.no-data-message {
  text-align: center;
  color: #888;
  font-style: italic;
  padding: 2rem;
}
</style>
