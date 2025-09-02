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
        <option value="收入">收入</option>
        <option value="支出">支出</option>
      </select>

      <label for="transactionCategory">項目:</label>
      <input
        type="text"
        id="transactionCategory"
        v-model="newTransaction.category"
        required
      />

      <label for="transactionAmount">金額:</label>
      <input
        type="number"
        id="transactionAmount"
        v-model.number="newTransaction.amount"
        required
      />

      <button type="submit">新增</button>
    </form>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "TransactionForm",
  data() {
    return {
      newTransaction: {
        date: "",
        type: "支出",
        category: "",
        amount: null,
      },
    };
  },
  methods: {
    async addTransaction() {
      try {
        await axios.post("/api/transactions", this.newTransaction);

        // 發送事件通知父組件
        this.$emit("transaction-added");

        // 清空表單
        this.resetForm();
      } catch (error) {
        console.error("新增失敗:", error);
      }
    },

    resetForm() {
      this.newTransaction = {
        date: "",
        type: "支出",
        category: "",
        amount: null,
      };
    },
  },
};
</script>

<style scoped>
.form-container form {
  display: grid;
  grid-template-columns: repeat(2, 1fr); /* 改為2列佈局 */
  gap: 1.5rem;
  align-items: end;
}

/* 或者使用更靈活的佈局 */
.form-container form {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: end;
}

.form-container form > div {
  display: flex;
  flex-direction: column;
  min-width: 150px;
  flex: 1;
}

/* 讓按鈕單獨一行 */
.form-container button {
  grid-column: 1 / -1; /* 如果用 grid */
  width: 100%;
  margin-top: 1rem;
}

label {
  font-weight: bold;
}

input,
select {
  padding: 0.8rem;
  border: 1px solid #ccc;
  border-radius: 6px;
}

button {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  color: white;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s ease;
  background-color: var(--primary-color);
}
</style>
