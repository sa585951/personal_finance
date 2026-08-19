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

    <section v-if="editingTransaction" class="entry-form-section">
      <TransactionForm
        :type="activeType"
        :editing-transaction="editingTransaction"
        @transaction-updated="handleTransactionUpdated"
        @edit-cancelled="cancelEditingTransaction"
      />
    </section>

    <TransactionSummary
      :transactions="transactions"
      :month="selectedSummaryMonth"
      @month-change="selectedSummaryMonth = $event"
    />

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
      <p v-if="recordError" class="record-error">{{ recordError }}</p>
      <p v-if="isRecordLoading && recordTransactions.length === 0" class="record-loading">
        讀取紀錄中
      </p>
      <TransactionTable
        v-else
        :transactions="recordTransactions"
        @transaction-edit="startEditingTransaction"
        @transaction-deleted="fetchTransactions"
      />
      <div class="record-list-actions">
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
      <div class="account-flow-panel">
        <div class="account-flow-header">
          <div>
            <h3>付款來源分析</h3>
            <p>{{ selectedMonthLabel }}的支出依付款帳戶類型整理。</p>
          </div>
          <small>{{ selectedMonthTypeTransactions.length }} 筆支出</small>
        </div>
        <div v-if="accountFlowGroups.length > 0" class="account-flow-groups">
          <div
            v-for="group in accountFlowGroups"
            :key="group.currency"
            class="account-flow-group"
          >
            <div class="account-flow-total">
              <span>{{ group.currency }} 合計</span>
              <strong>{{ formatMoney(group.total, group.currency) }}</strong>
            </div>
            <div class="account-flow-bar" aria-label="付款來源比例">
              <span
                v-for="row in group.rows"
                :key="`${group.currency}-${row.key}`"
                :style="{
                  width: `${row.percentage}%`,
                  background: row.color,
                }"
              ></span>
            </div>
            <div class="account-flow-list">
              <div
                v-for="row in group.rows"
                :key="`${group.currency}-${row.key}`"
                class="account-flow-row"
              >
                <div class="account-flow-main">
                  <span>
                    <i :style="{ background: row.color }"></i>
                    {{ row.label }}
                  </span>
                  <small>{{ row.count }} 筆 · {{ Math.round(row.rawPercentage) }}%</small>
                </div>
                <strong>{{ formatMoney(row.amount, group.currency) }}</strong>
              </div>
            </div>
          </div>
        </div>
        <p v-else class="account-flow-empty">
          這個月份尚未有支出紀錄。新增支出並連動帳戶後，這裡會顯示現金、銀行、信用卡等付款來源比例。
        </p>
      </div>
    </section>
    <section v-else class="income-check-section">
      <div class="section-heading">
        <h2>收入來源核對</h2>
        <span>{{ selectedMonthLabel }}</span>
      </div>
      <div class="income-check-panel">
        <div v-if="monthlyIncomeTotal > 0">
          <div class="income-check-total">
            <div>
              <span>本月收入</span>
              <strong>{{ formatMoney(monthlyIncomeTotal) }}</strong>
            </div>
            <small>{{ incomeSourceRows.length }} 個來源 · {{ selectedMonthIncomeTransactions.length }} 筆</small>
          </div>
          <div class="income-distribution-bar" aria-label="收入來源分布">
            <span
              v-for="source in incomeSourceRows"
              :key="source.name"
              :style="{
                width: `${source.percentage}%`,
                background: source.color,
              }"
            ></span>
          </div>
          <div class="income-distribution-legend">
            <span
              v-for="source in incomeSourceRows"
              :key="source.name"
            >
              <i :style="{ background: source.color }"></i>
              {{ source.name }} {{ Math.round(source.rawPercentage) }}%
            </span>
          </div>
          <div class="income-source-list">
            <div
              v-for="source in incomeSourceRows"
              :key="source.name"
              class="income-source-row"
            >
              <div class="income-source-main">
                <span>{{ source.name }}</span>
                <small>{{ source.count }} 筆</small>
              </div>
              <strong>{{ formatMoney(source.amount) }}</strong>
              <small class="income-source-percent">{{ Math.round(source.rawPercentage) }}%</small>
            </div>
          </div>
          <p v-if="hiddenIncomeSourceCount > 0" class="income-check-note">
            另有 {{ hiddenIncomeSourceCount }} 個收入來源未顯示。
          </p>
        </div>
        <p v-else class="income-check-empty">
          這個月份尚未記錄收入。新增收入後，這裡會依收入類別整理來源。
        </p>
      </div>
      <div class="account-flow-panel">
        <div class="account-flow-header">
          <div>
            <h3>入帳帳戶分析</h3>
            <p>{{ selectedMonthLabel }}的收入依入帳帳戶類型整理。</p>
          </div>
          <small>{{ selectedMonthTypeTransactions.length }} 筆收入</small>
        </div>
        <div v-if="accountFlowGroups.length > 0" class="account-flow-groups">
          <div
            v-for="group in accountFlowGroups"
            :key="group.currency"
            class="account-flow-group"
          >
            <div class="account-flow-total">
              <span>{{ group.currency }} 合計</span>
              <strong>{{ formatMoney(group.total, group.currency) }}</strong>
            </div>
            <div class="account-flow-bar" aria-label="入帳帳戶比例">
              <span
                v-for="row in group.rows"
                :key="`${group.currency}-${row.key}`"
                :style="{
                  width: `${row.percentage}%`,
                  background: row.color,
                }"
              ></span>
            </div>
            <div class="account-flow-list">
              <div
                v-for="row in group.rows"
                :key="`${group.currency}-${row.key}`"
                class="account-flow-row"
              >
                <div class="account-flow-main">
                  <span>
                    <i :style="{ background: row.color }"></i>
                    {{ row.label }}
                  </span>
                  <small>{{ row.count }} 筆 · {{ Math.round(row.rawPercentage) }}%</small>
                </div>
                <strong>{{ formatMoney(row.amount, group.currency) }}</strong>
              </div>
            </div>
          </div>
        </div>
        <p v-else class="account-flow-empty">
          這個月份尚未有收入紀錄。新增收入並連動帳戶後，這裡會顯示銀行、現金或其他入帳來源比例。
        </p>
      </div>
    </section>
  </div>
</template>

<script>
import apiClient from "@/api";
import TransactionForm from "../components/budgets/TransactionForm.vue";
import TransactionTable from "../components/budgets/TransactionTable.vue";
import TransactionSummary from "../components/budgets/TransactionSummary.vue";
import MonthlyExpensesChart from "../components/charts/MonthlyExpensesChart.vue";
import SpendingTrendsChart from "../components/charts/SpendingTrendsChart.vue";

export default {
  name: "TransactionRecord",
  components: {
    TransactionForm,
    TransactionTable,
    TransactionSummary,
    MonthlyExpensesChart,
    SpendingTrendsChart,
  },
  data() {
    return {
      transactions: [],
      recordTransactions: [],
      activeType: this.initialTypeFromRoute(),
      editingTransaction: null,
      activeAnalysisTab: "category",
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
      selectedSummaryMonth: this.defaultMonthKey(),
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
    selectedSummaryMonth() {
      this.fetchAnalysisTransactions();
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
    analysisTitle() {
      return this.activeAnalysisTab === "category" ? "支出花在哪裡" : "支出變化趨勢";
    },
    selectedMonthLabel() {
      if (!this.selectedSummaryMonth) return "本月";
      const [year, month] = this.selectedSummaryMonth.split("-");
      if (!year || !month) return this.selectedSummaryMonth;
      return `${Number(month)} 月`;
    },
    selectedMonthIncomeTransactions() {
      return this.selectedMonthTransactions("income");
    },
    selectedMonthTypeTransactions() {
      return this.selectedMonthTransactions(this.activeType);
    },
    monthlyIncomeTotal() {
      return this.selectedMonthIncomeTransactions.reduce(
        (sum, transaction) => sum + Number(transaction.amount || 0),
        0
      );
    },
    allIncomeSourceRows() {
      const sourceMap = new Map();
      this.selectedMonthIncomeTransactions.forEach((transaction) => {
        const sourceName = transaction.budget_category || "未分類收入";
        const current = sourceMap.get(sourceName) || {
          name: sourceName,
          amount: 0,
          count: 0,
        };
        current.amount += Number(transaction.amount || 0);
        current.count += 1;
        sourceMap.set(sourceName, current);
      });
      const colors = ["#0f766e", "#2563eb", "#f59e0b", "#7c3aed"];
      return Array.from(sourceMap.values())
        .sort((left, right) => right.amount - left.amount)
        .map((source, index) => ({
          ...source,
          color: colors[index % colors.length],
          rawPercentage: this.monthlyIncomeTotal > 0
            ? (source.amount / this.monthlyIncomeTotal) * 100
            : 0,
          percentage: this.monthlyIncomeTotal > 0
            ? Math.max((source.amount / this.monthlyIncomeTotal) * 100, 2)
            : 0,
        }));
    },
    incomeSourceRows() {
      return this.allIncomeSourceRows.slice(0, 4);
    },
    hiddenIncomeSourceCount() {
      return Math.max(this.allIncomeSourceRows.length - this.incomeSourceRows.length, 0);
    },
    accountFlowGroups() {
      const palette = ["#0f766e", "#2563eb", "#f59e0b", "#7c3aed", "#dc2626", "#64748b"];
      const groupMap = new Map();

      this.selectedMonthTypeTransactions.forEach((transaction) => {
        const currency = transaction.base_currency || transaction.currency || "TWD";
        const amount = Number(transaction.converted_amount ?? transaction.amount ?? 0);
        if (amount <= 0) return;

        const accountType = transaction.account_id
          ? transaction.account_type || "other"
          : "unlinked";
        const accountLabel = this.translateAccountType(accountType);
        const groupKey = `${currency}:${accountType}`;
        const current = groupMap.get(groupKey) || {
          key: accountType,
          currency,
          label: accountLabel,
          amount: 0,
          count: 0,
        };
        current.amount += amount;
        current.count += 1;
        groupMap.set(groupKey, current);
      });

      const rowsByCurrency = Array.from(groupMap.values()).reduce((map, row) => {
        if (!map[row.currency]) {
          map[row.currency] = [];
        }
        map[row.currency].push(row);
        return map;
      }, {});

      return Object.entries(rowsByCurrency)
        .map(([currency, rows]) => {
          const sortedRows = rows.sort((left, right) => right.amount - left.amount);
          const total = sortedRows.reduce((sum, row) => sum + row.amount, 0);
          return {
            currency,
            total,
            rows: sortedRows.map((row, index) => ({
              ...row,
              color: palette[index % palette.length],
              rawPercentage: total > 0 ? (row.amount / total) * 100 : 0,
              percentage: total > 0 ? Math.max((row.amount / total) * 100, 2) : 0,
            })),
          };
        })
        .sort((left, right) => right.total - left.total);
    },
  },
  methods: {
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
    selectedMonthTransactions(type) {
      return this.transactions.filter((transaction) => (
        transaction.type === type
        && this.transactionMonthKey(transaction) === this.selectedSummaryMonth
      ));
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
    transactionMonthKey(transaction) {
      if (!transaction?.date) return "";
      const transactionDate = new Date(transaction.date);
      if (Number.isNaN(transactionDate.getTime())) return "";
      return `${transactionDate.getFullYear()}-${String(
        transactionDate.getMonth() + 1
      ).padStart(2, "0")}`;
    },
    formatMoney(amount, currency = "TWD") {
      const minorUnit = ["TWD", "JPY", "KRW"].includes(currency) ? 0 : 2;
      return `${currency} ${Number(amount || 0).toLocaleString("zh-TW", {
        minimumFractionDigits: minorUnit,
        maximumFractionDigits: minorUnit,
      })}`;
    },
    translateAccountType(type) {
      const typeMap = {
        bank: "銀行",
        cash: "現金",
        credit_card: "信用卡",
        e_wallet: "電子錢包",
        prepaid_card: "預付卡",
        investment: "投資",
        external: "外部帳戶",
        unlinked: "未連動帳戶",
        other: "其他",
      };
      return typeMap[type] || type || "其他";
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
    async fetchAnalysisTransactions() {
      try {
        const allTransactions = [];
        let cursor = null;
        let hasMore = true;
        while (hasMore) {
          const params = {
            month: this.selectedSummaryMonth,
            limit: 50,
          };
          if (cursor) params.cursor = cursor;
          const response = await apiClient.get("/api/transactions", { params });
          allTransactions.push(...(response.data.data || []));
          const pagination = response.data.pagination || {};
          hasMore = pagination.has_more === true;
          cursor = pagination.next_cursor || null;
          if (hasMore && !cursor) break;
        }
        this.transactions = allTransactions;
      } catch (error) {
        console.error("無法載入月份分析資料", error);
        this.transactions = [];
      }
    },
    async fetchTransactions() {
      await Promise.all([
        this.fetchRecordTransactions(),
        this.fetchAnalysisTransactions(),
      ]);
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

.analysis-panel {
  padding: 14px;
  border: 1px solid #dbe4ee;
  border-radius: 10px;
  background: #ffffff;
}

.account-flow-panel {
  display: grid;
  gap: 12px;
  margin-top: 12px;
  padding: 14px;
  border: 1px solid #dbe4ee;
  border-radius: 10px;
  background: #ffffff;
}

.account-flow-header,
.account-flow-total {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.account-flow-header h3 {
  margin: 0;
  color: #1f2933;
  font-size: 1rem;
  letter-spacing: 0;
}

.account-flow-header p {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 0.82rem;
  font-weight: 700;
  line-height: 1.45;
}

.account-flow-header small {
  flex: 0 0 auto;
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 900;
  white-space: nowrap;
}

.account-flow-groups {
  display: grid;
  gap: 12px;
}

.account-flow-group {
  display: grid;
  gap: 10px;
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.account-flow-total span {
  color: #64748b;
  font-size: 0.82rem;
  font-weight: 800;
}

.account-flow-total strong {
  color: #0f172a;
  font-size: 1.05rem;
  white-space: nowrap;
}

.account-flow-bar {
  display: flex;
  height: 12px;
  overflow: hidden;
  background: #e2e8f0;
  border-radius: 999px;
}

.account-flow-bar span {
  min-width: 2px;
}

.account-flow-list {
  display: grid;
  gap: 8px;
}

.account-flow-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-height: 44px;
}

.account-flow-main {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.account-flow-main span {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: #0f172a;
  font-size: 0.9rem;
  font-weight: 900;
}

.account-flow-main i {
  flex: 0 0 auto;
  width: 8px;
  height: 8px;
  border-radius: 999px;
}

.account-flow-main small {
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 800;
}

.account-flow-row strong {
  color: #0f172a;
  font-size: 0.9rem;
  white-space: nowrap;
}

.account-flow-empty {
  margin: 0;
  padding: 12px;
  color: #64748b;
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  font-size: 0.86rem;
  font-weight: 700;
  line-height: 1.5;
}

.income-check-section {
  margin-top: 1rem;
}

.income-check-panel {
  padding: 14px;
  border: 1px solid #dbe4ee;
  border-radius: 10px;
  background: #ffffff;
}

.income-check-total {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 76px;
  padding: 14px;
  color: #134e4a;
  background: linear-gradient(135deg, #ecfdf5 0%, #eff6ff 100%);
  border: 1px solid #99f6e4;
  border-radius: 8px;
}

.income-check-total div {
  display: grid;
  gap: 4px;
}

.income-check-total span {
  color: #0f766e;
  font-size: 0.86rem;
  font-weight: 800;
}

.income-check-total strong {
  color: #134e4a;
  font-size: 1.28rem;
}

.income-check-total small {
  flex: 0 0 auto;
  color: #475569;
  font-size: 0.82rem;
  font-weight: 800;
  text-align: right;
}

.income-distribution-bar {
  display: flex;
  height: 12px;
  overflow: hidden;
  margin-top: 12px;
  background: #e2e8f0;
  border-radius: 999px;
}

.income-distribution-bar span {
  min-width: 2px;
}

.income-distribution-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  margin-top: 10px;
}

.income-distribution-legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #475569;
  font-size: 0.8rem;
  font-weight: 800;
}

.income-distribution-legend i {
  width: 8px;
  height: 8px;
  border-radius: 999px;
}

.income-source-list {
  display: grid;
  gap: 10px;
  margin-top: 12px;
}

.income-source-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 8px 12px;
  align-items: center;
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
}

.income-source-main {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.income-source-main span {
  color: #0f172a;
  font-weight: 900;
  overflow-wrap: anywhere;
}

.income-source-main small {
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 800;
}

.income-source-row strong {
  color: #0f172a;
  font-size: 0.94rem;
  white-space: nowrap;
}

.income-source-percent {
  display: inline-flex;
  justify-content: flex-end;
  min-width: 38px;
  color: #64748b;
  font-size: 0.82rem;
  font-weight: 900;
}

.income-check-note,
.income-check-empty {
  margin: 12px 0 0;
  color: #64748b;
  font-size: 0.88rem;
  font-weight: 700;
  line-height: 1.5;
}

.income-check-empty {
  margin: 0;
  padding: 12px;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  background: #f8fafc;
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
  h1 {
    font-size: 1.65rem;
  }

  .mode-switch {
    margin-top: 0.8rem;
  }
}
</style>
