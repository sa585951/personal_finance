<template>
  <div class="analysis-screen">
    <header class="analysis-header">
      <div>
        <p class="eyebrow">Nomica Analysis</p>
        <h1>財務分析</h1>
      </div>
      <input v-model="selectedMonth" type="month" aria-label="分析月份" />
    </header>

    <div class="scope-switch" aria-label="分析範圍">
      <button type="button" :class="{ active: includeTrips }" @click="includeTrips = true">
        含旅行
      </button>
      <button type="button" :class="{ active: !includeTrips }" @click="includeTrips = false">
        日常
      </button>
    </div>

    <div class="analysis-tabs" aria-label="分析檢視">
      <button
        v-for="tab in analysisTabs"
        :key="tab.key"
        type="button"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </div>

    <p v-if="errorMessage" class="state-message error">{{ errorMessage }}</p>
    <p v-else-if="isLoading" class="state-message">分析資料讀取中</p>

    <template v-if="activeTab === 'overview'">
      <section class="summary-card" aria-label="月份收支摘要">
        <div class="summary-heading">
          <div>
            <span>{{ selectedMonthLabel }}</span>
            <strong>{{ monthlyNet >= 0 ? "本月結餘" : "本月超支" }}</strong>
          </div>
          <b :class="monthlyNet >= 0 ? 'positive' : 'negative'">
            {{ formatMoney(Math.abs(monthlyNet)) }}
          </b>
        </div>
        <div class="summary-metrics">
          <div class="income">
            <span>收入</span>
            <strong>+{{ formatMoney(monthlyIncome) }}</strong>
          </div>
          <div class="expense">
            <span>支出</span>
            <strong>-{{ formatMoney(monthlyExpense) }}</strong>
          </div>
        </div>
      </section>

      <section class="status-card">
        <div class="section-heading">
          <div>
            <span>預算狀態</span>
            <h2>{{ budgetStatusLabel }}</h2>
          </div>
          <router-link to="/budgets">管理預算</router-link>
        </div>
        <div class="status-metrics">
          <div>
            <span>總預算</span>
            <strong>{{ formatMoney(totalBudget) }}</strong>
          </div>
          <div>
            <span>已使用</span>
            <strong>{{ budgetUsageRate }}%</strong>
          </div>
          <div>
            <span>需留意</span>
            <strong>{{ budgetAttentionCount }} 類</strong>
          </div>
        </div>
        <div class="progress-track" aria-label="預算使用率">
          <span :class="{ danger: budgetUsageRate > 100 }" :style="{ width: `${budgetProgressWidth}%` }"></span>
        </div>
        <p v-if="budgetSummary.length === 0">這個月份尚未有預算或支出資料。</p>
        <p v-else-if="unbudgetedSpentCount > 0">
          另有 {{ unbudgetedSpentCount }} 個已有支出的分類尚未設定預算。
        </p>
      </section>

      <section class="status-card">
        <div class="section-heading">
          <div>
            <span>旅行摘要</span>
            <h2>{{ includeTrips ? "已納入我的月報" : "目前只看日常" }}</h2>
          </div>
          <router-link to="/trips">查看旅行</router-link>
        </div>
        <div class="status-metrics">
          <div>
            <span>旅行支出</span>
            <strong>{{ formatMoney(monthlyTravelExpense) }}</strong>
          </div>
          <div>
            <span>旅行帳本</span>
            <strong>{{ monthlyTripRows.length }} 個</strong>
          </div>
          <div>
            <span>進行中</span>
            <strong>{{ activeTripCount }} 個</strong>
          </div>
        </div>
        <div v-if="includeTrips && monthlyTripRows.length > 0" class="trip-list">
          <div v-for="trip in monthlyTripRows.slice(0, 3)" :key="trip.id">
            <span>{{ trip.name }}</span>
            <strong>{{ formatMoney(trip.amount) }}</strong>
          </div>
        </div>
        <p v-else-if="includeTrips">本月沒有納入個人月報的旅行分攤。</p>
        <p v-else>切換至「含旅行」可查看已納入月報的個人旅行分攤。</p>
      </section>
    </template>

    <template v-else-if="activeTab === 'spending'">
      <section class="chart-card">
        <div class="chart-switch" aria-label="支出分析切換">
          <button type="button" :class="{ active: spendingView === 'category' }" @click="spendingView = 'category'">
            分類比例
          </button>
          <button type="button" :class="{ active: spendingView === 'trend' }" @click="spendingView = 'trend'">
            變化趨勢
          </button>
        </div>
        <MonthlyExpensesChart
          v-if="spendingView === 'category'"
          :month="selectedMonth"
          :transactions="transactions"
        />
        <SpendingTrendsChart v-else />
      </section>
    </template>

    <template v-else>
      <div class="flow-type-switch" aria-label="資金來源類型">
        <button type="button" :class="{ active: flowType === 'expense' }" @click="flowType = 'expense'">支出</button>
        <button type="button" :class="{ active: flowType === 'income' }" @click="flowType = 'income'">收入</button>
      </div>

      <section v-if="flowType === 'income'" class="source-card">
        <div class="section-heading">
          <div>
            <span>收入來源</span>
            <h2>{{ selectedMonthLabel }}收入組成</h2>
          </div>
          <strong>{{ selectedTypeTransactions.length }} 筆</strong>
        </div>
        <div v-if="incomeSourceRows.length > 0" class="source-list">
          <div v-for="source in incomeSourceRows" :key="source.name" class="source-row">
            <div>
              <i :style="{ background: source.color }"></i>
              <span>{{ source.name }}</span>
              <small>{{ source.count }} 筆</small>
            </div>
            <strong>{{ formatMoney(source.amount) }}</strong>
            <small>{{ Math.round(source.percentage) }}%</small>
          </div>
        </div>
        <p v-else>這個月份尚未記錄收入。</p>
      </section>

      <section class="source-card">
        <div class="section-heading">
          <div>
            <span>{{ flowType === "income" ? "入帳帳戶" : "付款來源" }}</span>
            <h2>依帳戶類型整理</h2>
          </div>
          <strong>{{ selectedTypeTransactions.length }} 筆</strong>
        </div>
        <div v-if="accountFlowGroups.length > 0" class="flow-groups">
          <div v-for="group in accountFlowGroups" :key="group.currency" class="flow-group">
            <div class="flow-total">
              <span>{{ group.currency }} 合計</span>
              <strong>{{ formatMoney(group.total, group.currency) }}</strong>
            </div>
            <div class="flow-bar" :aria-label="`${group.currency} 帳戶類型比例`">
              <span
                v-for="row in group.rows"
                :key="`${group.currency}-${row.key}`"
                :style="{ width: `${row.width}%`, background: row.color }"
              ></span>
            </div>
            <div class="source-list">
              <div v-for="row in group.rows" :key="row.key" class="source-row">
                <div>
                  <i :style="{ background: row.color }"></i>
                  <span>{{ row.label }}</span>
                  <small>{{ row.count }} 筆</small>
                </div>
                <strong>{{ formatMoney(row.amount, group.currency) }}</strong>
                <small>{{ Math.round(row.percentage) }}%</small>
              </div>
            </div>
          </div>
        </div>
        <p v-else>
          這個月份尚未有{{ flowType === "income" ? "入帳" : "付款" }}帳戶資料。
        </p>
      </section>
    </template>
  </div>
</template>

<script>
import apiClient from "@/api";
import MonthlyExpensesChart from "@/components/charts/MonthlyExpensesChart.vue";
import SpendingTrendsChart from "@/components/charts/SpendingTrendsChart.vue";

export default {
  name: "AnalysisView",
  components: {
    MonthlyExpensesChart,
    SpendingTrendsChart,
  },
  data() {
    return {
      selectedMonth: this.defaultMonthKey(),
      includeTrips: true,
      activeTab: "overview",
      spendingView: "category",
      flowType: "expense",
      transactions: [],
      budgetSummary: [],
      trips: [],
      isLoading: false,
      errorMessage: "",
      requestSequence: 0,
    };
  },
  computed: {
    analysisTabs() {
      return [
        { key: "overview", label: "總覽" },
        { key: "spending", label: "支出" },
        { key: "flow", label: "資金來源" },
      ];
    },
    selectedMonthLabel() {
      const [year, month] = String(this.selectedMonth || "").split("-");
      return year && month ? `${year} 年 ${Number(month)} 月` : "指定月份";
    },
    monthlyIncome() {
      return this.transactions
        .filter((transaction) => transaction.type === "income")
        .reduce((sum, transaction) => sum + this.transactionAmount(transaction), 0);
    },
    monthlyExpense() {
      return this.transactions
        .filter((transaction) => transaction.type === "expense")
        .reduce((sum, transaction) => sum + this.transactionAmount(transaction), 0);
    },
    monthlyNet() {
      return this.monthlyIncome - this.monthlyExpense;
    },
    monthlyTravelExpense() {
      if (!this.includeTrips) return 0;
      return this.transactions
        .filter((transaction) => transaction.type === "expense" && transaction.trip_id)
        .reduce((sum, transaction) => sum + this.transactionAmount(transaction), 0);
    },
    tripNameMap() {
      return new Map(this.trips.map((trip) => [trip.id, trip.name || "未命名旅行"]));
    },
    monthlyTripRows() {
      const totals = new Map();
      this.transactions
        .filter((transaction) => transaction.type === "expense" && transaction.trip_id)
        .forEach((transaction) => {
          const current = totals.get(transaction.trip_id) || 0;
          totals.set(transaction.trip_id, current + this.transactionAmount(transaction));
        });
      return Array.from(totals.entries())
        .map(([id, amount]) => ({ id, name: this.tripNameMap.get(id) || "旅行帳本", amount }))
        .sort((left, right) => right.amount - left.amount);
    },
    activeTripCount() {
      return this.trips.filter((trip) => trip.status === "active").length;
    },
    budgetedItems() {
      return this.effectiveBudgetSummary.filter((item) => Number(item.budget || 0) > 0);
    },
    effectiveBudgetSummary() {
      if (this.includeTrips) return this.budgetSummary;
      const spentByCategory = this.transactions
        .filter((transaction) => transaction.type === "expense")
        .reduce((totals, transaction) => {
          const category = transaction.budget_category || "未分類";
          totals[category] = (totals[category] || 0) + this.transactionAmount(transaction);
          return totals;
        }, {});
      return this.budgetSummary.map((item) => {
        const budget = Number(item.budget || 0);
        const spent = Number(spentByCategory[item.category] || 0);
        return {
          ...item,
          spent,
          remaining: budget > 0 ? budget - spent : 0,
        };
      });
    },
    totalBudget() {
      return this.budgetedItems.reduce((sum, item) => sum + Number(item.budget || 0), 0);
    },
    totalBudgetSpent() {
      return this.budgetedItems.reduce((sum, item) => sum + Number(item.spent || 0), 0);
    },
    budgetUsageRate() {
      if (this.totalBudget <= 0) return 0;
      return Math.round((this.totalBudgetSpent / this.totalBudget) * 100);
    },
    budgetProgressWidth() {
      return Math.min(Math.max(this.budgetUsageRate, 0), 100);
    },
    budgetAttentionCount() {
      return this.budgetedItems.filter((item) => {
        const budget = Number(item.budget || 0);
        return budget > 0 && Number(item.spent || 0) / budget >= 0.9;
      }).length;
    },
    unbudgetedSpentCount() {
      return this.effectiveBudgetSummary.filter(
        (item) => Number(item.budget || 0) <= 0 && Number(item.spent || 0) > 0
      ).length;
    },
    budgetStatusLabel() {
      if (this.totalBudget <= 0) return "尚未設定預算";
      if (this.budgetUsageRate > 100) return "本月已有分類超支";
      if (this.budgetAttentionCount > 0) return "有分類接近上限";
      return "目前控制良好";
    },
    selectedTypeTransactions() {
      return this.transactions.filter((transaction) => transaction.type === this.flowType);
    },
    incomeSourceRows() {
      const totals = new Map();
      this.transactions
        .filter((transaction) => transaction.type === "income")
        .forEach((transaction) => {
          const name = transaction.budget_category || "未分類收入";
          const current = totals.get(name) || { name, amount: 0, count: 0 };
          current.amount += this.transactionAmount(transaction);
          current.count += 1;
          totals.set(name, current);
        });
      const total = Array.from(totals.values()).reduce((sum, item) => sum + item.amount, 0);
      const colors = ["#0f766e", "#2563eb", "#f59e0b", "#7c3aed", "#dc2626"];
      return Array.from(totals.values())
        .sort((left, right) => right.amount - left.amount)
        .slice(0, 5)
        .map((item, index) => ({
          ...item,
          color: colors[index % colors.length],
          percentage: total > 0 ? (item.amount / total) * 100 : 0,
        }));
    },
    accountFlowGroups() {
      const palette = ["#0f766e", "#2563eb", "#f59e0b", "#7c3aed", "#dc2626", "#64748b"];
      const groups = new Map();
      this.selectedTypeTransactions.forEach((transaction) => {
        const currency = transaction.base_currency || transaction.currency || "TWD";
        const amount = this.transactionAmount(transaction);
        if (amount <= 0) return;
        const key = transaction.account_id ? transaction.account_type || "other" : "unlinked";
        const groupKey = `${currency}:${key}`;
        const current = groups.get(groupKey) || {
          key,
          currency,
          label: this.translateAccountType(key),
          amount: 0,
          count: 0,
        };
        current.amount += amount;
        current.count += 1;
        groups.set(groupKey, current);
      });

      const byCurrency = Array.from(groups.values()).reduce((result, row) => {
        if (!result[row.currency]) result[row.currency] = [];
        result[row.currency].push(row);
        return result;
      }, {});

      return Object.entries(byCurrency).map(([currency, rows]) => {
        const sortedRows = rows.sort((left, right) => right.amount - left.amount);
        const total = sortedRows.reduce((sum, row) => sum + row.amount, 0);
        return {
          currency,
          total,
          rows: sortedRows.map((row, index) => {
            const percentage = total > 0 ? (row.amount / total) * 100 : 0;
            return {
              ...row,
              color: palette[index % palette.length],
              percentage,
              width: percentage > 0 ? Math.max(percentage, 2) : 0,
            };
          }),
        };
      });
    },
  },
  watch: {
    selectedMonth() {
      this.fetchAnalysisData();
    },
    includeTrips() {
      this.fetchTransactions();
    },
  },
  methods: {
    defaultMonthKey() {
      const now = new Date();
      return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
    },
    transactionAmount(transaction) {
      return Number(transaction.converted_amount ?? transaction.amount ?? 0);
    },
    formatMoney(amount, currency = "TWD") {
      const minorUnit = ["TWD", "JPY", "KRW"].includes(currency) ? 0 : 2;
      return `${currency} ${Number(amount || 0).toLocaleString("zh-TW", {
        minimumFractionDigits: minorUnit,
        maximumFractionDigits: minorUnit,
      })}`;
    },
    translateAccountType(type) {
      const labels = {
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
      return labels[type] || type || "其他";
    },
    async fetchTransactions() {
      const requestId = ++this.requestSequence;
      this.isLoading = true;
      this.errorMessage = "";
      try {
        const items = [];
        let cursor = null;
        let hasMore = true;
        while (hasMore) {
          const params = {
            month: this.selectedMonth,
            limit: 50,
            monthly_report: this.includeTrips ? "true" : "false",
          };
          if (cursor) params.cursor = cursor;
          const response = await apiClient.get("/api/transactions", { params });
          items.push(...(response.data.data || []));
          const pagination = response.data.pagination || {};
          hasMore = pagination.has_more === true;
          cursor = pagination.next_cursor || null;
          if (hasMore && !cursor) break;
        }
        if (requestId === this.requestSequence) this.transactions = items;
      } catch (error) {
        if (requestId === this.requestSequence) {
          this.transactions = [];
          this.errorMessage = error.response?.data?.message || "無法載入分析資料，請稍後再試。";
        }
      } finally {
        if (requestId === this.requestSequence) this.isLoading = false;
      }
    },
    async fetchBudgetSummary() {
      try {
        const response = await apiClient.get(`/api/budgets/summary/${this.selectedMonth}`);
        this.budgetSummary = response.data.data || [];
      } catch (error) {
        console.error("無法載入分析頁預算摘要", error);
        this.budgetSummary = [];
      }
    },
    async fetchTrips() {
      try {
        const response = await apiClient.get("/api/trips");
        this.trips = response.data.data || [];
      } catch (error) {
        console.error("無法載入分析頁旅行摘要", error);
        this.trips = [];
      }
    },
    async fetchAnalysisData() {
      await Promise.all([
        this.fetchTransactions(),
        this.fetchBudgetSummary(),
      ]);
    },
  },
  created() {
    this.fetchTrips();
    this.fetchAnalysisData();
  },
};
</script>

<style scoped>
.analysis-screen {
  max-width: 720px;
  min-height: calc(100vh - 80px);
  margin: 0 auto;
  padding: 24px 14px calc(var(--app-bottom-nav-height) + 22px);
  color: #1f2933;
}

.analysis-header,
.summary-heading,
.section-heading,
.flow-total {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.analysis-header {
  align-items: flex-end;
  margin-bottom: 14px;
}

.eyebrow {
  margin: 0 0 4px;
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 700;
}

h1,
h2 {
  margin: 0;
  letter-spacing: 0;
}

h1 {
  color: var(--text-color);
  font-size: 1.85rem;
}

h2 {
  color: #0f172a;
  font-size: 1.05rem;
}

.analysis-header input {
  min-height: 40px;
  max-width: 145px;
  padding: 0 9px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
}

.scope-switch,
.analysis-tabs,
.chart-switch,
.flow-type-switch {
  display: grid;
  gap: 6px;
  padding: 6px;
  background: #e2e8f0;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
}

.scope-switch,
.chart-switch,
.flow-type-switch {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.analysis-tabs {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin: 10px 0 14px;
}

.scope-switch button,
.analysis-tabs button,
.chart-switch button,
.flow-type-switch button {
  min-height: 40px;
  padding: 0 8px;
  color: #475569;
  background: transparent;
  border: 0;
  border-radius: 8px;
  box-shadow: none;
  font-weight: 900;
}

.scope-switch button.active,
.analysis-tabs button.active,
.chart-switch button.active,
.flow-type-switch button.active {
  color: #0f172a;
  background: #ffffff;
}

.summary-card,
.status-card,
.chart-card,
.source-card {
  margin-top: 12px;
  padding: 16px;
  border: 1px solid #dbe4ee;
  border-radius: 10px;
  background: #ffffff;
}

.summary-card {
  color: #ffffff;
  background: #123c3b;
  border-color: #123c3b;
}

.summary-heading div,
.section-heading div {
  display: grid;
  gap: 3px;
}

.summary-heading span,
.section-heading span,
.status-metrics span,
.summary-metrics span {
  color: #64748b;
  font-size: 0.8rem;
  font-weight: 800;
}

.summary-heading span {
  color: #b9d9d4;
}

.summary-heading strong {
  font-size: 0.92rem;
}

.summary-heading b {
  font-size: 1.35rem;
  white-space: nowrap;
}

.summary-heading b.positive {
  color: #d9f99d;
}

.summary-heading b.negative {
  color: #fdba74;
}

.summary-metrics,
.status-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 14px;
}

.summary-metrics {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.summary-metrics div,
.status-metrics div {
  display: grid;
  gap: 4px;
  min-width: 0;
  padding: 11px;
  border-radius: 8px;
  background: #f8fafc;
}

.summary-metrics div {
  background: rgba(255, 255, 255, 0.1);
}

.summary-metrics span {
  color: #d8e8e5;
}

.summary-metrics strong,
.status-metrics strong {
  color: #0f172a;
  font-size: 0.9rem;
  overflow-wrap: anywhere;
}

.summary-metrics strong {
  color: #ffffff;
}

.section-heading a {
  flex: 0 0 auto;
  color: #0f766e;
  font-size: 0.84rem;
  font-weight: 900;
  text-decoration: none;
}

.section-heading > strong {
  color: #64748b;
  font-size: 0.82rem;
}

.progress-track,
.flow-bar {
  display: flex;
  height: 10px;
  overflow: hidden;
  margin-top: 12px;
  background: #e2e8f0;
  border-radius: 999px;
}

.progress-track span {
  background: #0f766e;
}

.progress-track span.danger {
  background: #dc2626;
}

.status-card > p,
.source-card > p {
  margin: 12px 0 0;
  color: #64748b;
  font-size: 0.84rem;
  font-weight: 700;
  line-height: 1.5;
}

.trip-list,
.source-list,
.flow-groups {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}

.trip-list div,
.source-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-height: 42px;
  padding: 10px 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.trip-list span,
.source-row span {
  color: #0f172a;
  font-weight: 800;
}

.trip-list strong,
.source-row strong {
  white-space: nowrap;
}

.chart-switch,
.flow-type-switch {
  margin-bottom: 12px;
}

.flow-type-switch {
  margin-top: 12px;
}

.flow-group {
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.flow-total span {
  color: #64748b;
  font-size: 0.82rem;
  font-weight: 800;
}

.flow-bar span {
  min-width: 2px;
}

.source-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
}

.source-row > div {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
}

.source-row i {
  flex: 0 0 auto;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.source-row small {
  color: #64748b;
  font-size: 0.76rem;
  font-weight: 800;
}

.state-message {
  margin: 12px 0 0;
  padding: 10px 12px;
  color: #475569;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-weight: 800;
}

.state-message.error {
  color: #b91c1c;
  background: #fef2f2;
  border-color: #fecaca;
}

@media (max-width: 430px) {
  .analysis-header {
    align-items: stretch;
    flex-direction: column;
  }

  .analysis-header input {
    width: 100%;
    max-width: none;
  }

  .summary-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .status-metrics {
    grid-template-columns: 1fr;
  }

  .source-row {
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .source-row > small {
    grid-column: 2;
    text-align: right;
  }
}
</style>
