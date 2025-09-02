<template>
  <div class="table-container">
    <h2>所有交易紀錄</h2>
    <table v-if="transactions.length > 0">
      <thead>
        <tr>
          <th>日期</th>
          <th>類型</th>
          <th>項目</th>
          <th>金額</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="transaction in transactions" :key="transaction.id">
          <td>{{ transaction.date }}</td>
          <td>
            <span :class="transaction.type === '收入' ? 'income' : 'expense'">
              {{ transaction.type }}
            </span>
          </td>
          <td>{{ transaction.category }}</td>
          <td>
            <span
              :class="
                transaction.type === '收入' ? 'income-amount' : 'expense-amount'
              "
            >
              ${{ transaction.amount.toLocaleString() }}
            </span>
          </td>
          <td>
            <button
              class="delete-btn"
              @click="deleteTransaction(transaction.id)"
            >
              刪除
            </button>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-else class="no-data">目前沒有交易記錄</div>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "TransactionTable",
  props: {
    transactions: {
      type: Array,
      required: true,
    },
  },
  methods: {
    async deleteTransaction(id) {
      if (confirm("確定要刪除這筆交易嗎？")) {
        try {
          await axios.delete(`/api/transactions/${id}`);
          this.$emit("transaction-deleted");
        } catch (error) {
          console.error("刪除失敗:", error);
        }
      }
    },
  },
};
</script>

<style scoped>
.table-container {
  margin-top: 2rem;
  padding: 1.5rem;
  border: 1px solid #e0e0e0;
  border-radius: 10px;
  background-color: #fafafa;
}

h2 {
  text-align: center;
  color: var(--text-color);
  margin-bottom: 1rem;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 1rem;
}

th,
td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

thead th {
  background-color: var(--primary-color);
  color: white;
  text-align: center;
}

tbody tr:nth-child(even) {
  background-color: #f9f9f9;
}

.income {
  color: #4caf50;
  font-weight: bold;
}

.expense {
  color: #f44336;
  font-weight: bold;
}

.income-amount {
  color: #4caf50;
  font-weight: bold;
}

.expense-amount {
  color: #f44336;
  font-weight: bold;
}

.delete-btn {
  background-color: var(--danger-color);
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
}

.no-data {
  text-align: center;
  padding: 2rem;
  color: #666;
}
</style>
