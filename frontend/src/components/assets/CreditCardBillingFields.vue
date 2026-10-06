<template>
  <fieldset class="billing-fields">
    <legend>信用卡帳期</legend>
    <label class="enable-row">
      <input type="checkbox" :checked="Boolean(modelValue)" @change="toggle" />
      顯示結帳與繳款日期
    </label>

    <template v-if="modelValue">
      <div class="field-grid">
        <label>
          每月結帳日
          <select :value="modelValue.closing_day ?? ''" required @change="setField('closing_day', $event)">
            <option value="" disabled>請選擇</option>
            <option v-for="day in 31" :key="day" :value="day">{{ day }} 日</option>
          </select>
        </label>
        <label>
          每月繳款日
          <select :value="modelValue.due_day ?? ''" required @change="setField('due_day', $event)">
            <option value="" disabled>請選擇</option>
            <option v-for="day in 31" :key="day" :value="day">{{ day }} 日</option>
          </select>
        </label>
      </div>
      <label>
        繳款月份
        <select :value="modelValue.due_month_offset" @change="setField('due_month_offset', $event)">
          <option :value="0">結帳當月</option>
          <option :value="1">結帳次月</option>
        </select>
      </label>
      <small>若該月沒有設定的日期，會以當月最後一天計算。規則推算的日期僅供提醒，請以銀行帳單為準。</small>

      <label v-if="allowOverride && nextDueClosingDate">
        本期實際繳款截止日（選填）
        <input
          type="date"
          :value="modelValue.override_due_date || ''"
          :min="nextDueClosingDate"
          @input="setOverride($event.target.value)"
        />
        <small>對應 {{ nextDueClosingDate }} 結帳週期；留空即使用預計日期。</small>
      </label>
      <small>此處只記錄日期，不追蹤本期應繳金額或是否已繳清。</small>
    </template>
  </fieldset>
</template>

<script>
export default {
  name: "CreditCardBillingFields",
  props: {
    modelValue: { type: Object, default: null },
    allowOverride: { type: Boolean, default: false },
    nextDueClosingDate: { type: String, default: "" },
  },
  emits: ["update:modelValue"],
  methods: {
    toggle(event) {
      this.$emit("update:modelValue", event.target.checked ? {
        closing_day: null,
        due_day: null,
        due_month_offset: 1,
        override_closing_date: null,
        override_due_date: null,
      } : null);
    },
    setField(name, event) {
      this.$emit("update:modelValue", {
        ...this.modelValue,
        [name]: Number(event.target.value),
        override_closing_date: null,
        override_due_date: null,
      });
    },
    setOverride(value) {
      this.$emit("update:modelValue", {
        ...this.modelValue,
        override_closing_date: value ? this.nextDueClosingDate : null,
        override_due_date: value || null,
      });
    },
  },
};
</script>

<style scoped>
.billing-fields {
  display: grid;
  gap: 12px;
  min-width: 0;
  padding: 14px;
  border: 1px solid var(--border-color);
  border-radius: 10px;
}

.billing-fields legend { font-weight: 700; color: var(--text-color); }
.billing-fields label { display: grid; gap: 6px; font-weight: 600; color: var(--light-text-color); }
.billing-fields .enable-row { display: flex; align-items: center; gap: 8px; }
.billing-fields .enable-row input { min-height: auto; width: auto; }
.billing-fields .field-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.billing-fields select, .billing-fields input[type="date"] {
  min-width: 0;
  min-height: 44px;
  padding: 8px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: white;
}
.billing-fields small { font-weight: 400; line-height: 1.5; color: var(--light-text-color); }
</style>
