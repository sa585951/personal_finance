<template>
  <section class="account-activity">
    <div class="activity-heading">
      <strong>近期活動</strong>
      <small>核對支出、收入與帳戶互轉</small>
    </div>
    <div class="activity-filters" aria-label="帳戶活動篩選">
      <button
        v-for="filter in activityFilters"
        :key="filter.value"
        type="button"
        :class="{ active: activeFilter === filter.value }"
        :disabled="loading"
        @click="changeFilter(filter.value)"
      >
        {{ filter.label }}
      </button>
    </div>
    <p v-if="loading" class="activity-state">
      載入中...
    </p>
    <p v-else-if="error" class="activity-state error">
      {{ error }}
    </p>
    <p v-else-if="!activities.length" class="activity-state">
      {{ emptyMessage }}
    </p>
    <div v-else class="activity-list">
      <article
        v-for="activity in activities"
        :key="`${activity.type}-${activity.id}`"
        class="activity-item"
      >
        <div class="activity-main">
          <div>
            <strong>{{ activityTitle(activity) }}</strong>
            <span>{{ activitySubtitle(activity) }}</span>
          </div>
          <strong :class="activityAmountClass(activity)">
            {{ activityAmountText(activity) }}
          </strong>
        </div>
        <div class="activity-meta">
          <span>{{ formatDate(activity.date) }}</span>
          <span>{{ activityBadge(activity) }}</span>
          <span v-if="activity.trip_id">旅行</span>
        </div>
        <div
          v-if="activityActions(activity).length"
          class="activity-actions"
        >
          <button
            v-for="action in activityActions(activity)"
            :key="action.event"
            type="button"
            :class="{ danger: action.danger }"
            @click="$emit(action.event, activity)"
          >
            {{ action.label }}
          </button>
        </div>
      </article>
    </div>
    <div
      v-if="activities.length"
      class="activity-pagination"
    >
      <button
        type="button"
        :disabled="!pagination.has_prev || loading"
        @click="requestPage(pagination.page - 1)"
      >
        上一頁
      </button>
      <span>
        第 {{ pagination.page }} 頁
      </span>
      <button
        type="button"
        :disabled="!pagination.has_next || loading"
        @click="requestPage(pagination.page + 1)"
      >
        下一頁
      </button>
    </div>
  </section>
</template>

<script>
export default {
  name: "AccountActivityPanel",
  props: {
    activities: {
      type: Array,
      default: () => [],
    },
    error: {
      type: String,
      default: "",
    },
    loading: {
      type: Boolean,
      default: false,
    },
    activeFilter: {
      type: String,
      default: "all",
    },
    pagination: {
      type: Object,
      default: () => ({
        page: 1,
        limit: 10,
        has_next: false,
        has_prev: false,
      }),
    },
  },
  emits: [
    "filter-change",
    "page-change",
    "edit-transfer",
    "delete-transfer",
    "edit-transaction",
    "delete-transaction",
    "open-trip",
  ],
  computed: {
    activityFilters() {
      return [
        { value: "all", label: "全部" },
        { value: "income", label: "收入" },
        { value: "expense", label: "支出" },
        { value: "transfer", label: "轉帳" },
      ];
    },
    emptyMessage() {
      const messageMap = {
        income: "這個帳戶目前沒有收入紀錄，可用來核對薪資、退款或入帳。",
        expense: "這個帳戶目前沒有支出紀錄，可用來核對信用卡或付款帳戶。",
        transfer: "這個帳戶目前沒有轉帳紀錄，可用來核對儲蓄、投資或帳戶間資金流向。",
      };
      return messageMap[this.activeFilter] || "這個帳戶目前沒有近期活動。";
    },
  },
  methods: {
    changeFilter(filter) {
      if (filter === this.activeFilter || this.loading) return;
      this.$emit("filter-change", filter);
    },
    requestPage(page) {
      if (page < 1) return;
      this.$emit("page-change", page);
    },
    activityActions(activity) {
      if (activity.type === "transfer") {
        return [
          { event: "edit-transfer", label: "編輯" },
          { event: "delete-transfer", label: "刪除", danger: true },
        ];
      }
      if (activity.type !== "transaction") {
        return [];
      }
      if (activity.trip_id) {
        return [{ event: "open-trip", label: "前往旅行帳本" }];
      }

      const actions = [];
      if (activity.can_edit !== false) {
        actions.push({ event: "edit-transaction", label: "前往編輯" });
      }
      if (activity.can_delete !== false) {
        actions.push({ event: "delete-transaction", label: "刪除", danger: true });
      }
      return actions;
    },
    activityTitle(activity) {
      if (activity.type === "transfer") {
        return activity.direction === "out"
          ? `轉出至 ${activity.target_name}`
          : `由 ${activity.source_name} 轉入`;
      }
      return activity.title || activity.budget_category || "未命名交易";
    },
    activitySubtitle(activity) {
      if (activity.type === "transfer") {
        return activity.note || "帳戶互轉";
      }
      return activity.merchant || activity.description || activity.budget_category || "一般收支";
    },
    activityBadge(activity) {
      if (activity.type === "transfer") {
        return activity.direction === "out" ? "轉出" : "轉入";
      }
      return activity.transaction_type === "income" ? "收入" : "支出";
    },
    activityAmountClass(activity) {
      if (activity.type === "transfer") {
        return activity.direction === "out" ? "negative" : "positive";
      }
      return activity.transaction_type === "income" ? "positive" : "negative";
    },
    activityAmountText(activity) {
      const sign = this.activityAmountClass(activity) === "positive" ? "+" : "-";
      return `${sign}${this.formatMoney(activity.amount, activity.currency)}`;
    },
    formatMoney(amount, currency = "TWD") {
      const minorUnit = ["TWD", "JPY", "KRW"].includes(currency) ? 0 : 2;
      return `${currency} ${Number(amount || 0).toLocaleString("zh-TW", {
        minimumFractionDigits: minorUnit,
        maximumFractionDigits: minorUnit,
      })}`;
    },
    formatDate(dateValue) {
      if (!dateValue) return "";
      return String(dateValue).slice(0, 10);
    },
  },
};
</script>

<style scoped>
.account-activity {
  display: grid;
  gap: 10px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid #e2e8f0;
}

.activity-heading,
.activity-main,
.activity-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.activity-filters {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px;
  padding: 4px;
  background: #f1f5f9;
  border-radius: 8px;
}

.activity-filters button {
  min-height: 34px;
  padding: 0 8px;
  color: #475569;
  background: transparent;
  border: 0;
  border-radius: 6px;
  box-shadow: none;
  font-size: 0.82rem;
  font-weight: 900;
}

.activity-filters button.active {
  color: #0f766e;
  background: #ffffff;
}

.activity-filters button:hover {
  transform: none;
  box-shadow: none;
}

.activity-filters button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.activity-heading strong {
  color: #1f2933;
}

.activity-heading small,
.activity-state,
.activity-main span,
.activity-meta {
  color: #64748b;
  font-size: 0.84rem;
}

.activity-state {
  margin: 0;
}

.activity-state.error {
  color: #b91c1c;
}

.activity-list {
  display: grid;
  gap: 8px;
}

.activity-item {
  padding: 10px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
}

.activity-main div {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.activity-main strong:first-child,
.activity-main span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.activity-main .positive {
  color: #0f766e;
}

.activity-main .negative {
  color: #dc2626;
}

.activity-meta {
  justify-content: flex-start;
  flex-wrap: wrap;
  margin-top: 8px;
}

.activity-meta span {
  padding: 3px 7px;
  border-radius: 999px;
  background: #e2e8f0;
  color: #475569;
  font-size: 0.76rem;
  font-weight: 800;
}

.activity-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 10px;
}

.activity-actions button {
  min-height: 32px;
  padding: 0 10px;
  color: #334155;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  box-shadow: none;
  font-size: 0.82rem;
  font-weight: 800;
}

.activity-actions .danger {
  color: #b91c1c;
  border-color: #fecaca;
  background: #fef2f2;
}

.activity-pagination {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  gap: 8px;
}

.activity-pagination button {
  min-height: 38px;
  padding: 0 12px;
  color: #334155;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  box-shadow: none;
  font-size: 0.84rem;
  font-weight: 900;
}

.activity-pagination button:hover {
  transform: none;
  box-shadow: none;
}

.activity-pagination button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.activity-pagination span {
  color: #64748b;
  font-size: 0.82rem;
  font-weight: 800;
  white-space: nowrap;
}
</style>
