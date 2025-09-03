<template>
  <div>
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
            <span :class="transaction.type === 'income' ? 'income' : 'expense'">
              {{ transaction.type }}
            </span>
          </td>
          <td>{{ transaction.category }}</td>
          <td>
            <span
              :class="
                transaction.type === 'income'
                  ? 'income-amount'
                  : 'expense-amount'
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
table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0 10px;
}

thead th {
  background-color: var(--primary-color);
  color: var(--card-bg);
  padding: 12px;
  text-align: center;
  font-size: 1rem;
  white-space: nowrap;
}

thead th:first-child {
  border-top-left-radius: 8px;
}

thead th:last-child {
  border-top-right-radius: 8px;
}

tbody td {
  padding: 12px;
  text-align: center;
}

tbody tr {
  background-color: var(--card-bg);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  box-shadow: 0 1px 5px rgba(0, 0, 0, 0.05);
}

tbody tr:hover {
  transform: translateY(-3px);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.delete-btn {
  background-color: var(--danger-color);
  color: white;
  border: none;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.delete-btn:hover {
  background-color: #d32f2f;
}

.income,
.income-amount {
  color: #4caf50;
  font-weight: bold;
}

.expense,
.expense-amount {
  color: #f44336;
  font-weight: bold;
}

.no-data {
  text-align: center;
  padding: 2rem;
  color: #666;
  background-color: var(--card-bg);
  margin-top: 1rem;
  border-radius: 8px;
}
</style>
