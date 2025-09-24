<template>
  <div class="page-container">
    <h1>每月預算規劃</h1>
    <div class="form-container">
      <h3>設定預算</h3>
      <form @submit.prevent="setBudget">
        <div class="form-group">
          <label for="budgetMonth">月份:</label>
          <input
            type="month"
            id="budgetMonth"
            v-model="newBudget.month"
            required
          />
        </div>

        <div class="form-group">
          <label for="budgetCategory">類別:</label>
          <input
            type="text"
            id="budgetCategory"
            v-model="newBudget.category"
            required
          />
        </div>

        <div class="form-group">
          <label for="budgetAmount">預算金額:</label>
          <input
            type="number"
            id="budgetAmount"
            v-model.number="newBudget.amount"
            required
          />
        </div>

        <div class="form-group">
          <label for="budgetNotes">備註:</label>
          <input
            type="text"
            id="budgetNotes"
            v-model="newBudget.notes"
            placeholder="例如：餐費包含週末外食"
          />
        </div>
      </form>
      <div class="button-wrapper">
        <button type="submit" @click="setBudget">設定</button>
      </div>
    </div>
    <BudgetSummaryTable
      ref="budgetSummaryTable"
      :selected-month="selectedMonth"
      @update-month="selectedMonth = $event"
      @update-budget="updateBudget"
    />
  </div>
</template>

<script>
import apiClient from "@/api";
import { format } from "date-fns";
import BudgetSummaryTable from "@/components/budgets/BudgetSummaryTable.vue";

export default {
  name: "BudgetPlanner",
  components: {
    BudgetSummaryTable,
  },
  data() {
    return {
      newBudget: {
        month: format(new Date(), "yyyy-MM"),
        category: "",
        amount: 0,
        notes: "",
      },
      selectedMonth: format(new Date(), "yyyy-MM"),
    };
  },
  methods: {
    async setBudget() {
      try {
        const response = await apiClient.post(`/api/budgets`, this.newBudget);
        this.$swal.fire("成功！", response.data.message, "success");
        this.$refs.budgetSummaryTable.fetchBudgetSummary();
        this.newBudget.category = "";
        this.newBudget.amount = null;
        this.newBudget.notes = "";
      } catch (error) {
        console.error("預算設定失敗:", error);
        this.$swal.fire("失敗！", "預算設定失敗，請稍後再試。", "error");
      }
    },
    async updateBudget(month, category, amount, notes) {
      try {
        const response = await apiClient.post(`/api/budgets`, {
          month,
          category,
          amount,
          notes,
        });
        this.$swal.fire("成功！", response.data.message, "success");
        this.$refs.budgetSummaryTable.fetchBudgetSummary();
      } catch (error) {
        console.error("更新預算失敗:", error);
        this.$swal.fire("失敗！", "更新預算失敗，請稍後再試。", "error");
      }
    },
  },
  mounted() {
    if (this.$refs.budgetSummaryTable) {
      this.$refs.budgetSummaryTable.fetchAvailableMonths();
      this.$refs.budgetSummaryTable.fetchBudgetSummary();
    }
  },
};
</script>

<style scoped>
.page-container {
  max-width: 900px;
  margin: 40px auto;
  padding: 20px;
  background-color: var(--card-bg);
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

h1 {
  text-align: center;
  color: var(--text-color);
  font-size: 2.5rem;
  margin-bottom: 1rem;
}

/* 表單容器樣式 - 與其他頁面一致 */
.form-container {
  margin-bottom: 2rem;
  padding: 2rem;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  background-color: var(--secondary-color);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.form-container h3 {
  margin-top: 0;
  color: var(--light-text-color);
}

/* 表單使用 Flexbox 布局 - 取代 Grid */
.form-container form {
  display: flex;
  flex-wrap: wrap;
  gap: 1.5rem;
}

/* 表單群組樣式 - 每個佔約一半寬度 */
.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  flex: 1 1 45%; /* 彈性增長，基礎寬度45% */
  min-width: 200px; /* 最小寬度，避免太窄 */
}

.form-group label {
  font-weight: bold;
  color: var(--light-text-color);
  margin-bottom: 0.5rem;
}

.form-group input {
  padding: 0.8rem 1rem;
  border: 1px solid #ccc;
  border-radius: 6px;
  transition: all 0.3s ease;
}

.form-group input:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2);
}

/* 按鈕容器 - 獨立在表單外，置中 */
.button-wrapper {
  text-align: center;
  margin-top: 1.5rem;
}

/* 按鈕樣式 - 正常大小 */
.form-container button {
  background-color: var(--primary-color);
  padding: 12px 40px;
  border: none;
  border-radius: 8px;
  color: white;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  display: inline-block;
}

.form-container button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
}

/* 響應式設計 - 小螢幕時改為單列 */
@media (max-width: 768px) {
  .form-container form {
    grid-template-columns: 1fr;
  }
}
</style>
