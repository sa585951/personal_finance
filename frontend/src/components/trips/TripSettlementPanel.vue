<template>
  <section class="trip-settlement-panel">
    <div class="trip-closeout-panel" :class="closeoutStatus.tone">
      <div class="closeout-header">
        <span>旅行收尾檢查</span>
        <strong :class="closeoutStatus.tone">{{ closeoutStatus.label }}</strong>
      </div>
      <div class="closeout-list">
        <div
          v-for="item in closeoutChecks"
          :key="item.label"
          class="closeout-item"
          :class="item.tone"
        >
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
        </div>
      </div>
    </div>

    <div class="section-title split-title-row">
      <div>
        <TrendCharts />
        <h3>誰要給誰</h3>
      </div>
      <button class="copy-summary-button" type="button" @click="$emit('copy-summary')">
        複製摘要
      </button>
    </div>
    <div v-if="suggestions.length === 0" class="empty-state">目前已平衡或尚無需結算</div>
    <div v-else class="settlement-list settlement-action-list">
      <div
        v-for="suggestion in suggestions"
        :key="`${suggestion.from_member_id}-${suggestion.to_member_id}-${suggestion.amount}`"
        class="settlement-row settlement-action-row"
      >
        <div class="settlement-route">
          <strong>{{ suggestion.from_display_name }}</strong>
          <span>→</span>
          <strong>{{ suggestion.to_display_name }}</strong>
        </div>
        <div class="settlement-actions">
          <div class="settlement-action-amount">
            <small v-if="paidForPair(suggestion.from_member_id, suggestion.to_member_id) > 0">
              已還 {{ formatMoney(paidForPair(suggestion.from_member_id, suggestion.to_member_id), suggestion.currency) }}
            </small>
            <strong>剩餘 {{ formatMoney(suggestion.amount, suggestion.currency) }}</strong>
          </div>
          <button
            v-if="suggestion.can_confirm !== false"
            class="confirm-settlement-button"
            type="button"
            @click="$emit('select-suggestion', suggestion)"
          >
            依此記錄
          </button>
        </div>
      </div>
    </div>

    <form v-if="(debtors.length && creditors.length) || form.id" class="settlement-form" @submit.prevent="$emit('submit')">
      <strong>{{ form.id ? "修改還款紀錄" : "記錄已收到的還款" }}</strong>
      <div class="settlement-form-fields">
        <label>
          付款旅伴
          <select
            :value="form.from_member_id"
            :disabled="Boolean(form.id) || submitting"
            required
            @change="$emit('update-form', { from_member_id: $event.target.value })"
          >
            <option value="">請選擇</option>
            <option v-for="member in debtors" :key="member.member_id" :value="member.member_id">
              {{ member.display_name }}
            </option>
            <option v-if="form.id && !debtors.some((member) => member.member_id === form.from_member_id)" :value="form.from_member_id">
              {{ memberName(form.from_member_id) }}
            </option>
          </select>
        </label>
        <label>
          收款旅伴
          <select
            :value="form.to_member_id"
            :disabled="Boolean(form.id) || submitting"
            required
            @change="$emit('update-form', { to_member_id: $event.target.value })"
          >
            <option value="">請選擇</option>
            <option v-for="member in creditors" :key="member.member_id" :value="member.member_id">
              {{ member.display_name }}
            </option>
            <option v-if="form.id && !creditors.some((member) => member.member_id === form.to_member_id)" :value="form.to_member_id">
              {{ memberName(form.to_member_id) }}
            </option>
          </select>
        </label>
        <label>
          本次還款金額
          <input
            :value="form.amount"
            type="number"
            inputmode="decimal"
            :min="amountStep"
            :max="settlementLimit"
            :step="amountStep"
            :disabled="submitting"
            required
            @input="$emit('update-form', { amount: $event.target.value })"
          >
        </label>
        <label>
          收款日期
          <input
            :value="form.settled_on"
            type="date"
            :max="today"
            :disabled="submitting"
            required
            @input="$emit('update-form', { settled_on: $event.target.value })"
          >
        </label>
      </div>
      <small v-if="form.from_member_id && form.to_member_id">
        已還 {{ formatMoney(paidForSelectedPair, currency) }} · 目前待還 {{ formatMoney(currentRemaining, currency) }}
      </small>
      <small>此處只更新旅行分帳；不會自動異動任何人的帳戶餘額。</small>
      <div class="settlement-form-actions">
        <button v-if="form.id" class="quiet-mini-button" type="button" :disabled="submitting" @click="$emit('cancel-edit')">取消修改</button>
        <button class="confirm-settlement-button" type="submit" :disabled="!canSubmit">
          {{ submitting ? "儲存中..." : form.id ? "儲存修改" : "記錄還款" }}
        </button>
      </div>
    </form>

    <button class="detail-toggle settlement-title" type="button" @click="$emit('toggle-details')">
      <span>
        <TrendCharts />
        核對明細
      </span>
      <strong>{{ showDetails ? "收合" : "展開" }}</strong>
    </button>
    <div v-if="showDetails && summary.length === 0" class="empty-state">尚無分帳資料</div>
    <div v-else-if="showDetails" class="split-summary-list">
      <div
        v-for="member in summary"
        :key="member.member_id"
        class="split-summary-row"
        :class="splitStatusClass(member)"
      >
        <div>
          <strong>{{ member.display_name }}</strong>
          <span>
            付款 {{ formatMoney(member.paid_amount, member.currency) }} ·
            分攤 {{ formatMoney(member.share_amount, member.currency) }}
          </span>
        </div>
        <strong
          class="net-amount"
          :class="member.net_amount >= 0 ? 'positive-net' : 'negative-net'"
        >
          <small>{{ splitNetStatus(member) }}</small>
          {{ formatMoney(Math.abs(member.net_amount), member.currency) }}
        </strong>
      </div>
    </div>

    <div class="section-title settlement-title">
      <TrendCharts />
      <h3>還款紀錄</h3>
    </div>
    <div v-if="records.length === 0" class="empty-state">尚無還款紀錄</div>
    <div v-else class="settlement-list">
      <div v-for="settlement in records" :key="settlement.id" class="settlement-row settled">
        <div class="settlement-record-copy">
          <span>{{ settlement.from_display_name }} 已付給 {{ settlement.to_display_name }}</span>
          <small>收款日期：{{ settlement.settled_on || "未記錄" }}</small>
          <small v-if="settlement.account_entry?.status === 'posted'">
            {{ settlement.account_entry.account_name }} ·
            {{ settlement.account_entry.direction === "incoming" ? "已入帳" : "已扣款" }}
          </small>
          <small v-else-if="settlement.account_entry?.status === 'reversed'">
            {{ settlement.account_entry.account_name }} · 私人帳戶入帳已取消
          </small>
        </div>
        <div class="settlement-actions">
          <strong>{{ formatMoney(settlement.amount, settlement.currency) }}</strong>
          <button
            v-if="settlement.can_edit"
            class="quiet-mini-button"
            type="button"
            @click="$emit('edit', settlement)"
          >
            修改
          </button>
          <button
            v-if="settlement.can_post_account"
            class="quiet-mini-button"
            type="button"
            @click="$emit('post-account', settlement)"
          >
            記入我的帳戶
          </button>
          <button
            v-if="settlement.can_reverse_account"
            class="quiet-mini-button"
            type="button"
            @click="$emit('reverse-account', settlement)"
          >
            取消帳戶入帳
          </button>
          <button
            v-if="settlement.can_void !== false"
            class="quiet-mini-button"
            type="button"
            @click="$emit('void', settlement)"
          >
            撤銷
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script>
import { TrendCharts } from "@element-plus/icons-vue";

export default {
  name: "TripSettlementPanel",
  components: { TrendCharts },
  props: {
    closeoutStatus: { type: Object, required: true },
    closeoutChecks: { type: Array, default: () => [] },
    suggestions: { type: Array, default: () => [] },
    summary: { type: Array, default: () => [] },
    records: { type: Array, default: () => [] },
    showDetails: { type: Boolean, default: false },
    form: { type: Object, required: true },
    submitting: { type: Boolean, default: false },
    currentMemberId: { type: String, default: "" },
    isOwner: { type: Boolean, default: false },
    tripTimezone: { type: String, default: "Asia/Taipei" },
  },
  emits: [
    "select-suggestion",
    "update-form",
    "submit",
    "edit",
    "cancel-edit",
    "copy-summary",
    "post-account",
    "reverse-account",
    "toggle-details",
    "void",
  ],
  computed: {
    debtors() {
      return this.summary.filter((member) => Number(member.net_amount) < 0);
    },
    creditors() {
      return this.summary.filter((member) => Number(member.net_amount) > 0);
    },
    currency() {
      return this.summary[0]?.currency || "TWD";
    },
    amountStep() {
      return "0.0001";
    },
    today() {
      return new Date().toLocaleDateString("sv-SE", { timeZone: this.tripTimezone });
    },
    paidForSelectedPair() {
      return this.paidForPair(this.form.from_member_id, this.form.to_member_id);
    },
    currentRemaining() {
      const debtor = this.summary.find((member) => member.member_id === this.form.from_member_id);
      const creditor = this.summary.find((member) => member.member_id === this.form.to_member_id);
      return debtor && creditor ? Math.max(0, Math.min(-Number(debtor.net_amount), Number(creditor.net_amount))) : 0;
    },
    settlementLimit() {
      const previous = this.form.id
        ? Number(this.records.find((record) => record.id === this.form.id)?.amount || 0)
        : 0;
      return this.currentRemaining + previous;
    },
    canSubmit() {
      const amount = Number(this.form.amount);
      const allowed = this.isOwner || [this.form.from_member_id, this.form.to_member_id].includes(this.currentMemberId);
      return !this.submitting && allowed && Boolean(this.form.from_member_id && this.form.to_member_id)
        && this.form.from_member_id !== this.form.to_member_id
        && Number.isFinite(amount) && amount > 0 && amount <= this.settlementLimit
        && Math.abs(amount / Number(this.amountStep) - Math.round(amount / Number(this.amountStep))) < 1e-8
        && Boolean(this.form.settled_on) && this.form.settled_on <= this.today;
    },
  },
  methods: {
    paidForPair(fromMemberId, toMemberId) {
      return this.records
        .filter((record) => record.from_member_id === fromMemberId && record.to_member_id === toMemberId)
        .reduce((total, record) => total + Number(record.amount), 0);
    },
    memberName(memberId) {
      return this.summary.find((member) => member.member_id === memberId)?.display_name || "旅伴";
    },
    formatMoney(amount, currency) {
      const minorUnit = ["TWD", "JPY", "KRW"].includes(currency) ? 0 : 2;
      const hasExtraPrecision = Math.abs(Number(amount) * (10 ** minorUnit) - Math.round(Number(amount) * (10 ** minorUnit))) > 1e-8;
      return `${currency} ${Number(amount || 0).toLocaleString("zh-TW", {
        minimumFractionDigits: minorUnit,
        maximumFractionDigits: hasExtraPrecision ? 4 : minorUnit,
      })}`;
    },
    splitStatusClass(member) {
      const netAmount = Number(member.net_amount || 0);
      if (netAmount > 0) return "receivable";
      if (netAmount < 0) return "payable";
      return "balanced";
    },
    splitNetStatus(member) {
      const netAmount = Number(member.net_amount || 0);
      if (netAmount > 0) return "待收";
      if (netAmount < 0) return "待付";
      return "已平衡";
    },
  },
};
</script>

<style scoped>
.settlement-form {
  display: grid;
  gap: 10px;
  margin-top: 14px;
  padding: 14px;
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
}

.settlement-form-fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.settlement-form-fields label {
  display: grid;
  gap: 5px;
  color: #334155;
  font-size: 0.85rem;
  font-weight: 700;
}

.settlement-form-fields input,
.settlement-form-fields select {
  min-width: 0;
  width: 100%;
  min-height: 38px;
  padding: 7px 9px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  color: #0f172a;
  font: inherit;
}

.settlement-form small {
  color: #475569;
}

.settlement-form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.settlement-form-actions button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.settlement-action-amount {
  display: grid;
  gap: 2px;
  text-align: right;
}

.settlement-action-amount small {
  color: #475569;
}

.trip-closeout-panel {
  display: grid;
  gap: 10px;
  margin-bottom: 14px;
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-left: 5px solid #94a3b8;
  border-radius: 8px;
}

.trip-closeout-panel.success {
  background: #f0fdf4;
  border-color: #bbf7d0;
  border-left-color: #16a34a;
}

.trip-closeout-panel.warning {
  background: #fffbeb;
  border-color: #fde68a;
  border-left-color: #f59e0b;
}

.trip-closeout-panel.neutral {
  background: #f8fafc;
  border-color: #cbd5e1;
  border-left-color: #94a3b8;
}

.closeout-header,
.closeout-item,
.split-summary-row,
.settlement-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.closeout-header span {
  color: #334155;
  font-weight: 900;
}

.closeout-header strong,
.closeout-item strong {
  font-weight: 900;
}

.closeout-header strong {
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 0.82rem;
}

.closeout-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.closeout-item {
  min-height: 40px;
  padding: 8px 10px;
  background: #ffffff;
  border: 1px solid #dbe4ee;
  border-left: 4px solid #94a3b8;
  border-radius: 8px;
}

.closeout-item span {
  color: #64748b;
  font-size: 0.82rem;
  font-weight: 800;
}

.closeout-item.success {
  border-color: #bbf7d0;
  border-left-color: #16a34a;
}

.closeout-item.warning {
  background: #fff7ed;
  border-color: #fed7aa;
  border-left-color: #f59e0b;
}

.closeout-header .success,
.closeout-item.success strong {
  color: #15803d;
}

.closeout-header .success {
  background: #dcfce7;
}

.closeout-header .warning,
.closeout-item.warning strong {
  color: #b45309;
}

.closeout-header .warning {
  background: #fef3c7;
}

.closeout-header .neutral,
.closeout-item.neutral strong {
  color: #64748b;
}

.closeout-header .neutral {
  background: #e2e8f0;
}

.section-title,
.split-title-row > div {
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-title {
  margin-bottom: 14px;
  color: #334155;
}

.section-title h3 {
  margin: 0;
  letter-spacing: 0;
}

.section-title svg {
  width: 18px;
  height: 18px;
}

.split-title-row {
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 12px;
}

.copy-summary-button {
  flex: 0 0 auto;
  min-height: 34px;
  padding: 0 10px;
  color: #0f766e;
  background: #ccfbf1;
  border: 0;
  border-radius: 8px;
  box-shadow: none;
  font-size: 0.84rem;
  font-weight: 800;
}

.empty-state {
  margin: 12px 0 0;
  color: #475569;
}

.split-summary-row,
.settlement-row {
  min-height: 62px;
  padding: 10px 12px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.split-summary-row > div {
  display: grid;
  gap: 2px;
}

.split-summary-row span {
  color: #64748b;
}

.split-summary-list,
.settlement-list {
  display: grid;
  gap: 8px;
}

.split-summary-row.receivable {
  background: #ecfdf5;
  border-color: #99f6e4;
}

.split-summary-row.receivable span {
  color: #0f766e;
}

.split-summary-row.payable {
  background: #fff1f2;
  border-color: #fecdd3;
}

.split-summary-row.payable span {
  color: #be123c;
}

.split-summary-row.balanced {
  background: #f8fafc;
}

.net-amount {
  display: grid;
  gap: 2px;
  min-width: 96px;
  text-align: right;
}

.net-amount small {
  color: #64748b;
  font-size: 0.76rem;
  font-weight: 800;
}

.positive-net {
  color: #0f766e;
}

.negative-net {
  color: #dc2626;
}

.settlement-title {
  margin-top: 18px;
}

.detail-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-height: 44px;
  padding: 10px 12px;
  color: #334155;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  box-shadow: none;
}

.detail-toggle span {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 0.96rem;
  font-weight: 800;
}

.detail-toggle svg {
  width: 18px;
  height: 18px;
  color: #0f766e;
}

.detail-toggle strong {
  color: #64748b;
  font-size: 0.82rem;
}

.settlement-action-row,
.settlement-row {
  background: #eff6ff;
  border-color: #bfdbfe;
}

.settlement-route {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.settlement-route strong {
  color: #1e40af;
  font-size: 1rem;
}

.settlement-route strong:last-child {
  text-align: right;
}

.settlement-route span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  color: #1d4ed8;
  background: #dbeafe;
  border-radius: 999px;
  font-weight: 900;
}

.settlement-row.settled {
  background: #f0fdfa;
  border-color: #99f6e4;
}

.settlement-row > span {
  color: #1e40af;
  font-weight: 700;
}

.settlement-row.settled > span,
.settlement-row.settled strong {
  color: #0f766e;
}

.settlement-record-copy {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.settlement-record-copy span {
  color: #0f766e;
  font-weight: 700;
}

.settlement-record-copy small {
  color: #64748b;
  font-size: 0.78rem;
}

.settlement-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.confirm-settlement-button,
.quiet-mini-button {
  min-height: 32px;
  padding: 0 10px;
  border: 0;
  border-radius: 8px;
  box-shadow: none;
  font-size: 0.86rem;
  font-weight: 800;
}

.confirm-settlement-button {
  color: #ffffff;
  background: #2563eb;
}

.quiet-mini-button {
  color: #475569;
  background: #e2e8f0;
}

@media (max-width: 820px) {
  .settlement-form-fields {
    grid-template-columns: 1fr;
  }

  .closeout-list {
    grid-template-columns: 1fr;
  }

  .split-summary-row,
  .settlement-row {
    align-items: flex-start;
    flex-direction: column;
  }

  .settlement-action-row {
    gap: 10px;
  }

  .settlement-route,
  .settlement-actions {
    width: 100%;
  }

  .settlement-actions {
    justify-content: space-between;
    margin-left: 0;
  }
}
</style>
