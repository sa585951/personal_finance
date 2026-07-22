<template>
  <div class="allocation-screen">
    <header class="page-header">
      <div>
        <p class="eyebrow">Asset Allocation</p>
        <h1>資產配置</h1>
        <p class="page-description">記錄自己的投資策略、投入成本與手動估值，不連接券商或即時行情。</p>
      </div>
      <button class="primary-action" type="button" @click="toggleForm">
        <Close v-if="showForm" />
        <Plus v-else />
        <span>{{ showForm ? "收合" : "新增組合" }}</span>
      </button>
    </header>

    <section v-if="showForm" class="form-panel">
      <div class="section-heading">
        <div>
          <h2>{{ editingPortfolio ? "編輯投資組合" : "新增投資組合" }}</h2>
          <p>每個投資組合只使用一種基準幣別。</p>
        </div>
      </div>
      <form class="portfolio-form" @submit.prevent="savePortfolio">
        <label>
          <span>組合名稱</span>
          <input v-model.trim="form.name" maxlength="100" placeholder="例如：長期 ETF" required />
        </label>
        <label>
          <span>基準幣別</span>
          <select v-model="form.base_currency" :disabled="Boolean(editingPortfolio)">
            <option v-for="currency in currencies" :key="currency" :value="currency">
              {{ currency }}
            </option>
          </select>
        </label>
        <div class="form-actions">
          <button v-if="editingPortfolio" class="secondary-action" type="button" @click="resetForm">
            取消編輯
          </button>
          <button class="primary-action" type="submit" :disabled="saving">
            {{ saving ? "儲存中" : editingPortfolio ? "儲存變更" : "建立組合" }}
          </button>
        </div>
      </form>
    </section>

    <div v-if="loading" class="state-panel">正在載入投資組合...</div>
    <div v-else-if="error" class="state-panel error-state">{{ error }}</div>

    <section v-else-if="portfolios.length" class="portfolio-section">
      <div class="section-heading">
        <div>
          <h2>我的投資組合</h2>
          <p>{{ portfolios.length }} 個組合，依基準幣別分開管理</p>
        </div>
      </div>
      <div class="portfolio-grid">
        <article v-for="portfolio in portfolios" :key="portfolio.id" class="portfolio-card">
          <router-link class="portfolio-main" :to="`/allocation/${portfolio.id}`">
            <div class="portfolio-symbol" aria-hidden="true"><TrendCharts /></div>
            <div>
              <span>{{ portfolio.base_currency }}</span>
              <h3>{{ portfolio.name }}</h3>
              <p>查看配置標的、成本、快照與投入試算</p>
            </div>
            <ArrowRight class="portfolio-arrow" aria-hidden="true" />
          </router-link>
          <div class="portfolio-actions">
            <span class="status-badge" :class="{ inactive: !portfolio.is_active }">
              {{ portfolio.is_active ? "使用中" : "已停用" }}
            </span>
            <button type="button" title="編輯投資組合" @click="startEdit(portfolio)"><EditPen /></button>
            <button class="danger-icon" type="button" title="刪除投資組合" @click="deletePortfolio(portfolio)"><Delete /></button>
          </div>
        </article>
      </div>
    </section>

    <section v-else class="empty-panel">
      <div class="empty-icon" aria-hidden="true"><TrendCharts /></div>
      <h2>建立第一個投資組合</h2>
      <p>先決定基準幣別，再加入同幣別投資帳戶中的配置標的。</p>
      <button class="primary-action" type="button" @click="showForm = true"><Plus />新增投資組合</button>
    </section>
  </div>
</template>

<script>
import apiClient from "@/api";
import { ArrowRight, Close, Delete, EditPen, Plus, TrendCharts } from "@element-plus/icons-vue";

export default {
  name: "AllocationOverview",
  components: { ArrowRight, Close, Delete, EditPen, Plus, TrendCharts },
  data() {
    return {
      portfolios: [],
      loading: true,
      saving: false,
      error: "",
      showForm: false,
      editingPortfolio: null,
      currencies: ["TWD", "USD", "JPY", "EUR", "KRW"],
      form: { name: "", base_currency: "TWD" },
    };
  },
  created() {
    this.fetchPortfolios();
  },
  methods: {
    async fetchPortfolios() {
      this.loading = true;
      this.error = "";
      try {
        const response = await apiClient.get("/api/portfolios");
        this.portfolios = response.data.data || [];
      } catch (error) {
        this.error = error.response?.data?.message || "無法載入投資組合。";
      } finally {
        this.loading = false;
      }
    },
    toggleForm() {
      if (this.showForm) this.resetForm();
      else this.showForm = true;
    },
    startEdit(portfolio) {
      this.editingPortfolio = portfolio;
      this.form = { name: portfolio.name, base_currency: portfolio.base_currency };
      this.showForm = true;
      this.$nextTick(() => document.querySelector(".form-panel")?.scrollIntoView({ behavior: "smooth" }));
    },
    resetForm() {
      this.editingPortfolio = null;
      this.form = { name: "", base_currency: "TWD" };
      this.showForm = false;
    },
    async savePortfolio() {
      this.saving = true;
      try {
        if (this.editingPortfolio) {
          await apiClient.patch(`/api/portfolios/${this.editingPortfolio.id}`, { name: this.form.name });
        } else {
          await apiClient.post("/api/portfolios", this.form);
        }
        await this.fetchPortfolios();
        this.resetForm();
      } catch (error) {
        this.$swal.fire("無法儲存", error.response?.data?.message || "請稍後再試。", "error");
      } finally {
        this.saving = false;
      }
    },
    async deletePortfolio(portfolio) {
      const result = await this.$swal.fire({
        title: "刪除投資組合？",
        text: `「${portfolio.name}」會進入 30 天清理期，歷史資料不會立即硬刪除。`,
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "刪除",
        cancelButtonText: "取消",
      });
      if (!result.isConfirmed) return;
      try {
        await apiClient.delete(`/api/portfolios/${portfolio.id}`);
        await this.fetchPortfolios();
      } catch (error) {
        this.$swal.fire("刪除失敗", error.response?.data?.message || "請稍後再試。", "error");
      }
    },
  },
};
</script>

<style scoped>
.allocation-screen { max-width: var(--page-max-width); min-height: calc(100vh - 80px); margin: 0 auto; padding: 28px 18px calc(var(--app-bottom-nav-height) + 28px); color: var(--text-color); }
.page-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; margin-bottom: 20px; }
.eyebrow { margin: 0 0 4px; color: #0f766e; font-size: .78rem; font-weight: 800; text-transform: uppercase; }
h1 { margin: 0; font-size: 2rem; letter-spacing: 0; }
.page-description { max-width: 560px; margin: 8px 0 0; color: #64748b; line-height: 1.55; }
.primary-action, .secondary-action { min-height: 42px; display: inline-flex; align-items: center; justify-content: center; gap: 7px; padding: 0 14px; border-radius: 8px; }
.primary-action { color: #fff; background: #0f766e; }
.secondary-action { color: #334155; background: #fff; border: 1px solid #cbd5e1; }
.primary-action svg, .secondary-action svg { width: 18px; height: 18px; }
.form-panel, .state-panel, .empty-panel { padding: 20px; border: 1px solid #dbe4ee; border-radius: 10px; background: #fff; }
.form-panel { margin-bottom: 20px; }
.section-heading { display: flex; justify-content: space-between; gap: 12px; margin-bottom: 14px; }
.section-heading h2 { margin: 0; font-size: 1.15rem; }
.section-heading p { margin: 4px 0 0; color: #64748b; }
.portfolio-form { display: grid; grid-template-columns: minmax(0, 1fr) 180px; gap: 14px; }
.portfolio-form label { display: grid; gap: 6px; color: #475569; font-weight: 700; }
.portfolio-form input, .portfolio-form select { width: 100%; min-height: 44px; padding: 0 12px; border: 1px solid #cbd5e1; border-radius: 8px; background: #fff; font: inherit; }
.portfolio-form input:focus, .portfolio-form select:focus { outline: 3px solid #ccfbf1; border-color: #0f766e; }
.form-actions { grid-column: 1 / -1; display: flex; justify-content: flex-end; gap: 8px; }
.state-panel { color: #64748b; }
.error-state { color: #b91c1c; border-color: #fecaca; background: #fef2f2; }
.portfolio-section { padding: 20px; border: 1px solid #dbe4ee; border-radius: 10px; background: #fff; }
.portfolio-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.portfolio-card { min-width: 0; overflow: hidden; border: 1px solid #dbe4ee; border-radius: 10px; background: #fff; }
.portfolio-main { min-height: 128px; display: grid; grid-template-columns: 42px minmax(0, 1fr) 20px; align-items: center; gap: 12px; padding: 16px; color: #1f2933; text-decoration: none; background: #f8fafc; }
.portfolio-main:hover { background: #f0fdfa; }
.portfolio-symbol, .empty-icon { display: grid; place-items: center; color: #0f766e; background: #ccfbf1; border-radius: 8px; }
.portfolio-symbol { width: 42px; height: 42px; }
.portfolio-symbol svg, .portfolio-arrow { width: 20px; height: 20px; }
.portfolio-main span { color: #0f766e; font-size: .75rem; font-weight: 800; }
.portfolio-main h3 { margin: 2px 0; font-size: 1.08rem; }
.portfolio-main p { margin: 0; color: #64748b; font-size: .86rem; line-height: 1.4; }
.portfolio-arrow { color: #64748b; }
.portfolio-actions { min-height: 46px; display: flex; align-items: center; justify-content: flex-end; gap: 6px; padding: 6px 10px; border-top: 1px solid #e2e8f0; }
.portfolio-actions button { width: 34px; height: 34px; display: grid; place-items: center; padding: 0; color: #475569; background: transparent; border: 1px solid transparent; }
.portfolio-actions button:hover { border-color: #cbd5e1; background: #f8fafc; }
.portfolio-actions button svg { width: 17px; height: 17px; }
.portfolio-actions .danger-icon { color: #b91c1c; }
.status-badge { margin-right: auto; padding: 3px 8px; color: #0f766e; background: #ccfbf1; border-radius: 999px; font-size: .75rem; font-weight: 800; }
.status-badge.inactive { color: #64748b; background: #e2e8f0; }
.empty-panel { display: grid; justify-items: center; gap: 8px; padding: 42px 20px; text-align: center; }
.empty-icon { width: 52px; height: 52px; }
.empty-icon svg { width: 25px; height: 25px; }
.empty-panel h2 { margin: 4px 0 0; }
.empty-panel p { max-width: 440px; margin: 0 0 10px; color: #64748b; }
@media (max-width: 640px) { .allocation-screen { padding: 24px 14px calc(var(--app-bottom-nav-height) + 22px); } .page-header { align-items: stretch; flex-direction: column; } .page-header .primary-action { align-self: flex-start; } .portfolio-form, .portfolio-grid { grid-template-columns: 1fr; } .portfolio-form select { width: 100%; } }
</style>
