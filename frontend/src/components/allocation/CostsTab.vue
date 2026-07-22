<template>
  <section class="tab-panel">
    <div class="cost-summary">
      <div><span>累計投入成本</span><strong>{{ formatMoney(totalCost) }}</strong></div>
      <p>成本用來記錄實際投入，不會覆蓋帳戶餘額或手動資產快照。</p>
    </div>

    <button class="panel-toggle" type="button" :disabled="!activeHoldings.length" @click="toggleForm">
      <Close v-if="showForm" /><Plus v-else />{{ showForm ? "收合表單" : "新增投入成本" }}
    </button>

    <form v-if="showForm" class="entry-form" @submit.prevent="saveEntry">
      <label>
        <span>配置標的</span>
        <select v-model="form.holding_id" required :disabled="Boolean(editingEntry)">
          <option disabled value="">請選擇標的</option>
          <option v-for="holding in activeHoldings" :key="holding.id" :value="holding.id">{{ holding.name }}</option>
        </select>
      </label>
      <label>
        <span>紀錄方式</span>
        <select v-model="form.entry_type" required>
          <option value="manual_adjustment">手動調整</option>
          <option value="transfer">連結帳戶轉帳</option>
        </select>
      </label>
      <label v-if="form.entry_type === 'transfer'" class="wide-field">
        <span>轉入投資帳戶的紀錄</span>
        <select v-model="form.source_transfer_id" required>
          <option disabled value="">請選擇轉帳</option>
          <option v-for="transfer in eligibleTransfers" :key="transfer.id" :value="transfer.id">
            {{ transfer.transfer_date }} · {{ transfer.source_name }} → {{ transfer.target_name }} · {{ formatMoney(transfer.target_amount) }}
          </option>
        </select>
      </label>
      <label>
        <span>投入金額</span>
        <input v-model.number="form.amount" type="number" min="0.0001" step="0.0001" required />
      </label>
      <label>
        <span>投入日期</span>
        <input v-model="form.occurred_on" type="date" required />
      </label>
      <label class="wide-field">
        <span>備註（選填）</span>
        <input v-model.trim="form.note" maxlength="500" placeholder="例如：七月定期定額" />
      </label>
      <div class="form-actions wide-field">
        <button v-if="editingEntry" class="secondary-action" type="button" @click="resetForm">取消編輯</button>
        <button class="primary-action" type="submit" :disabled="saving">{{ saving ? "儲存中" : editingEntry ? "儲存變更" : "新增成本" }}</button>
      </div>
      <p v-if="form.entry_type === 'transfer' && form.holding_id && !eligibleTransfers.length" class="form-hint wide-field">
        最近轉帳中沒有符合此標的投資帳戶與幣別的紀錄。
      </p>
    </form>

    <div v-if="!entries.length" class="empty-state">尚無投入成本紀錄。</div>
    <div v-else class="cost-list">
      <article v-for="entry in entries" :key="entry.id" class="cost-row">
        <div class="cost-date"><strong>{{ day(entry.occurred_on) }}</strong><span>{{ month(entry.occurred_on) }}</span></div>
        <div class="cost-copy">
          <strong>{{ entry.holdingName }}</strong>
          <span>{{ entry.entry_type === "transfer" ? "帳戶轉帳" : "手動調整" }}<template v-if="entry.note"> · {{ entry.note }}</template></span>
        </div>
        <strong class="cost-amount">{{ formatMoney(entry.amount) }}</strong>
        <div class="row-actions">
          <button type="button" title="編輯成本" @click="startEdit(entry)"><EditPen /></button>
          <button class="danger-icon" type="button" title="刪除成本" @click="deleteEntry(entry)"><Delete /></button>
        </div>
      </article>
    </div>
  </section>
</template>

<script>
import apiClient from "@/api";
import { Close, Delete, EditPen, Plus } from "@element-plus/icons-vue";

export default {
  name: "CostsTab",
  components: { Close, Delete, EditPen, Plus },
  props: {
    portfolio: { type: Object, required: true },
    transfers: { type: Array, default: () => [] },
  },
  emits: ["changed"],
  data() { return { showForm: false, saving: false, editingEntry: null, form: this.emptyForm() }; },
  computed: {
    activeHoldings() { return (this.portfolio.holdings || []).filter((holding) => holding.is_active !== false); },
    entries() {
      return (this.portfolio.holdings || []).flatMap((holding) => (holding.cost_entries || []).map((entry) => ({ ...entry, holdingName: holding.name, accountId: holding.account_id })))
        .sort((a, b) => String(b.occurred_on).localeCompare(String(a.occurred_on)));
    },
    totalCost() { return this.entries.reduce((sum, entry) => sum + Number(entry.amount || 0), 0); },
    selectedHolding() { return this.activeHoldings.find((holding) => holding.id === this.form.holding_id); },
    eligibleTransfers() {
      if (!this.selectedHolding) return [];
      return this.transfers.filter((transfer) => transfer.target_account_id === this.selectedHolding.account_id && transfer.target_currency === this.portfolio.base_currency);
    },
  },
  methods: {
    today() { return new Date().toISOString().slice(0, 10); },
    emptyForm() { return { holding_id: "", entry_type: "manual_adjustment", source_transfer_id: "", amount: null, occurred_on: new Date().toISOString().slice(0, 10), note: "" }; },
    toggleForm() { this.showForm ? this.resetForm() : (this.showForm = true); },
    resetForm() { this.form = this.emptyForm(); this.editingEntry = null; this.showForm = false; },
    formatMoney(amount) { return `${this.portfolio.base_currency} ${Number(amount || 0).toLocaleString("zh-TW", { maximumFractionDigits: 4 })}`; },
    day(value) { return String(value || "").slice(8, 10); },
    month(value) { return String(value || "").slice(0, 7); },
    startEdit(entry) {
      this.editingEntry = entry;
      this.form = { holding_id: entry.holding_id, entry_type: entry.entry_type, source_transfer_id: entry.source_transfer_id || "", amount: Number(entry.amount), occurred_on: entry.occurred_on, note: entry.note || "" };
      this.showForm = true;
      this.$nextTick(() => document.querySelector(".entry-form")?.scrollIntoView({ behavior: "smooth", block: "start" }));
    },
    async saveEntry() {
      this.saving = true;
      const payload = { entry_type: this.form.entry_type, amount: this.form.amount, occurred_on: this.form.occurred_on, source_transfer_id: this.form.entry_type === "transfer" ? this.form.source_transfer_id : null, note: this.form.note || null };
      try {
        if (this.editingEntry) await apiClient.patch(`/api/holding-cost-entries/${this.editingEntry.id}`, payload);
        else await apiClient.post(`/api/holdings/${this.form.holding_id}/cost-entries`, payload);
        this.resetForm(); this.$emit("changed");
      } catch (error) { this.$swal.fire("無法儲存", error.response?.data?.message || "請稍後再試。", "error"); }
      finally { this.saving = false; }
    },
    async deleteEntry(entry) {
      const result = await this.$swal.fire({ title: "刪除投入成本？", text: `${entry.holdingName} · ${this.formatMoney(entry.amount)}`, icon: "warning", showCancelButton: true, confirmButtonText: "刪除", cancelButtonText: "取消" });
      if (!result.isConfirmed) return;
      try { await apiClient.delete(`/api/holding-cost-entries/${entry.id}`); this.$emit("changed"); }
      catch (error) { this.$swal.fire("刪除失敗", error.response?.data?.message || "請稍後再試。", "error"); }
    },
  },
};
</script>

<style scoped>
.tab-panel { display: grid; gap: 14px; }.cost-summary { padding: 16px; border: 1px solid #bfdbfe; border-radius: 10px; background: #eff6ff; }.cost-summary > div { display: flex; justify-content: space-between; gap: 12px; }.cost-summary span { color: #475569; font-weight: 700; }.cost-summary strong { color: #1d4ed8; font-size: 1.3rem; }.cost-summary p { margin: 5px 0 0; color: #64748b; font-size: .86rem; }
.panel-toggle { justify-self: start; min-height: 40px; display: inline-flex; align-items: center; gap: 7px; padding: 0 12px; color: #0f766e; background: #fff; border: 1px solid #99f6e4; }.panel-toggle svg { width: 17px; height: 17px; }
.entry-form { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; padding: 16px; border: 1px solid #dbe4ee; border-radius: 10px; background: #f8fafc; }.entry-form label { display: grid; gap: 6px; color: #475569; font-weight: 700; }.wide-field { grid-column: 1 / -1; }.entry-form input, .entry-form select { width: 100%; min-height: 44px; padding: 0 12px; border: 1px solid #cbd5e1; border-radius: 8px; background: #fff; font: inherit; }.entry-form input:focus, .entry-form select:focus { outline: 3px solid #ccfbf1; border-color: #0f766e; }
.form-actions { display: flex; justify-content: flex-end; gap: 8px; }.primary-action, .secondary-action { min-height: 38px; padding: 0 12px; border-radius: 8px; }.primary-action { color: #fff; background: #0f766e; }.secondary-action { color: #334155; background: #fff; border: 1px solid #cbd5e1; }.form-hint { margin: 0; color: #b45309; font-size: .86rem; }
.cost-list { display: grid; gap: 8px; }.cost-row { display: grid; grid-template-columns: 54px minmax(0, 1fr) auto auto; align-items: center; gap: 12px; padding: 12px; border: 1px solid #dbe4ee; border-radius: 10px; background: #fff; }.cost-date { display: grid; place-items: center; padding: 6px; color: #0f766e; background: #f0fdfa; border-radius: 8px; }.cost-date strong { font-size: 1.12rem; line-height: 1; }.cost-date span { font-size: .68rem; }.cost-copy { min-width: 0; display: grid; gap: 2px; }.cost-copy span { overflow: hidden; color: #64748b; font-size: .84rem; text-overflow: ellipsis; white-space: nowrap; }.cost-amount { color: #1f2933; white-space: nowrap; }.row-actions { display: flex; gap: 4px; }.row-actions button { width: 34px; height: 34px; display: grid; place-items: center; padding: 0; color: #475569; background: #f8fafc; border: 1px solid #e2e8f0; }.row-actions button svg { width: 16px; height: 16px; }.row-actions .danger-icon { color: #b91c1c; }.empty-state { padding: 28px 16px; color: #64748b; text-align: center; border: 1px dashed #cbd5e1; border-radius: 10px; background: #f8fafc; }
@media (max-width: 640px) { .entry-form { grid-template-columns: 1fr; }.entry-form label, .wide-field { grid-column: 1; }.cost-row { grid-template-columns: 48px minmax(0, 1fr) auto; }.cost-amount { grid-column: 2; }.row-actions { grid-column: 3; grid-row: 1 / span 2; flex-direction: column; } }
</style>
