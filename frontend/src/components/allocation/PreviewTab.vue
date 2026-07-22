<template>
  <section class="tab-panel">
    <div class="preview-intro">
      <div class="intro-icon" aria-hidden="true"><DataAnalysis /></div>
      <div>
        <h3>新增投入試算</h3>
        <p>依你設定的目標比例計算下一筆資金如何分配；結果不是買賣建議，也不會建立交易。</p>
      </div>
    </div>

    <form class="preview-form" @submit.prevent="runPreview">
      <label>
        <span>預計新增投入</span>
        <div class="money-input"><b>{{ portfolio.base_currency }}</b><input v-model.number="amount" type="number" min="0.0001" step="0.0001" placeholder="20000" required /></div>
      </label>
      <button class="primary-action" type="submit" :disabled="loading || !canPreview">{{ loading ? "計算中" : "開始試算" }}</button>
    </form>

    <div v-if="!canPreview" class="notice-state">
      active 配置標的的目標比例需合計為 100%，目前為 {{ targetTotal }}%。
    </div>

    <section v-if="preview" class="preview-result">
      <div class="result-header">
        <div><span>試算依據</span><strong>{{ basisLabel }}</strong></div>
        <div><span>投入金額</span><strong>{{ formatMoney(preview.new_amount) }}</strong></div>
      </div>
      <p class="basis-note">{{ preview.as_of ? `資料日期 ${preview.as_of}` : "目前尚無快照，使用累計投入成本作為配置基準。" }}</p>

      <div class="allocation-bar" aria-label="建議新增投入比例">
        <div v-for="(item, index) in preview.allocations" :key="item.holding_id" :style="{ width: recommendationPercent(item) + '%', backgroundColor: colors[index % colors.length] }"></div>
      </div>

      <div class="result-list">
        <article v-for="(item, index) in preview.allocations" :key="item.holding_id">
          <span class="swatch" :style="{ backgroundColor: colors[index % colors.length] }"></span>
          <div><strong>{{ item.name }}</strong><small>目標 {{ percent(item.target_weight) }} · 目前 {{ formatMoney(item.current_amount) }}</small></div>
          <div class="recommendation"><span>本次投入</span><strong>{{ formatMoney(item.recommended_amount) }}</strong></div>
        </article>
      </div>
    </section>
  </section>
</template>

<script>
import apiClient from "@/api";
import { DataAnalysis } from "@element-plus/icons-vue";

export default {
  name: "PreviewTab",
  components: { DataAnalysis },
  props: { portfolio: { type: Object, required: true } },
  data() { return { amount: null, loading: false, preview: null, colors: ["#0f766e", "#2563eb", "#ca8a04", "#7c3aed", "#dc2626", "#64748b"] }; },
  computed: {
    activeHoldings() { return (this.portfolio.holdings || []).filter((holding) => holding.is_active !== false); },
    targetTotal() { return Math.round(this.activeHoldings.reduce((sum, holding) => sum + Number(holding.target_weight || 0) * 100, 0) * 100) / 100; },
    canPreview() { return this.activeHoldings.length > 0 && this.targetTotal === 100; },
    basisLabel() { return this.preview?.basis === "snapshot" ? "最近資產快照" : "累計投入成本"; },
  },
  watch: { portfolio: { handler() { this.preview = null; }, deep: true } },
  methods: {
    formatMoney(amount) { return `${this.portfolio.base_currency} ${Number(amount || 0).toLocaleString("zh-TW", { maximumFractionDigits: 4 })}`; },
    percent(weight) { return `${(Number(weight || 0) * 100).toFixed(2).replace(/\.00$/, "")}%`; },
    recommendationPercent(item) { const total = Number(this.preview?.new_amount || 0); return total > 0 ? (Number(item.recommended_amount || 0) / total) * 100 : 0; },
    async runPreview() {
      this.loading = true;
      try { const response = await apiClient.post(`/api/portfolios/${this.portfolio.id}/allocation-preview`, { amount: this.amount }); this.preview = response.data.data; }
      catch (error) { this.preview = null; this.$swal.fire("無法試算", error.response?.data?.message || "請稍後再試。", "error"); }
      finally { this.loading = false; }
    },
  },
};
</script>

<style scoped>
.tab-panel { display: grid; gap: 14px; }.preview-intro { display: grid; grid-template-columns: 46px minmax(0, 1fr); align-items: center; gap: 12px; padding: 16px; border: 1px solid #99f6e4; border-radius: 10px; background: #f0fdfa; }.intro-icon { width: 46px; height: 46px; display: grid; place-items: center; color: #0f766e; background: #ccfbf1; border-radius: 8px; }.intro-icon svg { width: 22px; height: 22px; }.preview-intro h3 { margin: 0; }.preview-intro p { margin: 3px 0 0; color: #475569; font-size: .88rem; line-height: 1.5; }
.preview-form { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: end; gap: 12px; padding: 16px; border: 1px solid #dbe4ee; border-radius: 10px; background: #fff; }.preview-form label { display: grid; gap: 6px; color: #475569; font-weight: 700; }.money-input { display: grid; grid-template-columns: auto minmax(0, 1fr); align-items: center; overflow: hidden; border: 1px solid #cbd5e1; border-radius: 8px; }.money-input b { padding: 0 12px; color: #64748b; font-size: .82rem; }.money-input input { width: 100%; min-height: 44px; padding: 0 12px; border: 0; border-left: 1px solid #e2e8f0; font: inherit; }.money-input input:focus { outline: 3px solid #ccfbf1; }.primary-action { min-height: 44px; padding: 0 16px; color: #fff; background: #0f766e; border-radius: 8px; }.notice-state { padding: 12px 14px; color: #92400e; border: 1px solid #fde68a; border-radius: 8px; background: #fffbeb; }
.preview-result { padding: 18px; border: 1px solid #dbe4ee; border-radius: 10px; background: #fff; }.result-header { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }.result-header div { display: grid; gap: 2px; padding: 12px; background: #f8fafc; border-radius: 8px; }.result-header span { color: #64748b; font-size: .82rem; }.result-header strong { color: #1f2933; font-size: 1.08rem; }.basis-note { margin: 10px 0 14px; color: #64748b; font-size: .84rem; }.allocation-bar { display: flex; height: 12px; overflow: hidden; border-radius: 999px; background: #e2e8f0; }.allocation-bar div { min-width: 3px; }
.result-list { display: grid; gap: 8px; margin-top: 14px; }.result-list article { display: grid; grid-template-columns: 10px minmax(0, 1fr) auto; align-items: center; gap: 10px; padding: 10px 0; border-bottom: 1px solid #e2e8f0; }.result-list article:last-child { border-bottom: 0; }.swatch { width: 10px; height: 10px; border-radius: 2px; }.result-list article > div { min-width: 0; display: grid; gap: 2px; }.result-list small { color: #64748b; }.recommendation { text-align: right; }.recommendation span { color: #64748b; font-size: .75rem; }.recommendation strong { color: #0f766e; white-space: nowrap; }
@media (max-width: 640px) { .preview-form, .result-header { grid-template-columns: 1fr; }.result-list article { grid-template-columns: 10px minmax(0, 1fr); }.recommendation { grid-column: 2; text-align: left; } }
</style>
