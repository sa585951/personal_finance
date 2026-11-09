<template>
  <div class="ledger-page">
    <header class="ledger-header">
      <h1>明細</h1>
      <select v-model="month" aria-label="月份" class="month-select" @change="load">
        <option v-for="option in monthOptions" :key="option" :value="option">{{ monthLabel(option) }}</option>
      </select>
    </header>

    <label class="search">
      <Search aria-hidden="true" />
      <span class="sr-only">搜尋</span>
      <input v-model.trim="query" type="search" placeholder="搜尋品項、類別、帳戶、備註" />
    </label>

    <div class="filters" role="radiogroup" aria-label="類型">
      <button
        v-for="option in typeOptions"
        :key="option.value"
        type="button"
        role="radio"
        class="chip"
        :aria-checked="type === option.value"
        :class="{ active: type === option.value }"
        @click="type = option.value"
      >{{ option.label }}</button>
    </div>

    <section v-if="editing" class="edit-panel" aria-label="編輯紀錄">
      <TransactionForm
        :key="editing.id"
        :type="editing.type"
        :editing-transaction="editing"
        @transaction-updated="afterChange"
        @edit-cancelled="editing = null"
      />
      <button type="button" class="delete-button" @click="remove(editing)">刪除這筆</button>
    </section>

    <AppStatePanel v-if="loading" title="讀取中" loading />
    <AppStatePanel
      v-else-if="loadError"
      title="明細暫時無法載入"
      :message="loadError"
      action-label="重試"
      tone="error"
      @action="load"
    />

    <section v-else class="records-section" aria-label="收支明細">
      <p class="totals">
        <span>收入 <strong class="income">+{{ formatAmount(totals.income) }}</strong></span>
        <span>支出 <strong>−{{ formatAmount(totals.expense) }}</strong></span>
      </p>

      <div v-for="group in groups" :key="group.date" class="day">
        <h2>{{ friendlyDate(group.date) }}</h2>
        <LedgerRow
          v-for="item in group.items"
          :key="item.id"
          :transaction="item"
          :interactive="item.can_edit !== false"
          @select="edit"
        />
      </div>

      <div v-if="!groups.length" class="empty">
        <p>{{ query ? `找不到「${query}」。` : "這個月還沒有紀錄。" }}</p>
        <router-link v-if="!query" to="/add" class="ink-button">記一筆</router-link>
      </div>
      <p v-if="truncated" class="caption">只顯示前 {{ items.length }} 筆，請縮小月份範圍。</p>
    </section>
  </div>
</template>

<script>
import { Search } from "@element-plus/icons-vue";
import apiClient from "@/api";
import AppStatePanel from "@/components/shared/AppStatePanel.vue";
import LedgerRow from "@/components/shared/LedgerRow.vue";
import TransactionForm from "@/components/budgets/TransactionForm.vue";
import { formatAmount, friendlyDate, localDateKey } from "@/utils/money";

const PAGE_SIZE = 50;
const MAX_PAGES = 10;

export default {
  name: "TransactionRecord",
  components: { AppStatePanel, LedgerRow, Search, TransactionForm },
  data() {
    const query = this.$route.query;
    const currentMonth = localDateKey().slice(0, 7);
    return {
      month: /^\d{4}-\d{2}$/.test(query.month || "") ? query.month : currentMonth,
      months: [currentMonth],
      type: ["expense", "income"].includes(query.type) ? query.type : "all",
      typeOptions: [
        { value: "all", label: "全部" },
        { value: "expense", label: "支出" },
        { value: "income", label: "收入" },
      ],
      query: "",
      items: [],
      truncated: false,
      loading: true,
      loadError: "",
      editing: null,
    };
  },
  computed: {
    monthOptions() {
      return [...new Set([this.month, ...this.months])].sort().reverse();
    },
    filtered() {
      const needle = this.query.toLowerCase();
      return this.items.filter((item) => {
        if (this.type !== "all" && item.type !== this.type) return false;
        if (!needle) return true;
        return [item.category, item.budget_category, item.account_name, item.description, item.merchant]
          .some((value) => String(value || "").toLowerCase().includes(needle));
      });
    },
    groups() {
      const byDate = new Map();
      for (const item of this.filtered) {
        if (!byDate.has(item.date)) byDate.set(item.date, []);
        byDate.get(item.date).push(item);
      }
      return [...byDate.entries()].map(([date, items]) => ({ date, items }));
    },
    totals() {
      const sum = (kind) => this.filtered
        .filter((item) => item.type === kind)
        .reduce((total, item) => total + Number(item.converted_amount ?? item.amount ?? 0), 0);
      return { income: sum("income"), expense: sum("expense") };
    },
  },
  mounted() {
    this.loadMonths();
    this.load();
  },
  methods: {
    formatAmount,
    friendlyDate,
    monthLabel(value) {
      const [year, month] = value.split("-");
      return `${year} 年 ${Number(month)} 月`;
    },
    async loadMonths() {
      try {
        const response = await apiClient.get("/api/months");
        this.months = response.data?.data || this.months;
      } catch {
        // The current month stays selectable without the list.
      }
    },
    async load() {
      this.loading = true;
      this.loadError = "";
      this.editing = null;
      try {
        const items = [];
        let cursor = null;
        let pages = 0;
        do {
          const response = await apiClient.get("/api/transactions", {
            params: { month: this.month, limit: PAGE_SIZE, ...(cursor ? { cursor } : {}) },
          });
          items.push(...(response.data?.data || []));
          const pagination = response.data?.pagination || {};
          cursor = pagination.has_more ? pagination.next_cursor : null;
          pages += 1;
        } while (cursor && pages < MAX_PAGES);
        this.items = items;
        this.truncated = Boolean(cursor);
      } catch (error) {
        this.loadError = error.response?.data?.message || "請確認網路連線後重試。";
      } finally {
        this.loading = false;
      }
    },
    edit(item) {
      this.editing = item;
      window.scrollTo({ top: 0, behavior: "smooth" });
    },
    async remove(item) {
      const label = `${item.category || item.budget_category}（${formatAmount(item.amount, item.currency)} ${item.currency || "TWD"}）`;
      const result = await this.$swal.fire({
        title: "刪除這筆紀錄？",
        text: `${label}會從明細移除，帳戶餘額會一併還原。`,
        showCancelButton: true,
        confirmButtonText: "刪除",
        cancelButtonText: "取消",
        reverseButtons: true,
      });
      if (!result.isConfirmed) return;
      try {
        await apiClient.delete(`/api/transactions/${item.id}`);
        await this.afterChange();
      } catch (error) {
        this.$swal.fire("刪除失敗", error.response?.data?.message || "請稍後再試。", "error");
      }
    },
    async afterChange() {
      this.editing = null;
      await this.load();
    },
  },
};
</script>

<style scoped>
.ledger-page {
  max-width: var(--compact-page-max-width);
  margin: 0 auto;
  padding: 20px 16px calc(var(--app-bottom-nav-height) + 24px);
  color: var(--text-color);
}

.ledger-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.ledger-header h1 {
  margin: 0;
  font-size: 1.5rem;
}

.month-select {
  min-height: 40px;
  padding: 0 10px;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  color: var(--text-color);
  background: var(--card-bg);
  font-weight: 600;
}

.search {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 44px;
  margin-bottom: 10px;
  padding: 0 12px;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  background: var(--card-bg);
}

.search svg {
  width: 16px;
  height: 16px;
  color: var(--light-text-color);
}

.search input {
  flex: 1;
  min-width: 0;
  border: 0;
  color: var(--text-color);
  background: transparent;
  outline: none;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
}

.filters {
  display: flex;
  gap: 6px;
  margin-bottom: 14px;
}

.chip {
  min-height: 34px;
  padding: 0 14px;
  border: 1px solid var(--border-color);
  border-radius: 999px;
  color: var(--light-text-color);
  background: transparent;
  font-weight: 600;
}

.chip.active {
  color: var(--on-primary);
  background: var(--primary-color);
  border-color: var(--primary-color);
}

.totals {
  display: flex;
  justify-content: space-between;
  margin: 0 0 8px;
  color: var(--light-text-color);
  font-size: 0.88rem;
}

.totals strong {
  color: var(--text-color);
  font-variant-numeric: tabular-nums;
}

.totals strong.income {
  color: var(--income-color);
}

.day h2 {
  margin: 18px 0 0;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border-color);
  color: var(--light-text-color);
  font-size: 0.82rem;
  font-weight: 600;
}

.edit-panel {
  margin-bottom: 16px;
}

.delete-button {
  min-height: 44px;
  padding: 0 16px;
  border: 1px solid var(--expense-color);
  border-radius: 10px;
  color: var(--expense-color);
  background: transparent;
  font-weight: 700;
}

.empty {
  display: grid;
  justify-items: start;
  gap: 12px;
  padding: 24px 0;
}

.empty p,
.caption {
  margin: 0;
  color: var(--light-text-color);
}

.ink-button {
  display: inline-flex;
  align-items: center;
  min-height: 44px;
  padding: 0 18px;
  border-radius: 10px;
  color: var(--on-primary);
  background: var(--primary-color);
  text-decoration: none;
  font-weight: 700;
}
</style>
