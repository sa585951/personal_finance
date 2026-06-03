<template>
  <div class="summary-container">
    <div class="summary-header">
      <div>
        <span>日常本月摘要</span>
        <strong>{{ netIncome >= 0 ? "結餘" : "超支" }} {{ formatMoney(Math.abs(netIncome)) }}</strong>
      </div>
      <input
        type="month"
        id="selectedMonth"
        v-model="selectedMonth"
        @change="calculateSummary"
      />
    </div>

    <div class="summary-cards">
      <div class="summary-card income">
        <h3>收入</h3>
        <p class="amount">{{ formatMoney(totalIncome) }}</p>
      </div>

      <div class="summary-card expense">
        <h3>支出</h3>
        <p class="amount">{{ formatMoney(totalExpense) }}</p>
      </div>
    </div>
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
    formatMoney(amount) {
      return `TWD ${Number(amount || 0).toLocaleString("zh-TW", {
        maximumFractionDigits: 0,
      })}`;
    },
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
  padding: 16px;
  border: 1px solid #dbe4ee;
  border-radius: 10px;
  background-color: #ffffff;
}

.summary-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.summary-header div {
  display: grid;
  gap: 2px;
}

.summary-header span {
  color: #64748b;
  font-size: 0.86rem;
  font-weight: 700;
}

.summary-header strong {
  color: #1f2933;
  font-size: 1.15rem;
}

.summary-header input {
  min-height: 38px;
  max-width: 142px;
  padding: 0.45rem 0.55rem;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.summary-card {
  display: grid;
  gap: 4px;
  min-height: 72px;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  box-shadow: none;
}

.summary-card.income {
  background-color: #ecfdf5;
}

.summary-card.expense {
  background-color: #fff1f2;
}

.summary-card h3 {
  margin: 0;
  color: #64748b;
  font-size: 0.86rem;
}

.amount {
  margin: 0;
  font-size: 1.05rem;
  font-weight: bold;
  color: #1f2933;
}
</style>
