<template>
  <div class="transactions-screen">
    <header class="page-header">
      <p class="eyebrow">Nomica Ledger</p>
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
      :type="activeType"
      @apply-draft="applyAIDraft"
      @parsed="refreshAIEvents"
    />

    <AIParseEventsPanel
      v-if="showDevAIEvents"
      ref="aiParseEventsPanel"
    />

    <section class="entry-form-section">
      <button
        v-if="!showTransactionForm"
        class="manual-entry-toggle"
        type="button"
        @click="openManualForm"
      >
        {{ manualEntryLabel }}
      </button>
      <p v-if="!showTransactionForm" class="manual-entry-hint">
        AI 解析後也會在這裡展開表單，送出前仍可調整日期、類別與帳戶。
      </p>

      <TransactionForm
        v-if="showTransactionForm"
        :type="activeType"
        :draft="aiDraft"
        :editing-transaction="editingTransaction"
        @transaction-added="handleTransactionAdded"
        @transaction-updated="handleTransactionUpdated"
        @edit-cancelled="cancelEditingTransaction"
      />
    </section>

    <TransactionSummary :transactions="transactions" />

    <section class="records-section">
      <div class="section-heading">
        <h2>{{ tableTitle }}</h2>
        <span>{{ tableMetaText }}</span>
      </div>
      <div
        v-if="recordDateFilters.length > 1"
        class="record-date-tabs"
        aria-label="收支紀錄日期篩選"
      >
        <button
          v-for="filter in recordDateFilters"
          :key="filter.key"
          type="button"
          :class="{ active: selectedRecordDate === filter.key }"
          @click="selectedRecordDate = filter.key"
        >
          <span>{{ filter.label }}</span>
          <small>{{ filter.count }} 筆</small>
        </button>
      </div>
      <TransactionTable
        :transactions="displayedTransactions"
        @transaction-edit="startEditingTransaction"
        @transaction-deleted="fetchTransactions"
      />
      <div
        v-if="hiddenRecordCount > 0 || canCollapseRecords"
        class="record-list-actions"
      >
        <button
          v-if="hiddenRecordCount > 0"
          type="button"
          @click="showAllRecords = true"
        >
          顯示更多（尚有 {{ hiddenRecordCount }} 筆）
        </button>
        <button
          v-else
          type="button"
          @click="showAllRecords = false"
        >
          收合為最新 {{ recordPreviewLimit }} 筆
        </button>
      </div>
    </section>

    <section v-if="activeType !== 'income'" class="analysis-section">
      <div class="section-heading">
        <h2>{{ analysisTitle }}</h2>
        <span>支出分析</span>
      </div>
      <div class="analysis-panel">
        <div class="analysis-tabs" aria-label="支出分析切換">
          <button
            v-for="tab in analysisTabs"
            :key="tab.key"
            type="button"
            :class="{ active: activeAnalysisTab === tab.key }"
            @click="activeAnalysisTab = tab.key"
          >
            {{ tab.label }}
          </button>
        </div>
        <MonthlyExpensesChart v-if="activeAnalysisTab === 'category'" />
        <SpendingTrendsChart v-else />
      </div>
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
import MonthlyExpensesChart from "../components/charts/MonthlyExpensesChart.vue";
import SpendingTrendsChart from "../components/charts/SpendingTrendsChart.vue";

export default {
  name: "TransactionRecord",
  components: {
    AIParseEventsPanel,
    AIQuickInput,
    TransactionForm,
    TransactionTable,
    TransactionSummary,
    MonthlyExpensesChart,
    SpendingTrendsChart,
  },
  data() {
    return {
      transactions: [],
      activeType: this.initialTypeFromRoute(),
      aiDraft: null,
      editingTransaction: null,
      selectedRecordDate: "all",
      activeAnalysisTab: "category",
      showAllRecords: false,
      recordPreviewLimit: 10,
      showTransactionForm: false,
    };
  },
  watch: {
    "$route.query.type"() {
      this.activeType = this.initialTypeFromRoute();
      this.selectedRecordDate = "all";
      this.showAllRecords = false;
    },
    "$route.query.edit": {
      immediate: true,
      handler(transactionId) {
        if (transactionId) {
          this.loadTransactionForEdit(transactionId);
        }
      },
    },
    selectedRecordDate() {
      this.showAllRecords = false;
    },
  },
  computed: {
    filteredTransactions() {
      return this.transactions.filter((transaction) => transaction.type === this.activeType);
    },
    sortedFilteredTransactions() {
      return [...this.filteredTransactions].sort(this.sortTransactionsNewestFirst);
    },
    recordDateFilters() {
      const dateMap = new Map();
      this.filteredTransactions.forEach((transaction) => {
        if (!transaction.date) return;
        const current = dateMap.get(transaction.date) || {
          key: transaction.date,
          label: this.formatDateChip(transaction.date),
          count: 0,
        };
        current.count += 1;
        dateMap.set(transaction.date, current);
      });

      const dates = Array.from(dateMap.values())
        .sort((left, right) => right.key.localeCompare(left.key));

      return [
        {
          key: "all",
          label: "全部",
          count: this.filteredTransactions.length,
        },
        ...dates,
      ];
    },
    recordListTransactions() {
      if (this.selectedRecordDate === "all") {
        return this.sortedFilteredTransactions;
      }
      return this.sortedFilteredTransactions.filter(
        (transaction) => transaction.date === this.selectedRecordDate
      );
    },
    displayedTransactions() {
      if (this.selectedRecordDate !== "all" || this.showAllRecords) {
        return this.recordListTransactions;
      }
      return this.recordListTransactions.slice(0, this.recordPreviewLimit);
    },
    hiddenRecordCount() {
      if (this.selectedRecordDate !== "all" || this.showAllRecords) return 0;
      return Math.max(this.recordListTransactions.length - this.recordPreviewLimit, 0);
    },
    canCollapseRecords() {
      return (
        this.selectedRecordDate === "all" &&
        this.showAllRecords &&
        this.recordListTransactions.length > this.recordPreviewLimit
      );
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
    analysisTabs() {
      return [
        {
          key: "category",
          label: "花在哪裡",
        },
        {
          key: "trend",
          label: "變化趨勢",
        },
      ];
    },
    tableTitle() {
      const typeLabel = this.activeType === "income" ? "收入" : "支出";
      if (this.selectedRecordDate !== "all") {
        return `${this.formatDateChip(this.selectedRecordDate)} 的${typeLabel}`;
      }
      if (this.showAllRecords || this.recordListTransactions.length <= this.recordPreviewLimit) {
        return `全部${typeLabel}紀錄`;
      }
      return `最近 ${this.recordPreviewLimit} 筆${typeLabel}`;
    },
    tableMetaText() {
      const count = this.recordListTransactions.length;
      if (this.selectedRecordDate !== "all") {
        return `${count} 筆`;
      }
      if (this.showAllRecords || count <= this.recordPreviewLimit) {
        return `共 ${count} 筆`;
      }
      return `共 ${count} 筆`;
    },
    manualEntryLabel() {
      return this.activeType === "income" ? "手動新增收入" : "手動新增支出";
    },
    analysisTitle() {
      return this.activeAnalysisTab === "category" ? "支出花在哪裡" : "支出變化趨勢";
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
      this.selectedRecordDate = "all";
      this.showAllRecords = false;
      this.aiDraft = null;
      this.showTransactionForm = false;
      this.$router.replace({
        path: this.$route.path,
        query: {
          ...this.$route.query,
          type,
        },
      });
    },
    applyAIDraft(draft) {
      const switchedType = ["expense", "income"].includes(draft.type) && draft.type !== this.activeType;
      if (["expense", "income"].includes(draft.type) && draft.type !== this.activeType) {
        this.setActiveType(draft.type);
      }
      this.editingTransaction = null;
      this.showTransactionForm = true;
      this.aiDraft = {
        ...draft,
        switchedType,
        appliedAt: Date.now(),
      };
      this.$nextTick(() => {
        document.querySelector(".entry-form-section")?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      });
    },
    openManualForm() {
      this.aiDraft = null;
      this.editingTransaction = null;
      this.showTransactionForm = true;
      this.$nextTick(() => {
        document.querySelector(".entry-form-section")?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      });
    },
    async handleTransactionAdded() {
      await this.fetchTransactions();
      this.refreshAIEvents();
      this.showTransactionForm = false;
      this.aiDraft = null;
    },
    async handleTransactionUpdated() {
      this.editingTransaction = null;
      await this.fetchTransactions();
      this.clearEditQuery();
      this.showTransactionForm = false;
    },
    cancelEditingTransaction() {
      this.editingTransaction = null;
      this.clearEditQuery();
      this.showTransactionForm = false;
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
      this.showTransactionForm = true;
      this.$nextTick(() => {
        document.querySelector(".entry-form-section")?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      });
    },
    async loadTransactionForEdit(transactionId) {
      try {
        const response = await apiClient.get(`/api/transactions/${transactionId}`);
        const transaction = response.data.data;
        if (transaction.trip_id) {
          this.$router.replace({
            path: "/trips",
            query: { trip_id: transaction.trip_id },
          });
          return;
        }
        this.startEditingTransaction(transaction);
      } catch (error) {
        console.error("無法載入交易明細", error);
        this.$swal.fire(
          "無法開啟編輯",
          error.response?.data?.message || "請稍後再試。",
          "error"
        );
        this.clearEditQuery();
      }
    },
    clearEditQuery() {
      if (!this.$route.query.edit) return;
      const { edit, ...query } = this.$route.query;
      this.$router.replace({
        path: this.$route.path,
        query,
      });
    },
    refreshAIEvents() {
      this.$refs.aiParseEventsPanel?.fetchEvents();
    },
    syncSelectedRecordDate() {
      if (this.selectedRecordDate === "all") return;
      const hasSelectedDate = this.filteredTransactions.some(
        (transaction) => transaction.date === this.selectedRecordDate
      );
      if (!hasSelectedDate) {
        this.selectedRecordDate = "all";
      }
    },
    formatDateChip(dateString) {
      if (!dateString) return "";
      const parts = String(dateString).split("-");
      if (parts.length !== 3) return dateString;
      const month = Number(parts[1]);
      const day = Number(parts[2]);
      if (!Number.isFinite(month) || !Number.isFinite(day)) return dateString;
      return `${month}/${day}`;
    },
    sortTransactionsNewestFirst(left, right) {
      const leftDate = left.date || "";
      const rightDate = right.date || "";
      const dateComparison = rightDate.localeCompare(leftDate);
      if (dateComparison !== 0) return dateComparison;
      return Number(right.id || 0) - Number(left.id || 0);
    },
    async fetchTransactions() {
      try {
        const response = await apiClient.get(`/api/transactions`);
        this.transactions = response.data.data || [];
        this.syncSelectedRecordDate();
      } catch (error) {
        console.error("無法載入交易資料", error);
        this.transactions = [];
        this.selectedRecordDate = "all";
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

.entry-form-section {
  margin: 0 0 1rem;
}

.manual-entry-toggle {
  width: 100%;
  min-height: 44px;
  padding: 0 14px;
  color: #0f172a;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  box-shadow: none;
  font-size: 0.95rem;
  font-weight: 900;
}

.manual-entry-toggle:hover {
  background: #f8fafc;
}

.manual-entry-hint {
  margin: 8px 4px 0;
  color: #64748b;
  font-size: 0.84rem;
  font-weight: 700;
  line-height: 1.45;
  text-align: left;
}

.analysis-panel {
  padding: 14px;
  border: 1px solid #dbe4ee;
  border-radius: 10px;
  background: #ffffff;
}

.analysis-tabs {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
  padding: 6px;
  margin-bottom: 12px;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  background: #e2e8f0;
}

.analysis-tabs button {
  min-height: 40px;
  padding: 0 10px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #475569;
  box-shadow: none;
  font-size: 0.92rem;
  font-weight: 900;
}

.analysis-tabs button.active {
  background: #ffffff;
  color: #0f172a;
}

.analysis-tabs button:hover {
  transform: none;
  box-shadow: none;
}

.record-date-tabs {
  display: flex;
  gap: 8px;
  margin: 0 0 12px;
  padding: 2px 0 4px;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}

.record-date-tabs::-webkit-scrollbar {
  display: none;
}

.record-date-tabs button {
  display: grid;
  gap: 2px;
  flex: 0 0 auto;
  min-width: 68px;
  min-height: 48px;
  padding: 6px 10px;
  color: #475569;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  box-shadow: none;
}

.record-date-tabs button.active {
  color: #ffffff;
  background: #334155;
  border-color: #334155;
}

.record-date-tabs span {
  font-size: 0.86rem;
  font-weight: 900;
}

.record-date-tabs small {
  font-size: 0.72rem;
  font-weight: 800;
  opacity: 0.82;
}

.record-list-actions {
  display: flex;
  justify-content: center;
  margin: 12px 0 0;
}

.record-list-actions button {
  min-height: 42px;
  padding: 0 18px;
  color: #334155;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  box-shadow: none;
  font-size: 0.92rem;
  font-weight: 900;
}

.record-list-actions button:hover {
  transform: none;
  box-shadow: none;
  border-color: #94a3b8;
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
