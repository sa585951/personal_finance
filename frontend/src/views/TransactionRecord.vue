<template>
  <div class="transactions-screen">
    <header class="page-header">
      <div>
        <p class="eyebrow">Nomica Ledger</p>
        <h1>個人收支</h1>
      </div>
      <button type="button" class="page-add-button" @click="openUniversalAdd">
        <Plus />
        <span>記一筆</span>
      </button>
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

    <section v-if="editingTransaction" class="entry-form-section">
      <TransactionForm
        :type="activeType"
        :editing-transaction="editingTransaction"
        @transaction-updated="handleTransactionUpdated"
        @edit-cancelled="cancelEditingTransaction"
      />
    </section>

    <section class="records-section">
      <div class="section-heading">
        <h2>{{ tableTitle }}</h2>
        <span>{{ tableMetaText }}</span>
      </div>
      <div class="record-mode-switch" aria-label="紀錄查找方式">
        <button
          v-for="mode in recordModes"
          :key="mode.key"
          type="button"
          :class="{ active: recordMode === mode.key }"
          @click="setRecordMode(mode.key)"
        >
          {{ mode.label }}
        </button>
      </div>
      <label v-if="recordMode === 'month'" class="record-month-picker">
        查找月份
        <input v-model="recordMonth" type="month" />
      </label>
      <AppStatePanel
        v-if="recordError && recordTransactions.length === 0"
        title="收支紀錄暫時無法載入"
        :message="recordError"
        action-label="重新整理"
        tone="error"
        @action="fetchRecordTransactions"
      />
      <AppStatePanel
        v-else-if="isRecordLoading && recordTransactions.length === 0"
        title="正在載入收支紀錄"
        :message="recordMode === 'month' ? `查找 ${recordMonth} 的資料。` : '整理最近的交易資料。'"
        loading
      />
      <AppStatePanel
        v-else-if="recordTransactions.length === 0"
        :title="activeType === 'income' ? '目前沒有收入紀錄' : '目前沒有支出紀錄'"
        :message="recordMode === 'month' ? '這個月份沒有符合條件的紀錄。' : '記下第一筆後，這裡會依時間顯示最近紀錄。'"
        :action-label="recordMode === 'recent' ? '記第一筆' : ''"
        tone="empty"
        @action="openUniversalAdd"
      />
      <TransactionTable
        v-else
        :transactions="recordTransactions"
        @transaction-edit="startEditingTransaction"
        @transaction-deleted="fetchTransactions"
      />
      <div v-if="recordTransactions.length > 0" class="record-list-actions">
        <span>
          已顯示 {{ recordTransactions.length }} / 共 {{ recordPagination.total_count }} 筆
        </span>
        <button
          v-if="recordPagination.has_more"
          type="button"
          :disabled="isRecordLoading"
          @click="loadMoreRecords"
        >
          {{ isRecordLoading ? "載入中" : "再載入 10 筆" }}
        </button>
      </div>
    </section>

  </div>
</template>

<script>
import apiClient from "@/api";
import AppStatePanel from "@/components/shared/AppStatePanel.vue";
import { Plus } from "@element-plus/icons-vue";
import TransactionForm from "../components/budgets/TransactionForm.vue";
import TransactionTable from "../components/budgets/TransactionTable.vue";

export default {
  name: "TransactionRecord",
  components: {
    AppStatePanel,
    TransactionForm,
    TransactionTable,
    Plus,
  },
  data() {
    return {
      recordTransactions: [],
      activeType: this.initialTypeFromRoute(),
      editingTransaction: null,
      recordPreviewLimit: 10,
      recordMode: "recent",
      recordMonth: this.defaultMonthKey(),
      recordPagination: {
        next_cursor: null,
        has_more: false,
        limit: 10,
        total_count: 0,
      },
      isRecordLoading: false,
      recordError: "",
    };
  },
  watch: {
    "$route.query.type"() {
      this.activeType = this.initialTypeFromRoute();
      this.editingTransaction = null;
      this.fetchTransactions();
    },
    "$route.query.edit": {
      immediate: true,
      handler(transactionId) {
        if (transactionId) {
          this.loadTransactionForEdit(transactionId);
        }
      },
    },
    recordMonth() {
      if (this.recordMode === "month") {
        this.fetchRecordTransactions();
      }
    },
  },
  computed: {
    recordModes() {
      return [
        { key: "recent", label: "最近紀錄" },
        { key: "month", label: "依月份查找" },
      ];
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
      const typeLabel = this.activeType === "income" ? "收入" : "支出";
      return this.recordMode === "month"
        ? `${this.recordMonthLabel} ${typeLabel}紀錄`
        : `最近${typeLabel}紀錄`;
    },
    tableMetaText() {
      return `共 ${this.recordPagination.total_count} 筆`;
    },
    recordMonthLabel() {
      const [year, month] = String(this.recordMonth || "").split("-");
      return year && month ? `${year} 年 ${Number(month)} 月` : "指定月份";
    },
  },
  methods: {
    openUniversalAdd() {
      this.$router.push({
        name: "UniversalAdd",
        state: { returnTo: this.$route.fullPath },
      });
    },
    defaultMonthKey() {
      const now = new Date();
      return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
    },
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
    async handleTransactionUpdated() {
      this.editingTransaction = null;
      await this.fetchTransactions();
      this.clearEditQuery();
    },
    cancelEditingTransaction() {
      this.editingTransaction = null;
      this.clearEditQuery();
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
      this.editingTransaction = {
        ...transaction,
        selectedAt: Date.now(),
      };
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
    setRecordMode(mode) {
      if (!["recent", "month"].includes(mode) || mode === this.recordMode) return;
      this.recordMode = mode;
      this.fetchRecordTransactions();
    },
    async loadMoreRecords() {
      if (!this.recordPagination.has_more || this.isRecordLoading) return;
      await this.fetchRecordTransactions(true);
    },
    async fetchRecordTransactions(append = false) {
      if (this.isRecordLoading) return;
      this.isRecordLoading = true;
      this.recordError = "";
      try {
        const params = {
          type: this.activeType,
          limit: this.recordPreviewLimit,
        };
        if (this.recordMode === "month") {
          params.month = this.recordMonth;
        }
        if (append && this.recordPagination.next_cursor) {
          params.cursor = this.recordPagination.next_cursor;
        }
        const response = await apiClient.get("/api/transactions", { params });
        const incoming = response.data.data || [];
        if (append) {
          const existingIds = new Set(this.recordTransactions.map((transaction) => transaction.id));
          this.recordTransactions = [
            ...this.recordTransactions,
            ...incoming.filter((transaction) => !existingIds.has(transaction.id)),
          ];
        } else {
          this.recordTransactions = incoming;
        }
        this.recordPagination = response.data.pagination || {
          next_cursor: null,
          has_more: false,
          limit: this.recordPreviewLimit,
          total_count: this.recordTransactions.length,
        };
      } catch (error) {
        console.error("無法載入收支紀錄", error);
        if (!append) {
          this.recordTransactions = [];
          this.recordPagination = {
            next_cursor: null,
            has_more: false,
            limit: this.recordPreviewLimit,
            total_count: 0,
          };
        }
        this.recordError = error.response?.data?.message || "無法載入紀錄，請稍後再試。";
      } finally {
        this.isRecordLoading = false;
      }
    },
    async fetchTransactions() {
      await this.fetchRecordTransactions();
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
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 1rem;
}

.page-header > div {
  min-width: 0;
}

.page-add-button {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-width: 96px;
  min-height: 44px;
  padding: 0 14px;
  color: #ffffff;
  background: #0f766e;
  border: 0;
  border-radius: 8px;
  box-shadow: none;
  font-size: 0.92rem;
  font-weight: 900;
}

.page-add-button svg {
  width: 18px;
  height: 18px;
}

.page-add-button:hover {
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

.records-section {
  margin-top: 1rem;
}

.entry-form-section {
  margin: 0 0 1rem;
}

.record-mode-switch {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
  margin-bottom: 12px;
  padding: 6px;
  background: #e2e8f0;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
}

.record-mode-switch button {
  min-height: 40px;
  padding: 0 10px;
  color: #475569;
  background: transparent;
  border: 0;
  border-radius: 8px;
  box-shadow: none;
  font-size: 0.9rem;
  font-weight: 900;
}

.record-mode-switch button.active {
  color: #0f172a;
  background: #ffffff;
}

.record-month-picker {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  color: #475569;
  font-size: 0.86rem;
  font-weight: 900;
}

.record-month-picker input {
  width: 100%;
  min-height: 42px;
  padding: 0 10px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
}

.record-error,
.record-loading {
  margin: 0 0 10px;
  padding: 10px 12px;
  border-radius: 8px;
  font-weight: 800;
}

.record-error {
  color: #b91c1c;
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.record-loading {
  color: #475569;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.record-list-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 12px 0 0;
}

.record-list-actions span {
  color: #64748b;
  font-size: 0.82rem;
  font-weight: 800;
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

.record-list-actions button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
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
  .page-header {
    align-items: flex-start;
  }

  .page-header h1 {
    font-size: 1.65rem;
  }

  h1 {
    font-size: 1.65rem;
  }

  .mode-switch {
    margin-top: 0.8rem;
  }
}
</style>
