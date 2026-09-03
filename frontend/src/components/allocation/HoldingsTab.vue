<template>
  <section class="tab-panel">
    <div class="target-summary">
      <div>
        <span>目標比例合計</span>
        <strong :class="{ complete: targetTotal === 100 }">{{ targetTotal }}%</strong>
      </div>
      <p>{{ targetTotal === 100 ? "可以進行新增投入試算" : "比例可先分次設定，試算前需合計為 100%" }}</p>
      <div class="target-track"><div :style="{ width: `${Math.min(targetTotal, 100)}%` }"></div></div>
    </div>

    <button class="panel-toggle" type="button" @click="toggleForm">
      <Close v-if="showForm" /><Plus v-else />
      {{ showForm ? "收合表單" : "新增配置標的" }}
    </button>

    <form v-if="showForm" class="entry-form" @submit.prevent="saveHolding">
      <AccountPicker
        v-model="form.account_id"
        class="wide-field"
        :accounts="investmentAccounts"
        label="投資帳戶"
        :placeholder="`請選擇 ${portfolio.base_currency} 投資帳戶`"
        :allow-none="false"
        :disabled="Boolean(editingHolding?.hasHistory)"
      />
      <label>
        <span>標的名稱</span>
        <input v-model.trim="form.name" maxlength="100" placeholder="例如：元大台灣 50" required />
      </label>
      <label>
        <span>代號（選填）</span>
        <input v-model.trim="form.symbol" maxlength="50" placeholder="例如：0050" />
      </label>
      <label>
        <span>資產類別（選填）</span>
        <input v-model.trim="form.asset_class" maxlength="50" placeholder="例如：核心 ETF" />
      </label>
      <label>
        <span>目標比例 %（可稍後設定）</span>
        <input v-model.number="form.target_percentage" type="number" min="0" max="100" step="0.01" placeholder="80" />
      </label>
      <div class="form-actions wide-field">
        <button v-if="editingHolding" class="secondary-action" type="button" @click="resetForm">取消編輯</button>
        <button class="primary-action" type="submit" :disabled="saving || !investmentAccounts.length">
          {{ saving ? "儲存中" : editingHolding ? "儲存變更" : "新增標的" }}
        </button>
      </div>
      <p v-if="!investmentAccounts.length" class="form-hint wide-field">
        尚無符合 {{ portfolio.base_currency }} 的投資帳戶，請先到帳戶頁新增 investment 類型帳戶。
      </p>
    </form>

    <div v-if="!holdings.length" class="empty-state">尚未建立配置標的。</div>
    <div v-else class="holding-list">
      <article v-for="holding in holdings" :key="holding.id" class="holding-card" :class="{ inactive: !holding.is_active }">
        <div class="holding-top">
          <div>
            <span>{{ holding.symbol || holding.asset_class || "配置標的" }}</span>
            <h3>{{ holding.name }}</h3>
            <p>{{ accountName(holding.account_id) }} · {{ portfolio.base_currency }}</p>
          </div>
          <strong>{{ weightPercent(holding.target_weight) }}</strong>
        </div>
        <div class="holding-meta">
          <span>投入成本 {{ formatMoney(holding.recorded_cost) }}</span>
          <span>{{ holding.cost_entries?.length || 0 }} 筆紀錄</span>
          <span v-if="!holding.is_active">已停用</span>
        </div>
        <div class="card-actions">
          <button type="button" @click="startEdit(holding)"><EditPen />編輯</button>
          <button class="danger-action" type="button" @click="removeHolding(holding)"><Delete />{{ holdingHasHistory(holding) ? "停用" : "移除" }}</button>
        </div>
      </article>
    </div>
  </section>
</template>

<script>
import apiClient from "@/api";
import AccountPicker from "@/components/shared/AccountPicker.vue";
import { Close, Delete, EditPen, Plus } from "@element-plus/icons-vue";

export default {
  name: "HoldingsTab",
  components: { AccountPicker, Close, Delete, EditPen, Plus },
  props: {
    portfolio: { type: Object, required: true },
    accounts: { type: Array, default: () => [] },
  },
  emits: ["changed"],
  data() {
    return {
      showForm: false,
      saving: false,
      editingHolding: null,
      form: this.emptyForm(),
    };
  },
  computed: {
    holdings() { return this.portfolio.holdings || []; },
    activeHoldings() { return this.holdings.filter((holding) => holding.is_active !== false); },
    investmentAccounts() {
      return this.accounts.filter((account) => account.account_type === "investment" && account.currency === this.portfolio.base_currency);
    },
    targetTotal() {
      return Math.round(this.activeHoldings.reduce((sum, holding) => sum + Number(holding.target_weight || 0) * 100, 0) * 100) / 100;
    },
  },
  methods: {
    emptyForm() { return { account_id: "", name: "", symbol: "", asset_class: "", target_percentage: null }; },
    toggleForm() { this.showForm ? this.resetForm() : (this.showForm = true); },
    resetForm() { this.form = this.emptyForm(); this.editingHolding = null; this.showForm = false; },
    accountName(accountId) { return this.accounts.find((account) => account.id === accountId)?.bank_name || "投資帳戶"; },
    weightPercent(weight) { return weight === null || weight === undefined ? "未設定" : `${(Number(weight) * 100).toFixed(2).replace(/\.00$/, "")}%`; },
    formatMoney(amount) { return `${this.portfolio.base_currency} ${Number(amount || 0).toLocaleString("zh-TW", { maximumFractionDigits: 2 })}`; },
    holdingHasHistory(holding) {
      const hasCost = Boolean(holding.cost_entries?.length);
      const hasSnapshot = (this.portfolio.snapshots || []).some((snapshot) => (
        snapshot.items?.some((item) => item.holding_id === holding.id)
      ));
      return hasCost || hasSnapshot;
    },
    startEdit(holding) {
      this.editingHolding = { ...holding, hasHistory: this.holdingHasHistory(holding) };
      this.form = {
        account_id: holding.account_id,
        name: holding.name,
        symbol: holding.symbol || "",
        asset_class: holding.asset_class || "",
        target_percentage: holding.target_weight === null ? null : Number(holding.target_weight) * 100,
      };
      this.showForm = true;
      this.$nextTick(() => document.querySelector(".entry-form")?.scrollIntoView({ behavior: "smooth", block: "start" }));
    },
    async saveHolding() {
      if (!this.form.account_id) {
        this.$swal.fire("欄位未完整", "請選擇投資帳戶。", "warning");
        return;
      }
      this.saving = true;
      const payload = {
        account_id: this.form.account_id,
        name: this.form.name,
        symbol: this.form.symbol || null,
        asset_class: this.form.asset_class || null,
        target_weight: this.form.target_percentage === null || this.form.target_percentage === "" ? null : Number(this.form.target_percentage) / 100,
      };
      try {
        if (this.editingHolding) await apiClient.patch(`/api/holdings/${this.editingHolding.id}`, payload);
        else await apiClient.post(`/api/portfolios/${this.portfolio.id}/holdings`, payload);
        this.resetForm();
        this.$emit("changed");
      } catch (error) {
        this.$swal.fire("無法儲存", error.response?.data?.message || "請稍後再試。", "error");
      } finally { this.saving = false; }
    },
    async removeHolding(holding) {
      const hasHistory = this.holdingHasHistory(holding);
      const result = await this.$swal.fire({
        title: hasHistory ? "停用配置標的？" : "移除配置標的？",
        text: hasHistory ? "已有成本紀錄的標的會保留歷史並改為停用。" : "此標的尚無歷史資料，可以安全移除。",
        icon: "warning", showCancelButton: true, confirmButtonText: hasHistory ? "停用" : "移除", cancelButtonText: "取消",
      });
      if (!result.isConfirmed) return;
      try { await apiClient.delete(`/api/holdings/${holding.id}`); this.$emit("changed"); }
      catch (error) { this.$swal.fire("操作失敗", error.response?.data?.message || "請稍後再試。", "error"); }
    },
  },
};
</script>

<style scoped>
.tab-panel { display: grid; gap: 14px; }
.target-summary { padding: 16px; border: 1px solid #99f6e4; border-radius: 10px; background: #f0fdfa; }
.target-summary > div:first-child { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; }
.target-summary span { color: #475569; font-weight: 700; }
.target-summary strong { color: #b45309; font-size: 1.35rem; }.target-summary strong.complete { color: #0f766e; }
.target-summary p { margin: 6px 0 10px; color: #64748b; font-size: .86rem; }
.target-track { height: 8px; overflow: hidden; background: #dbe4ee; border-radius: 999px; }.target-track div { height: 100%; background: #0f766e; }
.panel-toggle { justify-self: start; min-height: 40px; display: inline-flex; align-items: center; gap: 7px; padding: 0 12px; color: #0f766e; background: #fff; border: 1px solid #99f6e4; }.panel-toggle svg { width: 17px; height: 17px; }
.entry-form { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; padding: 16px; border: 1px solid #dbe4ee; border-radius: 10px; background: #f8fafc; }
.entry-form label { display: grid; gap: 6px; color: #475569; font-weight: 700; }.wide-field { grid-column: 1 / -1; }
.entry-form input, .entry-form select { width: 100%; min-height: 44px; padding: 0 12px; border: 1px solid #cbd5e1; border-radius: 8px; background: #fff; font: inherit; }.entry-form input:focus, .entry-form select:focus { outline: 3px solid #ccfbf1; border-color: #0f766e; }
.form-actions, .card-actions { display: flex; justify-content: flex-end; gap: 8px; }.primary-action, .secondary-action, .card-actions button { min-height: 38px; display: inline-flex; align-items: center; justify-content: center; gap: 6px; padding: 0 12px; border-radius: 8px; }.primary-action { color: #fff; background: #0f766e; }.secondary-action, .card-actions button { color: #334155; background: #fff; border: 1px solid #cbd5e1; }.card-actions svg { width: 16px; height: 16px; }.card-actions .danger-action { color: #b91c1c; border-color: #fecaca; background: #fef2f2; }
.form-hint { margin: 0; color: #b45309; font-size: .86rem; }
.holding-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }.holding-card { padding: 16px; border: 1px solid #dbe4ee; border-radius: 10px; background: #fff; }.holding-card.inactive { opacity: .65; }
.holding-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }.holding-top span { color: #0f766e; font-size: .75rem; font-weight: 800; }.holding-top h3 { margin: 2px 0; }.holding-top p { margin: 0; color: #64748b; font-size: .86rem; }.holding-top > strong { color: #0f766e; font-size: 1.2rem; }
.holding-meta { display: flex; flex-wrap: wrap; gap: 6px 12px; margin: 14px 0; padding: 10px 0; color: #64748b; border-top: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0; font-size: .82rem; }
.empty-state { padding: 28px 16px; color: #64748b; text-align: center; border: 1px dashed #cbd5e1; border-radius: 10px; background: #f8fafc; }
@media (max-width: 640px) { .entry-form, .holding-list { grid-template-columns: 1fr; }.entry-form label, .wide-field { grid-column: 1; } }
</style>
