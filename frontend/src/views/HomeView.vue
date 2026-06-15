<template>
  <div class="home-screen">
    <header class="home-header">
      <p class="eyebrow">Nomica</p>
      <h1>今天要記什麼？</h1>
    </header>

    <section class="quick-actions" aria-label="快速入口">
      <router-link class="action-card expense" to="/transactions?type=expense">
        <span>記一筆支出</span>
        <strong>日常消費</strong>
      </router-link>
      <router-link class="action-card trip" to="/trips">
        <span>旅行帳本</span>
        <strong>記旅行 / 分帳</strong>
      </router-link>
    </section>

    <section class="secondary-actions" aria-label="常用入口">
      <router-link to="/budgets">看預算</router-link>
      <router-link to="/assets">看帳戶</router-link>
    </section>

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
    activeTrips() {
      return this.trips.filter((trip) => trip.status === "active");
    },
    recentTransactions() {
      return this.dashboardTransactions.slice(0, 5);
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
    formatShortDate(dateString) {
      if (!dateString) return "";
      const date = new Date(dateString);
      return `${date.getMonth() + 1}月${date.getDate()}日`;
    },
  },
  created() {
    this.fetchDashboardData();
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

.quick-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.action-card {
  display: grid;
  align-content: space-between;
  gap: 8px;
  aspect-ratio: 1 / 1;
  min-height: 132px;
  padding: 14px;
  border-radius: 8px;
  text-decoration: none;
}

.action-card span {
  font-size: 1.18rem;
  font-weight: 800;
}

.action-card strong {
  font-size: 0.9rem;
}

.action-card.expense {
  color: #ffffff;
  background: #2563eb;
}

.action-card.trip {
  color: #ffffff;
  background: #0891b2;
}

.secondary-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 1rem;
}

.secondary-actions a {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 42px;
  padding: 0 10px;
  color: #334155;
  background: #ffffff;
  border: 1px solid #dbe4ee;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 800;
  text-decoration: none;
}

.status-panel,
.recent-panel {
  padding: 16px;
  margin-top: 1rem;
  background: #ffffff;
  border: 1px solid #dbe4ee;
  border-radius: 10px;
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
}
</style>
