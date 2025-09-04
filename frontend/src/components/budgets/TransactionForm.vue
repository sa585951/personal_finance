<template>
  <div class="form-container">
    <h3>新增交易</h3>
    <form @submit.prevent="addTransaction">
      <label for="transactionDate">日期:</label>
      <input
        type="date"
        id="transactionDate"
        v-model="newTransaction.date"
        required
      />

      <label for="transactionType">類型:</label>
      <select id="transactionType" v-model="newTransaction.type" required>
        <option value="income">收入</option>
        <option value="expense">支出</option>
      </select>

      <label for="budgetCategory">預算類別:</label>
      <select
        id="budgetCategory"
        v-model="newTransaction.budget_category"
        required
      >
        <option disabled value="">請選擇預算類別</option>
        <option
          v-for="category in budgetCategories"
          :key="category"
          :value="category"
        >
          {{ category }}
        </option>
      </select>

      <label for="transactionCategory">項目:</label>
      <input
        type="text"
        id="transactionCategory"
        v-model="newTransaction.item"
        required
      />

      <label for="transactionAmount">金額:</label>
      <input
        type="number"
        id="transactionAmount"
        v-model.number="newTransaction.amount"
        required
      />

      <label for="transactionDescription">備註:</label>
      <input
        type="text"
        id="transactionDescription"
        v-model="newTransaction.description"
      />

      <button type="submit">新增</button>
    </form>
  </div>
</template>

<script>
import axios from "axios";
import { format } from "date-fns";

export default {
  name: "TransactionForm",
  data() {
    return {
      newTransaction: {
        date: format(new Date(), "yyyy-MM-dd"), // 預設為當天日期
        type: "expense",
        item: "", // 將 category 改為 item
        amount: null,
        budget_category: "", // 新增：預算類別
        description: "", // 新增：備註
      },
      // 硬編碼的預算類別，未來可從後端獲取
      budgetCategories: [],
    };
  },
  methods: {
    async addTransaction() {
      try {
        await axios.post("/api/transactions", this.newTransaction);

        this.$emit("transaction-added");
        this.resetForm();
      } catch (error) {
        console.error("新增失敗:", error);
      }
    },
    async fetchBudgetCategories() {
      try {
        const response = await axios.get("/api/budgets/categories");
        this.budgetCategories = response.data.data;
      } catch (error) {
        console.error("無法載入預算類別:", error);
      }
    },
    resetForm() {
      this.newTransaction = {
        date: format(new Date(), "yyyy-MM-dd"),
        type: "支出",
        item: "", // 將 category 改為 item
        amount: null,
        budget_category: "",
        description: "",
      };
    },
  },
  created() {
    // 在元件創建時立即載入類別
    this.fetchBudgetCategories();
  },
};
</script>

<style scoped>
/* 表單容器樣式 - 與 AccountForm 一致 */
.form-container {
  margin-bottom: 2rem;
  padding: 2rem;
  border: 1px solid #e0e0e0;
  border-radius: 10px;
  background-color: #fafafa;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.form-container h3 {
  margin-top: 0;
  color: var(--light-text-color);
  margin-bottom: 1.5rem;
}

/* 新的 Form Grid 佈局 */
.form-container form {
  display: grid;
  /* 2欄式佈局，每行一個 label-input */
  grid-template-columns: auto 1fr;
  gap: 1.2rem 1.5rem; /* row-gap column-gap */
  align-items: center;
}

.form-container label {
  font-weight: bold;
  color: var(--light-text-color);
  text-align: right;
}

.form-container input,
.form-container select {
  padding: 0.8rem 1rem;
  border: 1px solid #ccc;
  border-radius: 6px;
  transition: all 0.3s ease;
  width: 100%;
  background-color: #fff;
}

.form-container input:focus,
.form-container select:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2);
}

/* 按鈕樣式 - 與 AccountForm 一致 */
.form-container button {
  background-color: var(--primary-color);
  /* 讓按鈕橫跨所有欄位 */
  grid-column: 1 / -1;
  width: auto;
  justify-self: end; /* 靠右對齊 */
  margin-top: 1rem;
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

/* 響應式設計 */
@media (max-width: 768px) {
  .form-container form {
    grid-template-columns: 1fr; /* 在小螢幕上變為單欄 */
  }
  .form-container label {
    text-align: left; /* 標籤左對齊 */
  }
  .form-container button {
    width: 100%;
    justify-self: stretch;
  }
}
</style>
