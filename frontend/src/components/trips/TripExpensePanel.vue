<template>
  <section class="trip-expense-panel">
    <div class="section-title">
      <Money />
      <h3>新增旅行支出</h3>
    </div>
    <form class="expense-form" @submit.prevent="$emit('submit')">
      <label>
        品項
        <input
          :value="expense.item"
          type="text"
          required
          placeholder="拉麵"
          @input="updateText('item', $event.target.value)"
        />
      </label>
      <label>
        金額
        <input
          :value="expense.amount"
          type="number"
          min="1"
          step="1"
          required
          @input="updateNumber('amount', $event.target.value)"
        />
      </label>

      <div class="quick-currency-row full-row">
        <button
          v-for="currency in quickCurrencies"
          :key="currency"
          type="button"
          :class="{ active: expense.original_currency === currency }"
          @click="updateExpense({ original_currency: currency })"
        >
          {{ currency }}
        </button>
      </div>

      <label>
        類別
        <select
          :value="expense.budget_category"
          required
          @change="updateExpense({ budget_category: $event.target.value })"
        >
          <option v-for="category in expenseCategories" :key="category" :value="category">
            {{ category }}
          </option>
        </select>
      </label>
      <label>
        付款人
        <select
          :value="expense.paid_by_member_id"
          @change="updateExpense({ paid_by_member_id: $event.target.value })"
        >
          <option v-for="member in members" :key="member.id" :value="member.id">
            {{ member.display_name }}
          </option>
        </select>
      </label>

      <AccountPicker
        class="full-row"
        :model-value="expense.account_id"
        :accounts="accounts"
        label="付款帳戶"
        :disabled="!isCurrentUserPayer"
        @update:model-value="updateExpense({ account_id: $event })"
      />
      <p v-if="!isCurrentUserPayer" class="account-link-hint full-row">
        只有自己付款時才會連動帳戶。其他旅伴墊款會進入分帳結算，不會異動你的帳戶餘額。
      </p>

      <div v-if="expensePreview" class="expense-preview full-row">
        <div>
          <span>約略本幣</span>
          <strong>{{ expensePreview.convertedText }}</strong>
        </div>
        <div>
          <span>帳戶扣款</span>
          <strong>{{ expensePreview.accountDebitText }}</strong>
        </div>
      </div>

      <div class="split-box full-row">
        <div class="split-header">
          <span>分帳方式</span>
          <div class="split-mode-tabs">
            <button
              type="button"
              :class="{ active: expense.split_mode === 'equal' }"
              @click="$emit('set-split-mode', 'equal')"
            >
              均分
            </button>
            <button
              type="button"
              :class="{ active: expense.split_mode === 'custom' }"
              @click="$emit('set-split-mode', 'custom')"
            >
              自訂
            </button>
          </div>
        </div>

        <template v-if="expense.split_mode === 'equal'">
          <button class="split-member-toggle" type="button" @click="$emit('toggle-member-options')">
            <span>{{ splitMemberSummary }}</span>
            <strong>{{ showMemberOptions ? "收合" : "調整" }}</strong>
          </button>
          <div v-if="showMemberOptions" class="split-member-options">
            <label v-for="member in members" :key="member.id" class="split-option">
              <input
                type="checkbox"
                :value="member.id"
                :checked="expense.split_member_ids.includes(member.id)"
                @change="toggleSplitMember(member.id, $event.target.checked)"
              />
              {{ member.display_name }}
            </label>
          </div>
        </template>

        <div v-else class="custom-split-list">
          <label v-for="member in members" :key="member.id" class="custom-split-row">
            <span>{{ member.display_name }}</span>
            <input
              :value="expense.split_allocations[member.id]"
              type="number"
              min="0"
              step="1"
              @input="updateSplitAllocation(member.id, $event.target.value)"
            />
          </label>
          <div class="custom-split-summary" :class="{ invalid: customSplitDifference !== 0 }">
            <span>合計 {{ formatMoney(customSplitTotal, expense.original_currency) }}</span>
            <strong>
              {{ customSplitDifference === 0
                ? "已平衡"
                : `差額 ${formatMoney(customSplitDifference, expense.original_currency)}` }}
            </strong>
          </div>
        </div>
      </div>

      <button class="advanced-toggle full-row" type="button" @click="$emit('toggle-advanced')">
        {{ showAdvanced ? "收合進階設定" : "進階設定" }}
      </button>
      <div v-if="showAdvanced" class="advanced-expense-grid full-row">
        <label>
          日期
          <input
            :value="expense.date"
            type="date"
            required
            @input="updateExpense({ date: $event.target.value })"
          />
        </label>
        <label>
          店家
          <input
            :value="expense.merchant"
            type="text"
            placeholder="一蘭"
            @input="updateText('merchant', $event.target.value)"
          />
        </label>
        <label>
          匯率
          <input
            :value="expense.exchange_rate"
            type="number"
            min="0.00000001"
            step="0.00000001"
            required
            @input="updateNumber('exchange_rate', $event.target.value)"
          />
        </label>
        <label>
          備註
          <input
            :value="expense.description"
            type="text"
            placeholder="可留空"
            @input="updateText('description', $event.target.value)"
          />
        </label>
        <label>
          確認狀態
          <select
            :value="expense.review_status"
            @change="updateExpense({ review_status: $event.target.value })"
          >
            <option value="confirmed">已確認</option>
            <option value="pending">待確認</option>
          </select>
        </label>
      </div>

      <button
        v-if="editingTransactionId"
        class="quiet-action full-row"
        type="button"
        @click="$emit('cancel-edit')"
      >
        取消編輯
      </button>
      <button class="primary-action full-row" type="submit" :disabled="submitting">
        <Plus />
        {{ editingTransactionId ? "更新支出" : "新增支出" }}
      </button>
    </form>
    <p v-if="message" class="status-message">{{ message }}</p>
  </section>
</template>

<script>
import { Money, Plus } from "@element-plus/icons-vue";
import AccountPicker from "@/components/shared/AccountPicker.vue";

export default {
  name: "TripExpensePanel",
  components: { AccountPicker, Money, Plus },
  props: {
    expense: { type: Object, required: true },
    quickCurrencies: { type: Array, default: () => [] },
    expenseCategories: { type: Array, default: () => [] },
    members: { type: Array, default: () => [] },
    accounts: { type: Array, default: () => [] },
    isCurrentUserPayer: { type: Boolean, default: false },
    expensePreview: { type: Object, default: null },
    splitMemberSummary: { type: String, default: "" },
    customSplitTotal: { type: Number, default: 0 },
    customSplitDifference: { type: Number, default: 0 },
    showMemberOptions: { type: Boolean, default: false },
    showAdvanced: { type: Boolean, default: false },
    editingTransactionId: { type: String, default: "" },
    submitting: { type: Boolean, default: false },
    message: { type: String, default: "" },
  },
  emits: [
    "cancel-edit",
    "set-split-mode",
    "submit",
    "toggle-advanced",
    "toggle-member-options",
    "update-expense",
  ],
  methods: {
    updateExpense(patch) {
      this.$emit("update-expense", patch);
    },
    updateText(field, value) {
      this.updateExpense({ [field]: value.trimStart() });
    },
    updateNumber(field, value) {
      this.updateExpense({ [field]: value === "" ? null : Number(value) });
    },
    toggleSplitMember(memberId, checked) {
      const memberIds = checked
        ? [...new Set([...this.expense.split_member_ids, memberId])]
        : this.expense.split_member_ids.filter((id) => id !== memberId);
      this.updateExpense({ split_member_ids: memberIds });
    },
    updateSplitAllocation(memberId, value) {
      this.updateExpense({
        split_allocations: {
          ...this.expense.split_allocations,
          [memberId]: value === "" ? 0 : Number(value),
        },
      });
    },
    formatMoney(amount, currency) {
      const minorUnit = ["TWD", "JPY", "KRW"].includes(currency) ? 0 : 2;
      return `${currency} ${Number(amount || 0).toLocaleString("zh-TW", {
        minimumFractionDigits: minorUnit,
        maximumFractionDigits: minorUnit,
      })}`;
    },
  },
};
</script>

<style scoped>
.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  color: #334155;
}

.section-title h3 {
  margin: 0;
  letter-spacing: 0;
}

.section-title svg,
.primary-action svg {
  width: 18px;
  height: 18px;
}

.expense-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
  color: #475569;
  font-size: 0.9rem;
  font-weight: 700;
}

input,
select {
  box-sizing: border-box;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  min-height: 42px;
  padding: 8px 10px;
  color: #111827;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 1rem;
}

input[type="date"] {
  appearance: none;
  -webkit-appearance: none;
  line-height: 1.2;
}

input[type="date"]::-webkit-date-and-time-value {
  min-height: 1.2em;
  text-align: left;
}

input[type="date"]::-webkit-calendar-picker-indicator {
  margin: 0;
}

select:disabled,
input:disabled {
  color: #94a3b8;
  background: #f1f5f9;
  cursor: not-allowed;
}

.full-row {
  grid-column: 1 / -1;
}

.quick-currency-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.quick-currency-row button,
.advanced-toggle {
  min-height: 36px;
  padding: 0 12px;
  color: #475569;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  box-shadow: none;
}

.quick-currency-row button.active {
  color: #ffffff;
  background: #0f766e;
  border-color: #0f766e;
}

.advanced-toggle {
  width: 100%;
  color: #0f766e;
  background: #f0fdfa;
  border-color: #99f6e4;
  font-weight: 800;
}

.advanced-expense-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.account-link-hint {
  margin: -4px 0 0;
  padding: 10px 12px;
  color: #475569;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.88rem;
  font-weight: 700;
}

.expense-preview {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.expense-preview > div {
  display: grid;
  gap: 4px;
  padding: 10px 12px;
  color: #134e4a;
  background: #f0fdfa;
  border: 1px solid #99f6e4;
  border-radius: 8px;
}

.expense-preview span {
  color: #0f766e;
  font-size: 0.82rem;
  font-weight: 800;
}

.expense-preview strong {
  font-size: 1rem;
  line-height: 1.35;
}

.split-box {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  padding: 12px;
  color: #475569;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-weight: 700;
}

.split-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  width: 100%;
}

.split-mode-tabs {
  display: inline-grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
  padding: 4px;
  background: #e2e8f0;
  border-radius: 8px;
}

.split-mode-tabs button {
  min-height: 34px;
  padding: 0 14px;
  color: #475569;
  background: transparent;
  border: 0;
  border-radius: 6px;
  box-shadow: none;
  font-weight: 800;
}

.split-mode-tabs button.active {
  color: #0f766e;
  background: #ffffff;
}

.split-member-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-height: 42px;
  padding: 8px 10px;
  color: #334155;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  box-shadow: none;
}

.split-member-toggle span,
.split-member-toggle strong {
  font-size: 0.88rem;
}

.split-member-toggle strong {
  color: #0f766e;
}

.split-member-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  width: 100%;
}

.split-option {
  flex-direction: row;
  align-items: center;
  width: auto;
  min-height: 34px;
  padding: 6px 10px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-weight: 600;
}

.split-option input {
  width: 16px;
  min-height: 16px;
}

.split-option:has(input:checked) {
  color: #0f766e;
  background: #ecfdf5;
  border-color: #99f6e4;
}

.custom-split-list {
  display: grid;
  gap: 8px;
  width: 100%;
}

.custom-split-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 140px;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.custom-split-row input {
  min-height: 36px;
}

.custom-split-summary {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  color: #0f766e;
  background: #ecfdf5;
  border: 1px solid #99f6e4;
  border-radius: 8px;
}

.custom-split-summary.invalid {
  color: #b45309;
  background: #fffbeb;
  border-color: #fde68a;
}

.primary-action,
.quiet-action {
  min-height: 42px;
  padding: 0 14px;
  border: 0;
  border-radius: 8px;
  box-shadow: none;
  font-weight: 800;
}

.primary-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: #ffffff;
  background: #0f766e;
}

.quiet-action {
  color: #334155;
  background: #e2e8f0;
}

.status-message {
  margin: 12px 0 0;
  color: #475569;
}

@media (max-width: 820px) {
  .expense-form,
  .advanced-expense-grid,
  .expense-preview {
    grid-template-columns: 1fr;
  }

  .split-header,
  .custom-split-summary {
    align-items: stretch;
    flex-direction: column;
  }

  .split-mode-tabs,
  .custom-split-row {
    width: 100%;
  }

  .custom-split-row {
    grid-template-columns: 1fr;
  }
}
</style>
