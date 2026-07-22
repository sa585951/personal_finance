<template>
  <section class="tab-panel">
    <div class="snapshot-summary">
      <div>
        <span>最近資產快照</span>
        <strong>{{ latestSnapshot ? formatMoney(latestSnapshot.total_value) : "尚未建立" }}</strong>
      </div>
      <p>{{ latestSnapshot ? `${latestSnapshot.snapshot_date} 的手動估值，不是即時市值。` : "每月手動更新一次，就能保留當時的配置狀態。" }}</p>
    </div>

    <button class="panel-toggle" type="button" :disabled="!activeHoldings.length" @click="toggleForm">
      <Close v-if="showForm" /><CameraFilled v-else />{{ showForm ? "收合表單" : "記錄資產快照" }}
    </button>

    <form v-if="showForm" class="snapshot-form" @submit.prevent="saveSnapshot">
      <label class="date-field">
        <span>快照日期</span>
        <input v-model="form.snapshot_date" type="date" required />
      </label>
      <label class="note-field">
        <span>備註（選填）</span>
        <input v-model.trim="form.note" maxlength="500" placeholder="例如：七月底手動更新" />
      </label>
      <div class="value-grid">
        <label v-for="holding in activeHoldings" :key="holding.id">
          <span>{{ holding.name }}<small v-if="holding.symbol">{{ holding.symbol }}</small></span>
          <div class="money-input"><b>{{ portfolio.base_currency }}</b><input v-model.number="form.values[holding.id]" type="number" min="0" step="0.0001" required /></div>
        </label>
      </div>
      <div class="snapshot-total"><span>本次快照總值</span><strong>{{ formatMoney(draftTotal) }}</strong></div>
      <div class="form-actions">
        <button class="secondary-action" type="button" @click="resetForm">取消</button>
        <button class="primary-action" type="submit" :disabled="saving">{{ saving ? "儲存中" : existingDate ? "更新當日快照" : "儲存快照" }}</button>
      </div>
    </form>

    <div v-if="!snapshots.length" class="empty-state">尚無資產快照。</div>
    <div v-else class="snapshot-list">
      <article v-for="snapshot in snapshots" :key="snapshot.id" class="snapshot-card">
        <button class="snapshot-main" type="button" @click="editSnapshot(snapshot)">
          <span>{{ snapshot.snapshot_date }}</span>
          <strong>{{ formatMoney(snapshot.total_value) }}</strong>
          <small>{{ snapshot.items?.length || 0 }} 個標的<template v-if="snapshot.note"> · {{ snapshot.note }}</template></small>
        </button>
        <div class="snapshot-items">
          <div v-for="item in snapshot.items" :key="item.id">
            <span>{{ holdingName(item.holding_id) }}</span><strong>{{ formatMoney(item.value) }}</strong>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<script>
import apiClient from "@/api";
import { CameraFilled, Close } from "@element-plus/icons-vue";

export default {
  name: "SnapshotsTab",
  components: { CameraFilled, Close },
  props: { portfolio: { type: Object, required: true } },
  emits: ["changed"],
  data() { return { showForm: false, saving: false, form: this.emptyForm() }; },
  computed: {
    activeHoldings() { return (this.portfolio.holdings || []).filter((holding) => holding.is_active !== false); },
    snapshots() { return this.portfolio.snapshots || []; },
    latestSnapshot() { return this.snapshots[0] || null; },
    existingDate() { return this.snapshots.some((snapshot) => snapshot.snapshot_date === this.form.snapshot_date); },
    draftTotal() { return Object.values(this.form.values || {}).reduce((sum, value) => sum + Number(value || 0), 0); },
  },
  watch: {
    activeHoldings: { handler() { if (!this.showForm) this.form = this.emptyForm(); }, deep: true },
  },
  methods: {
    emptyForm() {
      const values = {};
      (this.portfolio?.holdings || []).filter((holding) => holding.is_active !== false).forEach((holding) => { values[holding.id] = null; });
      return { snapshot_date: new Date().toISOString().slice(0, 10), note: "", values };
    },
    toggleForm() { this.showForm ? this.resetForm() : (this.showForm = true); },
    resetForm() { this.form = this.emptyForm(); this.showForm = false; },
    formatMoney(amount) { return `${this.portfolio.base_currency} ${Number(amount || 0).toLocaleString("zh-TW", { maximumFractionDigits: 4 })}`; },
    holdingName(id) { return (this.portfolio.holdings || []).find((holding) => holding.id === id)?.name || "已停用標的"; },
    editSnapshot(snapshot) {
      const values = {};
      this.activeHoldings.forEach((holding) => { values[holding.id] = snapshot.items?.find((item) => item.holding_id === holding.id)?.value ?? null; });
      this.form = { snapshot_date: snapshot.snapshot_date, note: snapshot.note || "", values };
      this.showForm = true;
      this.$nextTick(() => document.querySelector(".snapshot-form")?.scrollIntoView({ behavior: "smooth", block: "start" }));
    },
    async saveSnapshot() {
      this.saving = true;
      const payload = { snapshot_date: this.form.snapshot_date, note: this.form.note || null, items: this.activeHoldings.map((holding) => ({ holding_id: holding.id, value: Number(this.form.values[holding.id]) })) };
      try { await apiClient.post(`/api/portfolios/${this.portfolio.id}/snapshots`, payload); this.resetForm(); this.$emit("changed"); }
      catch (error) { this.$swal.fire("無法儲存", error.response?.data?.message || "請確認所有標的都有填寫估值。", "error"); }
      finally { this.saving = false; }
    },
  },
};
</script>

<style scoped>
.tab-panel { display: grid; gap: 14px; }.snapshot-summary { padding: 16px; border: 1px solid #fde68a; border-radius: 10px; background: #fffbeb; }.snapshot-summary > div { display: flex; justify-content: space-between; gap: 12px; }.snapshot-summary span { color: #475569; font-weight: 700; }.snapshot-summary strong { color: #a16207; font-size: 1.3rem; }.snapshot-summary p { margin: 5px 0 0; color: #64748b; font-size: .86rem; }
.panel-toggle { justify-self: start; min-height: 40px; display: inline-flex; align-items: center; gap: 7px; padding: 0 12px; color: #0f766e; background: #fff; border: 1px solid #99f6e4; }.panel-toggle svg { width: 17px; height: 17px; }
.snapshot-form { display: grid; grid-template-columns: 180px minmax(0, 1fr); gap: 12px; padding: 16px; border: 1px solid #dbe4ee; border-radius: 10px; background: #f8fafc; }.snapshot-form label { display: grid; gap: 6px; color: #475569; font-weight: 700; }.snapshot-form input { width: 100%; min-height: 44px; padding: 0 12px; border: 1px solid #cbd5e1; border-radius: 8px; background: #fff; font: inherit; }.snapshot-form input:focus { outline: 3px solid #ccfbf1; border-color: #0f766e; }
.value-grid { grid-column: 1 / -1; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; padding-top: 12px; border-top: 1px solid #e2e8f0; }.value-grid label > span { display: flex; justify-content: space-between; gap: 8px; }.value-grid small { color: #0f766e; }.money-input { display: grid; grid-template-columns: auto minmax(0, 1fr); align-items: center; overflow: hidden; border: 1px solid #cbd5e1; border-radius: 8px; background: #fff; }.money-input b { padding: 0 10px; color: #64748b; font-size: .78rem; }.money-input input { border: 0; border-left: 1px solid #e2e8f0; border-radius: 0; }
.snapshot-total { grid-column: 1 / -1; display: flex; justify-content: space-between; gap: 12px; padding: 12px; color: #134e4a; background: #f0fdfa; border-radius: 8px; }.form-actions { grid-column: 1 / -1; display: flex; justify-content: flex-end; gap: 8px; }.primary-action, .secondary-action { min-height: 38px; padding: 0 12px; border-radius: 8px; }.primary-action { color: #fff; background: #0f766e; }.secondary-action { color: #334155; background: #fff; border: 1px solid #cbd5e1; }
.snapshot-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }.snapshot-card { overflow: hidden; border: 1px solid #dbe4ee; border-radius: 10px; background: #fff; }.snapshot-main { width: 100%; display: grid; gap: 2px; padding: 14px; color: #1f2933; background: #fff; text-align: left; }.snapshot-main span, .snapshot-main small { color: #64748b; }.snapshot-main strong { font-size: 1.2rem; }.snapshot-items { display: grid; gap: 6px; padding: 12px 14px; border-top: 1px solid #e2e8f0; background: #f8fafc; }.snapshot-items div { display: flex; justify-content: space-between; gap: 10px; font-size: .84rem; }.snapshot-items span { color: #64748b; }.empty-state { padding: 28px 16px; color: #64748b; text-align: center; border: 1px dashed #cbd5e1; border-radius: 10px; background: #f8fafc; }
@media (max-width: 640px) { .snapshot-form, .value-grid, .snapshot-list { grid-template-columns: 1fr; }.date-field, .note-field, .value-grid, .snapshot-total, .form-actions { grid-column: 1; } }
</style>
