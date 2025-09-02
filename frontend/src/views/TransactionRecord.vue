<template>
  <div class="transaction-container">
    <h1>個人交易紀錄</h1>

    <!-- 使用 TransactionForm 組件 -->
    <TransactionForm @transaction-added="fetchTransactions" />

    <!-- 使用 TransactionTable 組件 -->
    <TransactionTable
      :transactions="transactions"
      @transaction-deleted="fetchTransactions"
    />
  </div>
</template>

<script>
import axios from "axios";
import TransactionForm from "../components/TransactionForm.vue";
import TransactionTable from "../components/TransactionTable.vue";

export default {
  name: "TransactionRecord",
  components: {
    TransactionForm,
    TransactionTable,
  },
  data() {
    return {
      transactions: [],
    };
  },
  methods: {
    async fetchTransactions() {
      try {
        const response = await axios.get("/api/transactions");
        this.transactions = response.data.data || [];
      } catch (error) {
        console.error("無法載入交易資料", error);
        this.transactions = [];
      }
    },
  },
  created() {
    this.fetchTransactions();
  },
};
</script>

<style scoped>
.transaction-container {
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
</style>
