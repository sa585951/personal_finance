<template>
  <div class="summary-container">
    <h2>收支統計</h2>

    <!-- 月份選擇 -->
    <div class="month-selector">
      <label for="selectedMonth">選擇月份:</label>
      <input
        type="month"
        id="selectedMonth"
        v-model="selectedMonth"
        @change="calculateSummary"
      />
    </div>

    <!-- 總計卡片 -->
    <div class="summary-cards">
      <div class="summary-card income">
        <div class="card-icon">💰</div>
        <div class="card-content">
          <h3>總收入</h3>
          <p class="amount">${{ Math.round(totalIncome).toLocaleString() }}</p>
        </div>
      </div>

      <div class="summary-card expense">
        <div class="card-icon">💸</div>
        <div class="card-content">
          <h3>總支出</h3>
          <p class="amount">${{ Math.round(totalExpense).toLocaleString() }}</p>
        </div>
      </div>

      <div
        class="summary-card net"
        :class="netIncome >= 0 ? 'positive' : 'negative'"
      >
        <div class="card-icon">📊</div>
        <div class="card-content">
          <h3>淨收入</h3>
          <p class="amount">${{ Math.round(netIncome).toLocaleString() }}</p>
        </div>
      </div>
    </div>

    <div v-if="!selectedMonth" class="no-selection">請選擇月份查看統計</div>
  </div>
</template>

<script>
export default {
  name: "TransactionSummary",
  props: {
    transactions: {
      type: Array,
      required: true,
    },
  },
  data() {
    return {
      selectedMonth: "",
      totalIncome: 0,
      totalExpense: 0,
    };
  },
  computed: {
    netIncome() {
      return this.totalIncome - this.totalExpense;
    },
  },
  watch: {
    transactions() {
      this.calculateSummary();
    },
  },
  methods: {
    calculateSummary() {
      if (!this.selectedMonth) {
        this.resetSummary();
        return;
      }

      // 篩選該月份的交易
      const monthTransactions = this.transactions.filter((transaction) => {
        if (!transaction.date) return false;
        const transactionDate = new Date(transaction.date);
        const transactionYearMonth = `${transactionDate.getFullYear()}-${String(
          transactionDate.getMonth() + 1
        ).padStart(2, "0")}`;
        return transactionYearMonth === this.selectedMonth;
      });

      // 計算總收入和總支出
      this.totalIncome = monthTransactions
        .filter((t) => t.type === "income")
        .reduce((sum, t) => sum + parseFloat(t.amount), 0);

      this.totalExpense = monthTransactions
        .filter((t) => t.type === "expense")
        .reduce((sum, t) => sum + parseFloat(t.amount), 0);
    },

    resetSummary() {
      this.totalIncome = 0;
      this.totalExpense = 0;
    },
  },
  mounted() {
    // 預設為當前月份
    const now = new Date();
    this.selectedMonth = `${now.getFullYear()}-${String(
      now.getMonth() + 1
    ).padStart(2, "0")}`;
    this.calculateSummary();
  },
};
</script>

<style scoped>
.summary-container {
  margin-top: 2rem;
  padding: 1.5rem;
  border: 1px solid #e0e0e0;
  border-radius: 10px;
  background-color: #fafafa;
}

.month-selector {
  margin-bottom: 1.5rem;
  text-align: center;
}

.month-selector label {
  font-weight: bold;
  margin-right: 1rem;
}

.month-selector input {
  padding: 0.5rem;
  border: 1px solid #ccc;
  border-radius: 4px;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.summary-card {
  padding: 1.5rem;
  border-radius: 8px;
  display: flex;
  align-items: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.summary-card.income {
  background-color: #e8f5e9;
  border-left: 4px solid #4caf50;
}

.summary-card.expense {
  background-color: #ffebee;
  border-left: 4px solid #f44336;
}

.summary-card.net.positive {
  background-color: #e3f2fd;
  border-left: 4px solid #2196f3;
}

.summary-card.net.negative {
  background-color: #fff3e0;
  border-left: 4px solid #ff9800;
}

.card-icon {
  font-size: 2rem;
  margin-right: 1rem;
}

.card-content h3 {
  margin: 0 0 0.5rem 0;
  font-size: 1rem;
  color: #666;
}

.amount {
  margin: 0;
  font-size: 1.5rem;
  font-weight: bold;
  color: #333;
}

.no-selection {
  text-align: center;
  color: #666;
  padding: 2rem;
}

h2 {
  text-align: center;
  color: var(--text-color);
  margin-bottom: 1rem;
}
</style>
