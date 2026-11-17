<template>
  <ul class="pending-list">
    <li v-for="item in items" :key="item.id" class="pending-row">
      <div class="pending-main">
        <strong>{{ item.title }}</strong>
        <small>{{ dueLabel(item.due_date) }}<template v-if="item.account_name"> · {{ item.account_name }}</template></small>
      </div>
      <span class="pending-amount" :class="item.type">{{ item.type === "income" ? "+" : "−" }}{{ formatAmount(item.amount) }}</span>
      <div class="pending-actions">
        <button type="button" class="app-button app-button--primary" :disabled="busyId === item.id" @click="confirm(item)">確認</button>
        <button type="button" class="app-button" :disabled="busyId === item.id" @click="confirmWithAmount(item)">改金額</button>
        <button type="button" class="app-button app-button--text" :disabled="busyId === item.id" @click="skip(item)">略過</button>
      </div>
    </li>
  </ul>
</template>

<script>
import apiClient from "@/api";
import { formatAmount } from "@/utils/money";

export default {
  name: "RecurringPendingList",
  props: { items: { type: Array, required: true } },
  emits: ["changed"],
  data() {
    return { busyId: "" };
  },
  methods: {
    formatAmount,
    dueLabel(date) {
      const [, month, day] = date.split("-");
      return `${Number(month)}/${Number(day)} 到期`;
    },
    async run(item, request, failure) {
      this.busyId = item.id;
      try {
        await request();
        this.$emit("changed");
      } catch (error) {
        this.$swal.fire(failure, error.response?.data?.message || "請稍後再試。", "error");
        this.$emit("changed"); // The item may already have been handled on another device.
      } finally {
        this.busyId = "";
      }
    },
    confirm(item, amount) {
      return this.run(
        item,
        () => apiClient.post(`/api/recurring/occurrences/${item.id}/confirm`, amount === undefined ? {} : { amount }),
        "無法確認",
      );
    },
    async confirmWithAmount(item) {
      const result = await this.$swal.fire({
        title: item.title,
        text: `${this.dueLabel(item.due_date)}，這個月實際金額是多少？`,
        input: "number",
        inputValue: item.amount,
        inputAttributes: { min: "0", step: "any", inputmode: "decimal" },
        showCancelButton: true,
        confirmButtonText: "確認入帳",
        cancelButtonText: "取消",
        inputValidator: (value) => (Number(value) > 0 ? undefined : "金額必須大於 0"),
      });
      if (result.isConfirmed) await this.confirm(item, result.value);
    },
    async skip(item) {
      const result = await this.$swal.fire({
        title: `略過這個月的「${item.title}」？`,
        text: "不會入帳，之後也不會再提醒這個月。",
        showCancelButton: true,
        confirmButtonText: "略過",
        cancelButtonText: "取消",
      });
      if (!result.isConfirmed) return;
      await this.run(item, () => apiClient.post(`/api/recurring/occurrences/${item.id}/skip`), "無法略過");
    },
  },
};
</script>

<style scoped>
.pending-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.pending-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px 12px;
  align-items: center;
  padding: 12px;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  background: var(--card-bg);
}

.pending-main {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.pending-main small {
  color: var(--light-text-color);
}

.pending-amount {
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.pending-amount.expense {
  color: var(--expense-color);
}

.pending-amount.income {
  color: var(--income-color);
}

.pending-actions {
  display: flex;
  flex-wrap: wrap;
  grid-column: 1 / -1;
  gap: 8px;
}
</style>
