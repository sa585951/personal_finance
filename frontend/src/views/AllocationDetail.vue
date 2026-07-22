<template>
  <div class="allocation-detail-screen">
    <router-link class="back-link" to="/allocation"><Back />返回資產配置</router-link>

    <div v-if="loading" class="state-panel">正在載入投資組合...</div>
    <div v-else-if="error" class="state-panel error-state">{{ error }}</div>

    <template v-else-if="portfolio">
      <header class="detail-header">
        <div>
          <p class="eyebrow">{{ portfolio.base_currency }} Portfolio</p>
          <h1>{{ portfolio.name }}</h1>
          <p>手動管理策略與資產快照，不連接券商或即時行情。</p>
        </div>
        <span class="status-badge" :class="{ inactive: !portfolio.is_active }">{{ portfolio.is_active ? "使用中" : "已停用" }}</span>
      </header>

      <section class="summary-grid" aria-label="投資組合摘要">
        <article>
          <span>累計投入成本</span>
          <strong>{{ formatMoney(recordedCost) }}</strong>
          <small>{{ costEntryCount }} 筆投入紀錄</small>
        </article>
        <article>
          <span>最近資產快照</span>
          <strong>{{ latestSnapshot ? formatMoney(latestSnapshot.total_value) : "尚未建立" }}</strong>
          <small>{{ latestSnapshot?.snapshot_date || "手動更新估值後顯示" }}</small>
        </article>
        <article>
          <span>目標配置</span>
          <strong :class="{ warning: targetTotal !== 100 }">{{ targetTotal }}%</strong>
          <small>{{ activeHoldings.length }} 個 active 標的</small>
        </article>
      </section>

      <nav class="detail-tabs" aria-label="資產配置功能">
        <button v-for="tab in tabs" :key="tab.key" type="button" :class="{ active: activeTab === tab.key }" @click="activeTab = tab.key">
          <component :is="tab.icon" /><span>{{ tab.label }}</span>
        </button>
      </nav>

      <main class="detail-content">
        <HoldingsTab v-if="activeTab === 'holdings'" :portfolio="portfolio" :accounts="accounts" @changed="refreshPortfolio" />
        <CostsTab v-else-if="activeTab === 'costs'" :portfolio="portfolio" :transfers="transfers" @changed="refreshPortfolio" />
        <SnapshotsTab v-else-if="activeTab === 'snapshots'" :portfolio="portfolio" @changed="refreshPortfolio" />
        <PreviewTab v-else :portfolio="portfolio" />
      </main>
    </template>
  </div>
</template>

<script>
import apiClient from "@/api";
import { Back, Coin, DataAnalysis, List, PictureFilled } from "@element-plus/icons-vue";
import CostsTab from "@/components/allocation/CostsTab.vue";
import HoldingsTab from "@/components/allocation/HoldingsTab.vue";
import PreviewTab from "@/components/allocation/PreviewTab.vue";
import SnapshotsTab from "@/components/allocation/SnapshotsTab.vue";

export default {
  name: "AllocationDetail",
  components: { Back, Coin, CostsTab, DataAnalysis, HoldingsTab, List, PictureFilled, PreviewTab, SnapshotsTab },
  data() {
    return {
      portfolio: null,
      accounts: [],
      transfers: [],
      loading: true,
      error: "",
      activeTab: "holdings",
      tabs: [
        { key: "holdings", label: "配置標的", icon: "List" },
        { key: "costs", label: "投入成本", icon: "Coin" },
        { key: "snapshots", label: "資產快照", icon: "PictureFilled" },
        { key: "preview", label: "投入試算", icon: "DataAnalysis" },
      ],
    };
  },
  computed: {
    activeHoldings() { return (this.portfolio?.holdings || []).filter((holding) => holding.is_active !== false); },
    recordedCost() { return (this.portfolio?.holdings || []).reduce((sum, holding) => sum + Number(holding.recorded_cost || 0), 0); },
    costEntryCount() { return (this.portfolio?.holdings || []).reduce((sum, holding) => sum + (holding.cost_entries?.length || 0), 0); },
    latestSnapshot() { return this.portfolio?.snapshots?.[0] || null; },
    targetTotal() { return Math.round(this.activeHoldings.reduce((sum, holding) => sum + Number(holding.target_weight || 0) * 100, 0) * 100) / 100; },
  },
  created() { this.fetchPage(); },
  methods: {
    async fetchPage() {
      this.loading = true; this.error = "";
      try {
        const [portfolioResponse, assetsResponse, transfersResponse] = await Promise.all([
          apiClient.get(`/api/portfolios/${this.$route.params.portfolioId}`),
          apiClient.get("/api/assets"),
          apiClient.get("/api/transfers/recent?limit=100"),
        ]);
        this.portfolio = portfolioResponse.data.data;
        this.accounts = Object.values(assetsResponse.data.data || {});
        this.transfers = transfersResponse.data.data || [];
      } catch (error) { this.error = error.response?.data?.message || "無法載入投資組合。"; }
      finally { this.loading = false; }
    },
    async refreshPortfolio() {
      try { const response = await apiClient.get(`/api/portfolios/${this.$route.params.portfolioId}`); this.portfolio = response.data.data; }
      catch (error) { this.$swal.fire("更新失敗", error.response?.data?.message || "無法重新載入投資組合。", "error"); }
    },
    formatMoney(amount) { return `${this.portfolio?.base_currency || "TWD"} ${Number(amount || 0).toLocaleString("zh-TW", { maximumFractionDigits: 4 })}`; },
  },
};
</script>

<style scoped>
.allocation-detail-screen { max-width: var(--page-max-width); min-height: calc(100vh - 80px); margin: 0 auto; padding: 24px 18px calc(var(--app-bottom-nav-height) + 28px); color: var(--text-color); }.back-link { display: inline-flex; align-items: center; gap: 6px; margin-bottom: 18px; color: #0f766e; text-decoration: none; font-weight: 800; }.back-link svg { width: 18px; height: 18px; }
.detail-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 16px; }.eyebrow { margin: 0 0 4px; color: #0f766e; font-size: .78rem; font-weight: 800; text-transform: uppercase; }.detail-header h1 { margin: 0; font-size: 2rem; }.detail-header p { margin: 6px 0 0; color: #64748b; }.status-badge { flex-shrink: 0; padding: 5px 10px; color: #0f766e; background: #ccfbf1; border-radius: 999px; font-size: .78rem; font-weight: 800; }.status-badge.inactive { color: #64748b; background: #e2e8f0; }
.summary-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin-bottom: 16px; }.summary-grid article { min-width: 0; display: grid; gap: 4px; padding: 16px; border: 1px solid #dbe4ee; border-radius: 10px; background: #fff; }.summary-grid span, .summary-grid small { color: #64748b; }.summary-grid strong { overflow-wrap: anywhere; font-size: 1.15rem; }.summary-grid strong.warning { color: #b45309; }
.detail-tabs { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 4px; padding: 4px; border: 1px solid #dbe4ee; border-radius: 10px; background: #eaf0f4; }.detail-tabs button { min-width: 0; min-height: 44px; display: inline-flex; align-items: center; justify-content: center; gap: 7px; padding: 0 10px; color: #64748b; background: transparent; border-radius: 7px; }.detail-tabs button.active { color: #0f766e; background: #fff; box-shadow: 0 1px 3px rgba(15, 23, 42, .1); }.detail-tabs svg { width: 17px; height: 17px; }.detail-content { margin-top: 14px; padding: 18px; border: 1px solid #dbe4ee; border-radius: 10px; background: #fff; }.state-panel { padding: 20px; border: 1px solid #dbe4ee; border-radius: 10px; background: #fff; color: #64748b; }.error-state { color: #b91c1c; border-color: #fecaca; background: #fef2f2; }
@media (max-width: 640px) { .allocation-detail-screen { padding: 20px 14px calc(var(--app-bottom-nav-height) + 22px); }.detail-header { flex-direction: column; }.summary-grid { grid-template-columns: 1fr; }.detail-tabs { overflow-x: auto; grid-template-columns: repeat(4, minmax(92px, 1fr)); }.detail-tabs button { flex-direction: column; gap: 2px; min-height: 54px; font-size: .78rem; }.detail-content { padding: 14px; } }
</style>
