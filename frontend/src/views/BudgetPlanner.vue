<template>
  <div class="budget-screen">
    <header class="budget-header">
      <p class="eyebrow">Budget</p>
      <h1>每月預算</h1>
    </header>

    <div class="budget-actions">
      <button
        type="button"
        class="primary-toggle"
        @click="showBudgetForm = !showBudgetForm"
      >
        {{ showBudgetForm ? "收合設定" : "設定預算" }}
      </button>
    </div>

    <BudgetSummaryTable
      ref="budgetSummaryTable"
      :selected-month="selectedMonth"
      @update-month="handleSelectedMonthUpdate"
      @update-budget="updateBudget"
    />

    <div v-if="showBudgetForm" class="form-container">
      <div class="form-header">
        <h3>設定預算</h3>
        <button class="quiet-button" type="button" @click="showBudgetForm = false">收合</button>
      </div>
      <form @submit.prevent="setBudget">
        <div class="form-group">
          <label for="budgetMonth">月份</label>
          <input
            type="month"
            id="budgetMonth"
            v-model="newBudget.month"
            required
          />
        </div>

        <div class="form-group">
          <label for="budgetCategory">類別</label>
          <select
            id="budgetCategory"
            v-model="newBudget.category"
            required
          >
            <option disabled value="">請選擇支出類別</option>
            <option
              v-for="category in expenseCategories"
              :key="category.code"
              :value="category.name"
            >
              {{ category.name }}
            </option>
          </select>
        </div>

        <div class="form-group">
          <label for="budgetAmount">預算金額</label>
          <input
            type="number"
            id="budgetAmount"
            v-model.number="newBudget.amount"
            required
          />
        </div>

        <div class="form-group">
          <label for="budgetNotes">備註</label>
          <input
            type="text"
            id="budgetNotes"
            v-model="newBudget.notes"
            placeholder="例如：餐費包含週末外食"
          />
        </div>
        <button type="submit">設定預算</button>
      </form>
    </div>
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
      budgetCategories: [],
      showBudgetForm: false,
    };
  },
  computed: {
    expenseCategories() {
      return this.budgetCategories.filter(
        (category) => category.kind === "expense" || category.kind === "both"
      );
    },
  },
  methods: {
    handleSelectedMonthUpdate(month) {
      this.selectedMonth = month;
      this.newBudget.month = month;
    },
    ensureBudgetCategory() {
      if (
        this.expenseCategories.some(
          (category) => category.name === this.newBudget.category
        )
      ) {
        return;
      }
      this.newBudget.category = this.expenseCategories[0]?.name || "";
    },
    async fetchBudgetCategories() {
      try {
        const response = await apiClient.get(`/api/budgets/categories?include_meta=true`);
        this.budgetCategories = response.data.data || [];
        this.ensureBudgetCategory();
      } catch (error) {
        console.error("無法載入預算類別:", error);
      }
    },
    async setBudget() {
      try {
        const response = await apiClient.post(`/api/budgets`, this.newBudget);
        this.$swal.fire("成功！", response.data.message, "success");
        this.$refs.budgetSummaryTable.fetchBudgetSummary();
        this.ensureBudgetCategory();
        this.newBudget.amount = null;
        this.newBudget.notes = "";
        this.showBudgetForm = false;
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
    this.fetchBudgetCategories();
    if (this.$refs.budgetSummaryTable) {
      this.$refs.budgetSummaryTable.fetchBudgetSummary();
    }
  },
};
</script>

<style scoped>
.budget-screen {
  max-width: 520px;
  min-height: calc(100vh - 80px);
  margin: 0 auto;
  padding: 24px 14px calc(var(--app-bottom-nav-height) + 22px);
  color: #1f2933;
}

.budget-header {
  margin-bottom: 1rem;
}

.budget-actions {
  margin-bottom: 1rem;
}

.primary-toggle {
  width: 100%;
  min-height: 46px;
  color: #ffffff;
  background: #0f766e;
  border-radius: 8px;
  box-shadow: none;
}

.primary-toggle:hover {
  transform: none;
  box-shadow: none;
}

.eyebrow {
  margin: 0 0 4px;
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
}

h1,
h3 {
  margin: 0;
  letter-spacing: 0;
}

h1 {
  color: var(--text-color);
  font-size: 1.85rem;
}

.form-container {
  margin-top: 1rem;
  padding: 16px;
  border: 1px solid #dbe4ee;
  border-radius: 10px;
  background-color: #ffffff;
  box-shadow: none;
}

.form-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 1rem;
}

.form-container h3 {
  color: #1f2933;
}

.quiet-button {
  min-height: 34px;
  padding: 0 10px;
  color: #334155;
  background: #e2e8f0;
  border-radius: 8px;
  box-shadow: none;
}

.quiet-button:hover {
  transform: none;
  box-shadow: none;
}

.form-container form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.form-group label {
  font-weight: bold;
  color: #475569;
}

.form-group input,
.form-group select {
  min-height: 44px;
  min-width: 0;
  width: 100%;
  padding: 0.8rem 1rem;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  transition: all 0.3s ease;
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2);
}

.form-container button {
  grid-column: 1 / -1;
  min-height: 46px;
  background-color: #0f766e;
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  color: white;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.form-container button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
}

@media (max-width: 768px) {
  .form-container form {
    grid-template-columns: 1fr;
  }
}
</style>
