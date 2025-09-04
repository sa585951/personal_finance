<template>
  <div class="page-container">
    <h1>儀表板總覽</h1>

    <div class="dashboard-grid">
      <OverspendingWarnings />
      <MonthlyExpensesChart />
      <AssetAllocationChart />
      <IncomeExpenseChart />
    </div>
  </div>
</template>

<script>
// 確保路徑正確
import MonthlyExpensesChart from "../components/charts/MonthlyExpensesChart.vue";
import AssetAllocationChart from "../components/charts/AssetAllocationChart.vue";
import IncomeExpenseChart from "../components/charts/IncomeExpenseChart.vue";
import OverspendingWarnings from "../components/reports/OverspendingWarnings.vue";

export default {
  name: "HomeView",
  components: {
    MonthlyExpensesChart,
    AssetAllocationChart,
    IncomeExpenseChart,
    OverspendingWarnings,
  },
};
</script>

<style scoped>
.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
  margin-top: 20px;
}

@media (min-width: 768px) {
  .dashboard-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
