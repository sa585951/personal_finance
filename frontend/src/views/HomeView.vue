<template>
  <div class="today-page">
    <AppStatePanel v-if="loading" title="讀取中" loading />
    <AppStatePanel
      v-else-if="loadError"
      title="今天的資料暫時無法載入"
      :message="loadError"
      action-label="重新整理"
      tone="error"
      @action="load"
    />

    <template v-else>
      <section v-if="!hasAccounts" class="onboarding">
        <h1>先建立一個帳戶</h1>
        <p>現金、銀行或信用卡都可以。記帳時餘額會跟著變動。</p>
        <router-link class="ink-button" to="/assets">建立帳戶</router-link>
      </section>

      <section v-else class="monthly-overview-card" aria-label="本月概況">
        <p class="label">{{ monthLabel }} · {{ hasBudget ? "還可以花" : "本月支出" }}</p>
        <p class="hero-number" :class="{ over: hasBudget && remaining < 0 }">
          <span class="currency">NT$</span>{{ hasBudget && remaining < 0 ? "−" : "" }}{{ formatAmount(hasBudget ? remaining : expense) }}
        </p>
        <template v-if="hasBudget">
          <div class="progress" role="progressbar" :aria-valuenow="usedPercent" aria-valuemin="0" aria-valuemax="100" aria-label="預算使用率">
            <span :style="{ width: `${Math.min(usedPercent, 100)}%` }"></span>
          </div>
          <p class="caption">預算 {{ formatAmount(budgetTotal) }} · 已用 {{ usedPercent }}%</p>
        </template>
        <p class="caption">收入 +{{ formatAmount(income) }} · 支出 −{{ formatAmount(expense) }}</p>
      </section>

      <router-link v-if="alert" class="alert-line" :to="alert.to">
        <span>{{ alert.text }}</span>
        <ArrowRight aria-hidden="true" />
      </router-link>

      <section v-if="hasAccounts" class="recent" aria-labelledby="recent-title">
        <div class="section-head">
          <h2 id="recent-title">最近</h2>
          <router-link v-if="recent.length" to="/transactions">全部明細</router-link>
        </div>
        <LedgerRow v-for="item in recent" :key="item.id" :transaction="item" show-date />
        <div v-if="!recent.length" class="empty">
          <p>還沒有紀錄。用一句話記下第一筆，例如「午餐 120」。</p>
          <router-link class="ink-button" to="/add">記一筆</router-link>
        </div>
      </section>
    </template>
  </div>
</template>

<script>
import { ArrowRight } from "@element-plus/icons-vue";
import apiClient from "@/api";
import AppStatePanel from "@/components/shared/AppStatePanel.vue";
import LedgerRow from "@/components/shared/LedgerRow.vue";
import { formatAmount, localDateKey } from "@/utils/money";

export default {
  name: "HomeView",
  components: { AppStatePanel, ArrowRight, LedgerRow },
  data() {
    return {
      month: localDateKey().slice(0, 7),
      loading: true,
      loadError: "",
      hasAccounts: false,
      budgets: [],
      income: 0,
      expense: 0,
      recent: [],
    };
  },
  computed: {
    monthLabel() {
      return `${Number(this.month.slice(5))} 月`;
    },
    budgeted() {
      return this.budgets.filter((row) => row.budget !== null && row.budget !== undefined);
    },
    hasBudget() {
      return this.budgeted.length > 0;
    },
    budgetTotal() {
      return this.budgeted.reduce((sum, row) => sum + Number(row.budget || 0), 0);
    },
    budgetSpent() {
      return this.budgeted.reduce((sum, row) => sum + Number(row.spent || 0), 0);
    },
    remaining() {
      return this.budgetTotal - this.budgetSpent;
    },
    usedPercent() {
      return this.budgetTotal > 0 ? Math.round((this.budgetSpent / this.budgetTotal) * 100) : 0;
    },
    alert() {
      // One line, and only when something needs action.
      const over = this.budgeted.filter((row) => Number(row.remaining) < 0);
      if (over.length === 1) {
        return { text: `${over[0].category}超出 NT$${formatAmount(-over[0].remaining)}`, to: "/budgets" };
      }
      if (over.length > 1) {
        const total = over.reduce((sum, row) => sum - Number(row.remaining), 0);
        return { text: `${over.length} 個類別超出預算，共 NT$${formatAmount(total)}`, to: "/budgets" };
      }
      return null;
    },
  },
  mounted() {
    this.load();
  },
  methods: {
    formatAmount,
    async load() {
      this.loading = true;
      this.loadError = "";
      try {
        const [assets, budgets, summary, recent] = await Promise.all([
          apiClient.get("/api/assets"),
          apiClient.get(`/api/budgets/summary/${this.month}`),
          apiClient.get("/api/reports/income_expense_summary", { params: { month: this.month } }),
          apiClient.get("/api/transactions", { params: { limit: 5 } }),
        ]);
        this.hasAccounts = Object.keys(assets.data?.data || {}).length > 0;
        this.budgets = budgets.data?.data || [];
        const [income, expense] = summary.data?.data?.datasets?.[0]?.data || [0, 0];
        this.income = Number(income || 0);
        this.expense = Number(expense || 0);
        this.recent = recent.data?.data || [];
      } catch (error) {
        this.loadError = error.response?.data?.message || "請確認網路連線後重試。";
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>

<style scoped>
.today-page {
  max-width: var(--compact-page-max-width);
  margin: 0 auto;
  padding: 24px 16px calc(var(--app-bottom-nav-height) + 24px);
  color: var(--text-color);
}

.label,
.caption {
  margin: 0;
  color: var(--light-text-color);
  font-size: 0.85rem;
}

.hero-number {
  margin: 6px 0 14px;
  font-size: 2.6rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
  line-height: 1.1;
}

.hero-number.over {
  color: var(--expense-color);
}

.hero-number .currency {
  margin-right: 4px;
  color: var(--light-text-color);
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0;
}

.progress {
  height: 6px;
  margin-bottom: 8px;
  overflow: hidden;
  border-radius: 3px;
  background: var(--secondary-color);
}

.progress span {
  display: block;
  height: 100%;
  background: var(--text-color);
}

.monthly-overview-card {
  display: grid;
  gap: 2px;
  padding-bottom: 20px;
}

.alert-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 20px;
  padding: 12px 14px;
  border: 1px solid var(--warning-color);
  border-radius: 10px;
  color: var(--warning-text);
  background: var(--warning-soft);
  text-decoration: none;
  font-weight: 600;
}

.alert-line svg {
  width: 16px;
  height: 16px;
}

.section-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border-color);
}

.section-head h2 {
  margin: 0;
  font-size: 1rem;
}

.section-head a {
  color: var(--light-text-color);
  font-size: 0.85rem;
  text-decoration: none;
}

.empty,
.onboarding {
  display: grid;
  justify-items: start;
  gap: 12px;
  padding: 20px 0;
}

.onboarding h1 {
  margin: 0;
  font-size: 1.5rem;
}

.empty p,
.onboarding p {
  margin: 0;
  color: var(--light-text-color);
}

.ink-button {
  display: inline-flex;
  align-items: center;
  min-height: 44px;
  padding: 0 18px;
  border-radius: 10px;
  color: var(--on-primary);
  background: var(--primary-color);
  text-decoration: none;
  font-weight: 700;
}
</style>
