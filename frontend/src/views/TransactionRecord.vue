<template>
  <div class="transactions-screen">
    <header class="page-header">
      <p class="eyebrow">Personal Ledger</p>
      <h1>個人收支</h1>
    </header>

    <div class="mode-switch" aria-label="交易模式">
      <button
        v-for="tab in transactionTabs"
        :key="tab.key"
        type="button"
        :class="[tab.key, { active: activeType === tab.key }]"
        @click="setActiveType(tab.key)"
      >
        <span>{{ tab.label }}</span>
      </button>
    </div>

    <AIQuickInput
      @apply-draft="applyAIDraft"
      @parsed="refreshAIEvents"
    />

    <AIParseEventsPanel
      v-if="showDevAIEvents"
      ref="aiParseEventsPanel"
    />

    <TransactionForm
      :type="activeType"
      :draft="aiDraft"
      :editing-transaction="editingTransaction"
      @transaction-added="handleTransactionAdded"
      @transaction-updated="handleTransactionUpdated"
      @edit-cancelled="editingTransaction = null"
    />

    <TransactionSummary :transactions="transactions" />

    <section class="records-section">
      <div class="section-heading">
        <h2>{{ tableTitle }}</h2>
        <span>近期紀錄</span>
      </div>
      <TransactionTable
        :transactions="filteredTransactions"
        @transaction-edit="startEditingTransaction"
        @transaction-deleted="fetchTransactions"
      />
    </section>

    <section v-if="activeType !== 'income'" class="analysis-section">
      <div class="section-heading">
        <h2>月報支出趨勢</h2>
        <span>分析</span>
      </div>
      <SpendingTrendsChart />
    </section>
  </div>
</template>

<script>
import apiClient from "@/api";
import AIParseEventsPanel from "../components/budgets/AIParseEventsPanel.vue";
import AIQuickInput from "../components/budgets/AIQuickInput.vue";
import TransactionForm from "../components/budgets/TransactionForm.vue";
import TransactionTable from "../components/budgets/TransactionTable.vue";
import TransactionSummary from "../components/budgets/TransactionSummary.vue";
import SpendingTrendsChart from "../components/charts/SpendingTrendsChart.vue";

export default {
  name: "TransactionRecord",
  components: {
    AIParseEventsPanel,
    AIQuickInput,
    TransactionForm,
    TransactionTable,
    TransactionSummary,
    SpendingTrendsChart,
  },
  data() {
    return {
      transactions: [],
      activeType: this.initialTypeFromRoute(),
      aiDraft: null,
      editingTransaction: null,
    };
  },
  watch: {
    "$route.query.type"() {
      this.activeType = this.initialTypeFromRoute();
    },
  },
  computed: {
    filteredTransactions() {
      return this.transactions.filter((transaction) => transaction.type === this.activeType);
    },
    transactionTabs() {
      return [
        {
          key: "expense",
          label: "支出",
        },
        {
          key: "income",
          label: "收入",
        },
      ];
    },
    tableTitle() {
      const titleMap = {
        expense: "支出紀錄",
        income: "收入紀錄",
      };
      return titleMap[this.activeType];
    },
    showDevAIEvents() {
      return import.meta.env.DEV;
    },
  },
  methods: {
    initialTypeFromRoute() {
      return this.$route.query.type === "income" ? "income" : "expense";
    },
    setActiveType(type) {
      this.activeType = type;
      this.editingTransaction = null;
      this.$router.replace({
        path: this.$route.path,
        query: {
          ...this.$route.query,
          type,
        },
      });
    },
    applyAIDraft(draft) {
      if (["expense", "income"].includes(draft.type) && draft.type !== this.activeType) {
        this.setActiveType(draft.type);
      }
      this.aiDraft = {
        ...draft,
        appliedAt: Date.now(),
      };
    },
    async handleTransactionAdded() {
      await this.fetchTransactions();
      this.refreshAIEvents();
    },
    async handleTransactionUpdated() {
      this.editingTransaction = null;
      await this.fetchTransactions();
    },
    startEditingTransaction(transaction) {
      if (!transaction?.id) return;
      if (["expense", "income"].includes(transaction.type)) {
        this.activeType = transaction.type;
        this.$router.replace({
          path: this.$route.path,
          query: {
            ...this.$route.query,
            type: transaction.type,
          },
        });
      }
      this.aiDraft = null;
      this.editingTransaction = {
        ...transaction,
        selectedAt: Date.now(),
      };
      this.$nextTick(() => {
        document.querySelector(".form-container")?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      });
    },
    refreshAIEvents() {
      this.$refs.aiParseEventsPanel?.fetchEvents();
    },
    async fetchTransactions() {
      try {
        const response = await apiClient.get(`/api/transactions`);
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
.transactions-screen {
  max-width: 520px;
  min-height: calc(100vh - 80px);
  margin: 0 auto;
  padding: 24px 14px calc(var(--app-bottom-nav-height) + 22px);
  color: #1f2933;
}

.page-header {
  margin-bottom: 1rem;
}

.eyebrow {
  margin: 0 0 4px;
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
}

h1 {
  color: var(--text-color);
  font-size: 1.85rem;
  margin: 0;
  letter-spacing: 0;
}

.mode-switch {
  position: sticky;
  top: 0;
  z-index: 5;
  display: inline-grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
  width: 100%;
  padding: 6px;
  margin: 1rem 0;
  background: #e2e8f0;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
}

.mode-switch button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  padding: 0 12px;
  color: #475569;
  background: transparent;
  border: 0;
  border-radius: 8px;
  box-shadow: none;
  font-size: 1rem;
  text-align: center;
}

.mode-switch button.expense {
  color: #dc2626;
}

.mode-switch button.income {
  color: #0f766e;
}

.mode-switch button.expense.active {
  color: #ffffff;
  background: #dc2626;
}

.mode-switch button.income.active {
  color: #ffffff;
  background: #0f766e;
}

.mode-switch span {
  font-size: 1rem;
  font-weight: 800;
}

.records-section,
.analysis-section {
  margin-top: 1rem;
}

.section-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  margin: 0 0 10px;
}

.section-heading h2 {
  margin: 0;
  color: #1f2933;
  font-size: 1.08rem;
}

.section-heading span {
  color: #64748b;
  font-size: 0.86rem;
  font-weight: 700;
}

@media (min-width: 900px) {
  .transactions-screen {
    padding-top: 36px;
  }
}

@media (max-width: 420px) {
  h1 {
    font-size: 1.65rem;
  }

  .mode-switch {
    margin-top: 0.8rem;
  }
}
</style>
