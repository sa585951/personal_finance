<template>
  <component
    :is="interactive ? 'button' : 'div'"
    :type="interactive ? 'button' : undefined"
    class="ledger-row"
    :class="{ interactive }"
    @click="interactive && $emit('select', transaction)"
  >
    <span class="ledger-row__main">
      <span class="ledger-row__title">{{ transaction.category || transaction.budget_category || "未命名" }}</span>
      <span class="ledger-row__meta">{{ meta }}</span>
    </span>
    <span class="ledger-row__amount" :class="transaction.type">
      {{ formatSigned(transaction.amount, transaction.type, transaction.currency) }}
      <small v-if="transaction.currency && transaction.currency !== 'TWD'">{{ transaction.currency }}</small>
    </span>
  </component>
</template>

<script>
import { formatSigned, friendlyDate } from "@/utils/money";

export default {
  name: "LedgerRow",
  props: {
    transaction: { type: Object, required: true },
    showDate: { type: Boolean, default: false },
    interactive: { type: Boolean, default: false },
  },
  emits: ["select"],
  computed: {
    meta() {
      const t = this.transaction;
      const parts = [];
      if (this.showDate) parts.push(friendlyDate(t.date));
      if (t.budget_category && t.budget_category !== t.category) parts.push(t.budget_category);
      parts.push(t.account_name || "不連動帳戶");
      if (t.trip_id) parts.push("旅行");
      if (t.description) parts.push(t.description);
      return parts.join(" · ");
    },
  },
  methods: { formatSigned },
};
</script>

<style scoped>
.ledger-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  min-height: 56px;
  padding: 10px 2px;
  border: 0;
  border-bottom: 1px solid var(--border-color);
  border-radius: 0;
  color: var(--text-color);
  background: transparent;
  font: inherit;
  text-align: left;
}

.ledger-row.interactive {
  cursor: pointer;
}

.ledger-row.interactive:hover {
  background: var(--secondary-color);
}

.ledger-row__main {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.ledger-row__title {
  font-weight: 600;
}

.ledger-row__meta {
  overflow: hidden;
  color: var(--light-text-color);
  font-size: 0.8rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ledger-row__amount {
  flex: none;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}

.ledger-row__amount.income {
  color: var(--income-color);
}

.ledger-row__amount small {
  margin-left: 3px;
  color: var(--light-text-color);
  font-size: 0.72rem;
  font-weight: 500;
}
</style>
