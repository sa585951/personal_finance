<template>
  <div>
    <h2>資產總計</h2>
    <div class="totals-grid">
      <div class="total-card" v-for="(amount, type) in totals" :key="type">
        <div class="card-header">
          <div class="card-icon">
            <span v-if="type === '總資產'">💰</span>
            <span v-else-if="type === '活存'">🏦</span>
            <span v-else-if="type === '定存'">📈</span>
            <span v-else-if="type === '投資'">💎</span>
            <span v-else-if="type === '其他'">🎁</span>
            <span v-else>📊</span>
          </div>
          <div class="card-title">{{ type }}</div>
        </div>
        <div class="card-amount">${{ Math.round(parseFloat(amount)).toLocaleString() }}</div>
        <div
          v-if="type !== '總資產' && totals['總資產'] > 0"
          class="progress-bar-container"
        >
          <div
            class="progress-bar"
            :style="{ width: (amount / totals['總資產']) * 100 + '%' }"
          ></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "TotalCards",
  props: {
    totals: Object,
  },
};
</script>
<style scoped>
h2 {
  font-size: 1.8rem;
  margin-top: 2rem;
  margin-bottom: 1rem;
  border-bottom: 2px solid #eee;
  padding-bottom: 0.5rem;
}

.totals-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 20px;
  margin-top: 2rem;
}

.total-card {
  background-color: var(--card-bg);
  padding: 25px;
  border-radius: 12px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
  transition: transform 0.3s ease;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
}

.total-card:hover {
  transform: translateY(-5px);
}

.card-header {
  display: flex;
  align-items: center;
  margin-bottom: 15px;
  color: var(--light-text-color);
}

.card-icon {
  font-size: 2rem;
  margin-right: 15px;
}

.card-title {
  font-size: 1.2rem;
  font-weight: bold;
}

.card-amount {
  font-size: 2.2rem;
  font-weight: bold;
  color: var(--text-color);
  margin-bottom: 15px;
}

.progress-bar-container {
  width: 100%;
  height: 8px;
  background-color: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(to right, #4caf50, #2e7d32);
  transition: width 0.5s ease;
  border-radius: 4px;
}
</style>
