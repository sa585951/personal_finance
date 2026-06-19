<template>
  <div class="home-screen">
    <header class="home-header">
      <p class="eyebrow">Nomica</p>
      <h1>今天的財務狀態</h1>
    </header>

    <section class="monthly-overview-card" aria-label="本月月報">
      <div class="overview-card-header">
        <span>{{ monthlyNet >= 0 ? "本月結餘" : "本月超支" }}</span>
        <span>{{ currentMonth }} · {{ includeTripsInHome ? "含旅行" : "日常" }}</span>
      </div>
      <p class="overview-balance">
        {{ monthlyNet < 0 ? "-" : "" }}{{ formatDisplayMoney(Math.abs(monthlyNet)) }}
      </p>
      <div class="overview-scope-toggle" aria-label="月報範圍">
        <button
          type="button"
          :class="{ active: includeTripsInHome }"
          @click="includeTripsInHome = true"
        >
          含旅行
        </button>
        <button
          type="button"
          :class="{ active: !includeTripsInHome }"
          @click="includeTripsInHome = false"
        >
          日常
        </button>
      </div>
      <div class="overview-stats">
        <div>
          <p>收入</p>
          <strong>+{{ formatDisplayMoney(monthlyIncome) }}</strong>
        </div>
        <div>
          <p>支出</p>
          <strong>-{{ formatDisplayMoney(monthlyExpense) }}</strong>
        </div>
      </div>
      <div class="income-expense-ratio" aria-label="收入支出比例">
        <div class="ratio-labels">
          <span>收入 {{ monthlyIncomeRatio }}%</span>
          <span>支出 {{ monthlyExpenseRatio }}%</span>
        </div>
        <p class="ratio-helper">
          本月現金流比例，收入與支出合計為 100%
        </p>
        <div class="ratio-track">
          <div
            class="ratio-fill income"
            :style="{ width: `${monthlyIncomeRatio}%` }"
          ></div>
          <div
            class="ratio-fill expense"
            :style="{ width: `${monthlyExpenseRatio}%` }"
          ></div>
        </div>
      </div>
      <div class="overview-expense-source">
        <span>主要支出來源</span>
        <strong>{{ expenseSourceTitle }}</strong>
        <p>{{ expenseSourceDescription }}</p>
      </div>
    </section>

    <section class="insights-panel" aria-label="Nomica Insights">
      <div class="section-heading">
        <h2>Nomica Insights</h2>
        <span>{{ insightSummaryText }}</span>
      </div>

      <div v-if="insightItems.length === 0" class="insight-empty">
        <span>狀態良好</span>
        <strong>目前沒有需要處理的提醒</strong>
        <p>預算、旅行與帳戶狀態暫時沒有明顯警示；需要細看時可進入各頁面。</p>
      </div>

      <div v-else class="insight-list">
        <div class="insight-summary-strip" aria-label="提醒層級統計">
          <span>需要處理 {{ needsActionInsights.length }}</span>
          <span>值得注意 {{ attentionInsights.length }}</span>
          <span>資訊 {{ infoInsights.length }}</span>
        </div>
        <router-link
          v-for="insight in insightItems"
          :key="insight.key"
          class="insight-card"
          :class="insight.level"
          :to="insight.to"
        >
          <div class="insight-marker" aria-hidden="true"></div>
          <div class="insight-content">
            <span>{{ insight.group }}</span>
            <strong>{{ insight.title }}</strong>
            <p>{{ insight.description }}</p>
          </div>
          <span class="insight-action">{{ insight.action }}</span>
        </router-link>
      </div>
    </section>

    <section class="daily-summary-panel" aria-label="今日與本週摘要">
      <div class="section-heading">
        <h2>今日 / 本週摘要</h2>
        <span>{{ includeTripsInHome ? "含旅行" : "日常" }}</span>
      </div>
      <div class="daily-summary-grid">
        <div class="summary-card today">
          <span>今日支出</span>
          <strong>{{ formatDisplayMoney(todayExpense) }}</strong>
          <p>{{ todayExpense > 0 ? "今天已記錄的支出" : "今天還沒有支出紀錄" }}</p>
        </div>
        <div class="summary-card week">
          <span>本週支出</span>
          <strong>{{ formatDisplayMoney(weekExpense) }}</strong>
          <p>{{ weekExpense > 0 ? "本週累計支出" : "本週還沒有支出紀錄" }}</p>
        </div>
      </div>
      <router-link
        v-if="!latestTransaction"
        class="summary-empty-action"
        to="/transactions?type=expense"
      >
        今天還沒有紀錄，先記一筆支出
      </router-link>
      <div v-else class="latest-summary">
        <span>最近一筆</span>
        <strong>
          {{ latestTransaction.category || latestTransaction.budget_category || "未命名紀錄" }}
          <small v-if="latestTransaction.trip_id">旅行</small>
        </strong>
        <p>
          {{ formatShortDate(latestTransaction.date) }} ·
          {{ latestTransaction.type === "income" ? "收入" : "支出" }}
          {{ latestTransaction.type === "income" ? "+" : "-" }}{{ formatMoney(monthlyReportAmount(latestTransaction), latestTransaction.base_currency || "TWD") }}
        </p>
      </div>
    </section>

    <section class="status-panel">
      <div class="section-heading">
        <h2>旅行狀態</h2>
        <router-link to="/trips">查看</router-link>
      </div>
      <div class="trip-status">
        <span>進行中或已建立</span>
        <strong>{{ activeTrips.length }} 個旅行帳本</strong>
      </div>
    </section>

    <section class="recent-panel">
      <div class="section-heading">
        <h2>近期紀錄</h2>
        <router-link to="/transactions">全部</router-link>
      </div>
      <div v-if="recentTransactions.length === 0" class="empty-state">尚無月報交易紀錄</div>
      <div v-else class="recent-list">
        <div
          v-for="transaction in recentTransactions"
          :key="transaction.id"
          class="recent-row"
        >
          <div>
            <strong>
              {{ transaction.category }}
              <span v-if="transaction.trip_id" class="scope-badge">旅行</span>
            </strong>
            <span>
              {{ formatShortDate(transaction.date) }} · {{ transaction.budget_category }}
              <template v-if="transaction.trip_id && transaction.currency !== transaction.base_currency">
                · {{ formatMoney(transaction.amount, transaction.currency) }}
              </template>
            </span>
          </div>
          <strong :class="transaction.type === 'income' ? 'income' : 'expense'">
            {{ transaction.type === "income" ? "+" : "-" }}{{ formatMoney(monthlyReportAmount(transaction), transaction.base_currency || "TWD") }}
          </strong>
        </div>
      </div>
    </section>
  </div>
</template>

<script>
import apiClient from "@/api";

export default {
  name: "HomeView",
  data() {
    return {
      transactions: [],
      monthlyReportTransactions: [],
      trips: [],
      overspendingWarnings: [],
      assets: {},
      budgetSummary: [],
      includeTripsInHome: true,
    };
  },
  computed: {
    currentMonth() {
      return new Date().toISOString().slice(0, 7);
    },
    dashboardTransactions() {
      if (this.includeTripsInHome) {
        return this.monthlyReportTransactions;
      }
      return this.transactions.filter((transaction) => !transaction.trip_id);
    },
    monthTransactions() {
      return this.dashboardTransactions.filter((transaction) => transaction.date?.startsWith(this.currentMonth));
    },
    monthlyIncome() {
      return this.monthTransactions
        .filter((transaction) => transaction.type === "income")
        .reduce((sum, transaction) => sum + this.monthlyReportAmount(transaction), 0);
    },
    monthlyExpense() {
      return this.monthTransactions
        .filter((transaction) => transaction.type === "expense")
        .reduce((sum, transaction) => sum + this.monthlyReportAmount(transaction), 0);
    },
    monthlyNet() {
      return this.monthlyIncome - this.monthlyExpense;
    },
    monthlyTotalFlow() {
      return Math.max(this.monthlyIncome + this.monthlyExpense, 0);
    },
    monthlyIncomeRatio() {
      if (this.monthlyTotalFlow <= 0) return 0;
      return Math.round((this.monthlyIncome / this.monthlyTotalFlow) * 100);
    },
    monthlyExpenseRatio() {
      if (this.monthlyTotalFlow <= 0) return 0;
      return 100 - this.monthlyIncomeRatio;
    },
    monthlyDailyExpense() {
      return this.monthTransactions
        .filter((transaction) => transaction.type === "expense" && !transaction.trip_id)
        .reduce((sum, transaction) => sum + this.monthlyReportAmount(transaction), 0);
    },
    monthlyTravelExpense() {
      if (!this.includeTripsInHome) return 0;
      return this.monthTransactions
        .filter((transaction) => transaction.type === "expense" && transaction.trip_id)
        .reduce((sum, transaction) => sum + this.monthlyReportAmount(transaction), 0);
    },
    primaryExpenseSource() {
      const sources = [
        { label: "日常生活", amount: this.monthlyDailyExpense },
      ];

      if (this.includeTripsInHome) {
        sources.push({ label: "旅行", amount: this.monthlyTravelExpense });
      }

      return sources.sort((a, b) => b.amount - a.amount)[0] || { label: "尚無支出", amount: 0 };
    },
    expenseSourceTitle() {
      if (this.monthlyExpense <= 0) return "尚無本月支出";
      const percent = Math.round((this.primaryExpenseSource.amount / this.monthlyExpense) * 100);
      return `${this.primaryExpenseSource.label} ${percent}%`;
    },
    expenseSourceDescription() {
      if (this.monthlyExpense <= 0) {
        return "記錄支出後，這裡會顯示本月主要支出來自日常或旅行。";
      }

      const daily = this.formatDisplayMoney(this.monthlyDailyExpense);
      if (!this.includeTripsInHome) {
        return `日常支出 ${daily}。`;
      }

      return `日常 ${daily} · 旅行 ${this.formatDisplayMoney(this.monthlyTravelExpense)}。`;
    },
    activeTrips() {
      return this.trips.filter((trip) => trip.status === "active");
    },
    recentTransactions() {
      return this.dashboardTransactions.slice(0, 5);
    },
    todayExpense() {
      return this.dashboardTransactions
        .filter((transaction) => (
          transaction.type === "expense"
          && this.transactionDateKey(transaction) === this.todayKey()
        ))
        .reduce((sum, transaction) => sum + this.monthlyReportAmount(transaction), 0);
    },
    weekExpense() {
      const weekStart = this.weekStartKey();
      const today = this.todayKey();
      return this.dashboardTransactions
        .filter((transaction) => {
          const dateKey = this.transactionDateKey(transaction);
          return transaction.type === "expense" && dateKey >= weekStart && dateKey <= today;
        })
        .reduce((sum, transaction) => sum + this.monthlyReportAmount(transaction), 0);
    },
    latestTransaction() {
      return [...this.dashboardTransactions].sort((a, b) => {
        const aCreated = a.created_at || "";
        const bCreated = b.created_at || "";
        const dateCompare = this.transactionDateKey(b).localeCompare(this.transactionDateKey(a));
        if (dateCompare !== 0) return dateCompare;
        return bCreated.localeCompare(aCreated);
      })[0] || null;
    },
    totalOverspending() {
      return this.overspendingWarnings.reduce(
        (sum, warning) => sum + Number(warning.overspend || 0),
        0
      );
    },
    overspendingCategoryText() {
      return this.overspendingWarnings
        .slice(0, 2)
        .map((warning) => warning.category)
        .join("、");
    },
    creditCardAccountsToCheck() {
      return Object.values(this.assets || {})
        .filter((asset) => (
          asset.account_type === "credit_card" && Number(asset.balance || 0) < 0
        ))
        .sort((a, b) => Math.abs(Number(b.balance || 0)) - Math.abs(Number(a.balance || 0)));
    },
    nearlyUsedBudgets() {
      return this.budgetSummary
        .filter((item) => {
          const budget = Number(item.budget || 0);
          const spent = Number(item.spent || 0);
          const remaining = Number(item.remaining || 0);
          return budget > 0 && remaining >= 0 && spent / budget >= 0.9;
        })
        .sort((a, b) => {
          const aRatio = Number(a.spent || 0) / Number(a.budget || 1);
          const bRatio = Number(b.spent || 0) / Number(b.budget || 1);
          return bRatio - aRatio;
        });
    },
    largestMonthlyExpense() {
      return this.monthTransactions
        .filter((transaction) => transaction.type === "expense")
        .sort((a, b) => this.monthlyReportAmount(b) - this.monthlyReportAmount(a))[0] || null;
    },
    pendingMonthlyReportTrips() {
      return this.activeTrips.filter((trip) => this.tripMonthlyPreference(trip) === "pending");
    },
    needsActionInsights() {
      const items = [];

      this.creditCardAccountsToCheck.slice(0, 1).forEach((asset) => {
        items.push({
          key: `credit-card-${asset.account_key || asset.id}`,
          level: "needs-action",
          group: "需要處理",
          title: `${asset.bank_name || "信用卡"}待核對`,
          description: `目前餘額為 ${this.formatMoney(asset.balance, asset.currency || "TWD")}，請到帳戶頁確認刷卡或還款紀錄。`,
          action: "看帳戶",
          to: "/assets",
        });
      });

      if (this.overspendingWarnings.length > 0) {
        items.push({
          key: "budget-overspending",
          level: "needs-action",
          group: "需要處理",
          title: `${this.overspendingWarnings.length} 個分類預算超支`,
          description: `本月已超出 ${this.formatDisplayMoney(this.totalOverspending)}，優先檢查 ${this.overspendingCategoryText}。`,
          action: "看預算",
          to: "/budgets",
        });
      }

      if (this.pendingMonthlyReportTrips.length > 0) {
        items.push({
          key: "trip-monthly-report-pending",
          level: "needs-action",
          group: "需要處理",
          title: `${this.pendingMonthlyReportTrips.length} 個旅行尚未決定月報`,
          description: "請決定是否把自己的旅行分攤金額納入月報與預算統計。",
          action: "看旅行",
          to: "/trips",
        });
      }

      return items;
    },
    attentionInsights() {
      const items = [];

      if (this.overspendingWarnings.length === 0) {
        this.nearlyUsedBudgets.slice(0, 1).forEach((item) => {
          const ratio = Math.round((Number(item.spent || 0) / Number(item.budget || 1)) * 100);
          items.push({
            key: `budget-near-limit-${item.category}`,
            level: "attention",
            group: "值得注意",
            title: `${item.category} 預算快用完`,
            description: `已使用 ${ratio}%，剩餘 ${this.formatDisplayMoney(item.remaining)}。`,
            action: "看預算",
            to: "/budgets",
          });
        });
      }

      const activeDecidedTrips = this.activeTrips.filter(
        (trip) => this.tripMonthlyPreference(trip) !== "pending"
      );
      if (activeDecidedTrips.length > 0) {
        items.push({
          key: "active-trips",
          level: "attention",
          group: "值得注意",
          title: `${activeDecidedTrips.length} 個旅行帳本可核對`,
          description: "旅行分帳與結算狀態請到旅行頁確認，首頁只提示入口。",
          action: "看旅行",
          to: "/trips",
        });
      }

      return items;
    },
    infoInsights() {
      if (!this.largestMonthlyExpense) return [];
      return [
        {
          key: `largest-expense-${this.largestMonthlyExpense.id}`,
          level: "info",
          group: "資訊",
          title: "本月最大支出",
          description: `${this.largestMonthlyExpense.category || "未分類"} ${this.formatMoney(
            this.monthlyReportAmount(this.largestMonthlyExpense),
            this.largestMonthlyExpense.base_currency || "TWD"
          )}`,
          action: "看收支",
          to: "/transactions?type=expense",
        },
      ];
    },
    insightSummaryText() {
      if (this.needsActionInsights.length > 0) {
        return `需要處理 ${this.needsActionInsights.length}`;
      }
      if (this.attentionInsights.length > 0) {
        return `值得注意 ${this.attentionInsights.length}`;
      }
      return "狀態良好";
    },
    insightItems() {
      return [
        ...this.needsActionInsights.slice(0, 3),
        ...this.attentionInsights.slice(0, 2),
        ...this.infoInsights.slice(0, 1),
      ].slice(0, 4);
    },
  },
  methods: {
    async fetchDashboardData() {
      try {
        const response = await apiClient.get("/api/dashboard/overview");
        const overview = response.data.data || {};
        this.transactions = overview.transactions || [];
        this.monthlyReportTransactions = overview.monthly_report_transactions || [];
        this.trips = overview.trips || [];
      } catch (error) {
        console.error("無法載入首頁資料", error);
        this.transactions = [];
        this.monthlyReportTransactions = [];
        this.trips = [];
      }
    },
    async fetchOverspendingWarnings() {
      try {
        const response = await apiClient.get(`/api/reports/overspending_warnings?month=${this.currentMonth}`);
        this.overspendingWarnings = response.data.data || [];
      } catch (error) {
        console.error("無法載入首頁超支提醒", error);
        this.overspendingWarnings = [];
      }
    },
    async fetchAssets() {
      try {
        const response = await apiClient.get("/api/assets");
        this.assets = response.data.data || {};
      } catch (error) {
        console.error("無法載入首頁帳戶提醒", error);
        this.assets = {};
      }
    },
    async fetchBudgetSummary() {
      try {
        const response = await apiClient.get(`/api/budgets/summary/${this.currentMonth}`);
        this.budgetSummary = response.data.data || [];
      } catch (error) {
        console.error("無法載入首頁預算摘要", error);
        this.budgetSummary = [];
      }
    },
    formatMoney(amount, currency = "TWD") {
      const minorUnit = ["TWD", "JPY", "KRW"].includes(currency) ? 0 : 2;
      return `${currency} ${Number(amount || 0).toLocaleString("zh-TW", {
        minimumFractionDigits: minorUnit,
        maximumFractionDigits: minorUnit,
      })}`;
    },
    formatDisplayMoney(amount, currency = "TWD") {
      const minorUnit = ["TWD", "JPY", "KRW"].includes(currency) ? 0 : 2;
      const symbolMap = {
        TWD: "NT$",
        JPY: "JP¥",
        KRW: "₩",
        USD: "US$",
        EUR: "€",
      };
      return `${symbolMap[currency] || `${currency} `}${Number(amount || 0).toLocaleString("zh-TW", {
        minimumFractionDigits: minorUnit,
        maximumFractionDigits: minorUnit,
      })}`;
    },
    monthlyReportAmount(transaction) {
      return Number(transaction.converted_amount ?? transaction.amount ?? 0);
    },
    dateKey(date) {
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, "0");
      const day = String(date.getDate()).padStart(2, "0");
      return `${year}-${month}-${day}`;
    },
    todayKey() {
      return this.dateKey(new Date());
    },
    weekStartKey() {
      const today = new Date();
      const day = today.getDay();
      const diffToMonday = day === 0 ? -6 : 1 - day;
      const monday = new Date(today);
      monday.setDate(today.getDate() + diffToMonday);
      return this.dateKey(monday);
    },
    transactionDateKey(transaction) {
      return String(transaction?.date || "").slice(0, 10);
    },
    tripMonthlyPreference(trip) {
      const currentMember = (trip.members || []).find(
        (member) => member.id === trip.current_member_id
      );
      return currentMember?.monthly_report_preference || null;
    },
    formatShortDate(dateString) {
      if (!dateString) return "";
      const date = new Date(dateString);
      return `${date.getMonth() + 1}月${date.getDate()}日`;
    },
  },
  created() {
    this.fetchDashboardData();
    this.fetchOverspendingWarnings();
    this.fetchAssets();
    this.fetchBudgetSummary();
  },
};
</script>

<style scoped>
.home-screen {
  max-width: 520px;
  min-height: calc(100vh - 80px);
  margin: 0 auto;
  padding: 24px 14px calc(var(--app-bottom-nav-height) + 22px);
  color: #1f2933;
}

.home-header {
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

h1,
h2 {
  margin: 0;
  letter-spacing: 0;
}

h1 {
  font-size: 1.85rem;
}

.daily-summary-panel,
.insights-panel,
.status-panel,
.recent-panel {
  padding: 16px;
  margin-top: 1rem;
  background: #ffffff;
  border: 1px solid #dbe4ee;
  border-radius: 10px;
}

.daily-summary-panel {
  display: grid;
  gap: 12px;
}

.daily-summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.summary-card {
  display: grid;
  gap: 6px;
  min-width: 0;
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.summary-card span,
.latest-summary span {
  color: #64748b;
  font-size: 0.76rem;
  font-weight: 900;
}

.summary-card strong {
  color: #1f2933;
  font-size: 1.1rem;
  font-weight: 900;
  overflow-wrap: anywhere;
}

.summary-card p,
.latest-summary p {
  margin: 0;
  color: #64748b;
  font-size: 0.8rem;
  line-height: 1.4;
}

.latest-summary,
.summary-empty-action {
  display: grid;
  gap: 5px;
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.latest-summary strong {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  min-width: 0;
  color: #1f2933;
  font-size: 0.98rem;
}

.latest-summary small {
  display: inline-flex;
  align-items: center;
  min-height: 20px;
  padding: 0 7px;
  color: #0369a1;
  background: #e0f2fe;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 900;
}

.summary-empty-action {
  color: #0f766e;
  font-size: 0.9rem;
  font-weight: 900;
  text-align: center;
  text-decoration: none;
}

.insights-panel {
  display: grid;
  gap: 12px;
}

.insight-list {
  display: grid;
  gap: 10px;
}

.insight-summary-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
}

.insight-summary-strip span {
  min-width: 0;
  min-height: 30px;
  padding: 7px 8px;
  color: #334155;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.76rem;
  font-weight: 900;
  text-align: center;
  white-space: nowrap;
}

.insight-summary-strip span:first-child {
  color: #9a3412;
  background: #fff7ed;
  border-color: #fed7aa;
}

.insight-summary-strip span:nth-child(2) {
  color: #1d4ed8;
  background: #eff6ff;
  border-color: #bfdbfe;
}

.insight-card,
.insight-empty {
  display: grid;
  gap: 8px;
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.insight-card {
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  color: #334155;
  text-decoration: none;
}

.insight-card.needs-action {
  background: #fff7ed;
  border-color: #fed7aa;
}

.insight-card.attention {
  background: #f8fafc;
  border-color: #dbe4ee;
}

.insight-card.info {
  background: #f8fafc;
  border-color: #e2e8f0;
}

.insight-marker {
  width: 10px;
  height: 42px;
  border-radius: 999px;
  background: #64748b;
}

.insight-card.needs-action .insight-marker {
  background: #f97316;
}

.insight-card.attention .insight-marker {
  background: #2563eb;
}

.insight-card.info .insight-marker {
  background: #64748b;
}

.insight-content {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.insight-content span {
  color: #64748b;
  font-size: 0.72rem;
  font-weight: 900;
}

.insight-empty span {
  color: #0f766e;
  font-size: 0.72rem;
  font-weight: 900;
}

.insight-content strong {
  color: #1f2933;
  font-size: 0.96rem;
  font-weight: 900;
}

.insight-content p,
.insight-empty p {
  margin: 0;
  color: #64748b;
  font-size: 0.8rem;
  line-height: 1.4;
}

.insight-empty strong {
  color: #0f766e;
  font-size: 0.98rem;
}

.insight-action {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  color: #0f172a;
  background: #ffffff;
  border: 1px solid #dbe4ee;
  border-radius: 999px;
  font-size: 0.76rem;
  font-weight: 900;
  white-space: nowrap;
}

.monthly-overview-card {
  position: relative;
  padding: 24px;
  margin-top: 1rem;
  overflow: hidden;
  color: #ffffff;
  background: linear-gradient(135deg, #0f766e, #2563eb);
  border-radius: 16px;
}

.overview-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.overview-card-header span:first-child {
  padding: 5px 8px;
  color: #0f766e;
  background: #ccfbf1;
  border-radius: 6px;
  font-size: 0.68rem;
  font-weight: 900;
  letter-spacing: 0;
}

.overview-card-header span:last-child {
  color: rgba(255, 255, 255, 0.72);
  font-size: 0.7rem;
  font-weight: 800;
}

.overview-balance {
  margin: 0;
  font-size: 3rem;
  font-weight: 900;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.overview-scope-toggle {
  display: inline-grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 4px;
  padding: 4px;
  margin-top: 18px;
  background: rgba(255, 255, 255, 0.16);
  border-radius: 8px;
}

.overview-scope-toggle button {
  min-height: 32px;
  padding: 0 12px;
  color: rgba(255, 255, 255, 0.74);
  background: transparent;
  border: 0;
  border-radius: 6px;
  box-shadow: none;
  font-size: 0.82rem;
  font-weight: 900;
}

.overview-scope-toggle button.active {
  color: #0f766e;
  background: #ffffff;
}

.overview-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 18px;
}

.overview-stats p {
  margin: 0;
  color: rgba(255, 255, 255, 0.64);
  font-size: 0.7rem;
  font-weight: 900;
}

.overview-stats strong {
  display: block;
  margin-top: 2px;
  font-size: 0.92rem;
  font-weight: 800;
}

.income-expense-ratio {
  display: grid;
  gap: 8px;
  margin-top: 16px;
}

.ratio-labels {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: rgba(255, 255, 255, 0.78);
  font-size: 0.72rem;
  font-weight: 900;
}

.ratio-helper {
  margin: -2px 0 0;
  color: rgba(255, 255, 255, 0.66);
  font-size: 0.72rem;
  line-height: 1.4;
}

.ratio-track {
  display: flex;
  width: 100%;
  height: 10px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.18);
  border-radius: 999px;
}

.ratio-fill {
  min-width: 0;
  transition: width 0.2s ease;
}

.ratio-fill.income {
  background: #ccfbf1;
}

.ratio-fill.expense {
  background: #fecaca;
}

.overview-expense-source {
  display: grid;
  gap: 4px;
  padding: 12px;
  margin-top: 16px;
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 8px;
}

.overview-expense-source span {
  color: rgba(255, 255, 255, 0.66);
  font-size: 0.7rem;
  font-weight: 900;
}

.overview-expense-source strong {
  color: #ffffff;
  font-size: 0.96rem;
  font-weight: 900;
}

.overview-expense-source p {
  margin: 0;
  color: rgba(255, 255, 255, 0.72);
  font-size: 0.76rem;
  line-height: 1.45;
}

.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.section-heading h2 {
  font-size: 1.08rem;
}

.section-heading span,
.section-heading a {
  color: #64748b;
  font-size: 0.86rem;
  font-weight: 700;
  text-decoration: none;
}

.trip-status {
  display: grid;
  gap: 4px;
  min-height: 68px;
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.trip-status span {
  color: #64748b;
  font-size: 0.86rem;
  font-weight: 700;
}

.trip-status strong {
  color: #1f2933;
}

.recent-list {
  display: grid;
  gap: 8px;
}

.recent-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 58px;
  padding: 10px 0;
  border-bottom: 1px solid #e2e8f0;
}

.recent-row:last-child {
  border-bottom: 0;
}

.recent-row div {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.recent-row div > strong {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.recent-row span {
  color: #64748b;
  font-size: 0.86rem;
}

.scope-badge {
  display: inline-flex;
  align-items: center;
  min-height: 20px;
  padding: 0 7px;
  color: #0369a1;
  background: #e0f2fe;
  border-radius: 999px;
  font-size: 0.76rem;
  font-weight: 800;
}

.recent-row .income {
  color: #0f766e;
}

.recent-row .expense {
  color: #dc2626;
}

.empty-state {
  padding: 1rem;
  color: #64748b;
  text-align: center;
  background: #f8fafc;
  border-radius: 8px;
}

@media (min-width: 900px) {
  .home-screen {
    padding-top: 36px;
  }
}

@media (max-width: 420px) {
  .monthly-overview-card {
    padding: 20px;
  }

  .overview-balance {
    font-size: 2.4rem;
  }

  .daily-summary-grid {
    grid-template-columns: 1fr;
  }

  .insight-card {
    grid-template-columns: 1fr;
  }

  .insight-summary-strip {
    grid-template-columns: 1fr;
  }

  .insight-marker {
    width: 100%;
    height: 6px;
  }
}
</style>
