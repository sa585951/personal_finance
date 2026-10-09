<template>
  <div class="card app-chart-card">
    <div class="card-header">
      <h3 class="card-title">超支警告</h3>
    </div>
    <div class="card-body">
      <div v-if="warnings.length > 0">
        <ul class="warning-list">
          <li v-for="(warning, index) in warnings" :key="index" class="warning-item">
            <p>
              <span class="warning-icon">⚠️</span>
              您在 <strong>{{ warning.month }}</strong> 的 <strong>{{ warning.category }}</strong> 類別超支了
              <span class="overspend-amount">${{ warning.overspend.toLocaleString() }}</span>！
            </p>
            <p class="details">
              預算: ${{ warning.budget.toLocaleString() }}, 已花費: ${{ warning.spent.toLocaleString() }}
            </p>
          </li>
        </ul>
      </div>
      <div v-else class="no-warnings">
        <p>目前沒有超支警告，一切良好！</p>
      </div>
    </div>
  </div>
</template>

<script>
import apiClient from '../../api';

export default {
  name: 'OverspendingWarnings',
  data() {
    return {
      warnings: [],
      currentMonth: new Date().toISOString().slice(0, 7), // 可以根據需要調整月份選擇
    };
  },
  methods: {
    async fetchWarnings() {
      try {
        const response = await apiClient.get(`/api/reports/overspending_warnings?month=${this.currentMonth}`);
        this.warnings = response.data.data;
      } catch (error) {
        console.error("無法載入超支警告:", error);
        this.warnings = [];
      }
    },
  },
  created() {
    this.fetchWarnings();
  },
};
</script>

<style scoped>
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

.warning-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.warning-item {
  background-color: var(--warning-soft);
  border-left: 5px solid var(--warning-color);
  padding: 15px;
  margin-bottom: 10px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.warning-icon {
  font-size: 1.2em;
  margin-right: 8px;
}

.overspend-amount {
  color: var(--expense-color);
  font-weight: bold;
}

.details {
  font-size: 0.9em;
  color: var(--light-text-color);
}

.no-warnings {
  text-align: center;
  color: var(--income-color);
  font-style: italic;
  padding: 20px;
}
</style>
