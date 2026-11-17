<template>
  <div class="recurring-page">
    <h1>固定收支</h1>
    <p class="intro">每月固定的房租、訂閱、薪水。到期時會先列在「待確認」，由你確認後才會入帳。</p>

    <AppStatePanel v-if="loading" title="讀取中" loading />
    <AppStatePanel v-else-if="loadError" title="暫時無法載入" :message="loadError" action-label="重新整理" tone="error" @action="load" />

    <template v-else>
      <section v-if="pending.length" aria-labelledby="pending-title" class="block">
        <h2 id="pending-title">待確認</h2>
        <RecurringPendingList :items="pending" @changed="load" />
      </section>

      <section class="block" aria-labelledby="rules-title">
        <div class="block-head">
          <h2 id="rules-title">我的固定收支</h2>
          <button v-if="!formOpen" type="button" class="app-button app-button--primary" @click="openForm()">＋ 新增</button>
        </div>

        <form v-if="formOpen" class="rule-form app-card" @submit.prevent="save">
          <h3>{{ editingId ? "編輯固定收支" : "新增固定收支" }}</h3>
          <div class="segmented" role="group" aria-label="類型">
            <button type="button" :class="{ on: form.type === 'expense' }" @click="setType('expense')">支出</button>
            <button type="button" :class="{ on: form.type === 'income' }" @click="setType('income')">收入</button>
          </div>
          <label>項目
            <input v-model.trim="form.title" maxlength="100" required placeholder="例如：房租、Netflix、薪水" />
          </label>
          <label>金額（NT$）
            <input v-model="form.amount" type="number" min="0" step="any" inputmode="decimal" required />
          </label>
          <label>分類
            <select v-model="form.budget_category" required>
              <option value="" disabled>選擇分類</option>
              <option v-for="name in categoryNames" :key="name" :value="name">{{ name }}</option>
            </select>
          </label>
          <label>帳戶
            <select v-model="form.account_id">
              <option value="">不指定帳戶</option>
              <option v-for="account in accounts" :key="account.id" :value="account.id">{{ account.bank_name }}</option>
            </select>
            <small>固定收支目前只支援台幣帳戶。</small>
          </label>
          <label>每月幾號
            <input v-model.number="form.day_of_month" type="number" min="1" max="31" required />
            <small>當月沒有這一天時（例如 31 號遇到 2 月），會用當月最後一天。</small>
          </label>
          <label>開始日
            <input v-model="form.start_date" type="date" required />
          </label>
          <label>結束日（可不填）
            <input v-model="form.end_date" type="date" :min="form.start_date" />
          </label>
          <label>備註（可不填）
            <input v-model.trim="form.description" maxlength="200" />
          </label>
          <p v-if="formError" class="app-notice app-notice--error">{{ formError }}</p>
          <div class="form-actions">
            <button type="submit" class="app-button app-button--primary" :disabled="saving">{{ saving ? "儲存中" : "儲存" }}</button>
            <button type="button" class="app-button" :disabled="saving" @click="closeForm">取消</button>
          </div>
        </form>

        <p v-if="!rules.length && !formOpen" class="empty">
          還沒有固定收支。新增後，每月到期會提醒你確認，不需要每個月重新輸入。
        </p>

        <ul v-if="rules.length" class="rule-list">
          <li v-for="rule in rules" :key="rule.id" class="rule-row" :class="{ paused: !rule.is_active }">
            <div class="rule-main">
              <strong>{{ rule.title }}</strong>
              <small>
                每月 {{ rule.day_of_month }} 號 · {{ rule.budget_category }}<template v-if="rule.account_name"> · {{ rule.account_name }}</template>
              </small>
              <small>{{ statusLine(rule) }}</small>
            </div>
            <span class="rule-amount" :class="rule.type">{{ rule.type === "income" ? "+" : "−" }}{{ formatAmount(rule.amount) }}</span>
            <div class="rule-actions">
              <button type="button" class="app-button app-button--text" @click="openForm(rule)">編輯</button>
              <button type="button" class="app-button app-button--text" @click="toggle(rule)">{{ rule.is_active ? "暫停" : "恢復" }}</button>
              <button type="button" class="app-button app-button--text" @click="remove(rule)">刪除</button>
            </div>
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>

<script>
import apiClient from "@/api";
import AppStatePanel from "@/components/shared/AppStatePanel.vue";
import RecurringPendingList from "@/components/recurring/RecurringPendingList.vue";
import { formatAmount, localDateKey } from "@/utils/money";

function blankForm() {
  return {
    type: "expense", title: "", amount: "", budget_category: "", account_id: "",
    day_of_month: Number(localDateKey().slice(8)), start_date: localDateKey(), end_date: "", description: "",
  };
}

export default {
  name: "RecurringView",
  components: { AppStatePanel, RecurringPendingList },
  data() {
    return {
      loading: true,
      loadError: "",
      rules: [],
      pending: [],
      categories: [],
      accounts: [],
      formOpen: false,
      editingId: "",
      form: blankForm(),
      formError: "",
      saving: false,
    };
  },
  computed: {
    categoryNames() {
      return this.categories.filter((c) => c.kind === this.form.type || c.kind === "both").map((c) => c.name);
    },
  },
  async mounted() {
    await this.load();
    if (this.$route.query.new && !this.loadError) this.openForm();
  },
  methods: {
    formatAmount,
    async load() {
      this.loadError = "";
      try {
        const [recurring, categories, assets] = await Promise.all([
          apiClient.get("/api/recurring"),
          apiClient.get("/api/budgets/categories", { params: { include_meta: true } }),
          apiClient.get("/api/assets"),
        ]);
        this.rules = recurring.data?.data?.rules || [];
        this.pending = recurring.data?.data?.pending || [];
        this.categories = categories.data?.data || [];
        this.accounts = Object.values(assets.data?.data || {}).filter((a) => a.currency === "TWD");
      } catch (error) {
        this.loadError = error.response?.data?.message || "請確認網路連線後重試。";
      } finally {
        this.loading = false;
      }
    },
    statusLine(rule) {
      if (!rule.is_active) return "已暫停，不會產生新的待確認";
      const end = rule.end_date ? `，到 ${rule.end_date} 為止` : "";
      return rule.next_due ? `下次 ${rule.next_due}${end}` : `已結束${end}`;
    },
    setType(type) {
      this.form.type = type;
      if (!this.categoryNames.includes(this.form.budget_category)) this.form.budget_category = "";
    },
    openForm(rule) {
      this.formError = "";
      this.editingId = rule?.id || "";
      this.form = rule
        ? {
          type: rule.type, title: rule.title, amount: rule.amount, budget_category: rule.budget_category,
          account_id: rule.account_id || "", day_of_month: rule.day_of_month, start_date: rule.start_date,
          end_date: rule.end_date || "", description: rule.description || "",
        }
        : blankForm();
      this.formOpen = true;
    },
    closeForm() {
      this.formOpen = false;
      this.editingId = "";
      if (this.$route.query.new) this.$router.replace({ path: "/recurring" });
    },
    async save() {
      this.saving = true;
      this.formError = "";
      const payload = { ...this.form, account_id: this.form.account_id || null, end_date: this.form.end_date || null };
      try {
        if (this.editingId) await apiClient.put(`/api/recurring/rules/${this.editingId}`, payload);
        else await apiClient.post("/api/recurring/rules", payload);
        this.closeForm();
        await this.load();
      } catch (error) {
        this.formError = error.response?.data?.message || "儲存失敗，請稍後再試。";
      } finally {
        this.saving = false;
      }
    },
    async toggle(rule) {
      try {
        await apiClient.put(`/api/recurring/rules/${rule.id}`, { is_active: !rule.is_active });
        await this.load();
      } catch (error) {
        this.$swal.fire("無法更新", error.response?.data?.message || "請稍後再試。", "error");
      }
    },
    async remove(rule) {
      const result = await this.$swal.fire({
        title: `刪除「${rule.title}」？`,
        text: "尚未確認的待確認項目會一起移除；已經入帳的紀錄不受影響。",
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "刪除",
        cancelButtonText: "取消",
      });
      if (!result.isConfirmed) return;
      try {
        await apiClient.delete(`/api/recurring/rules/${rule.id}`);
        await this.load();
      } catch (error) {
        this.$swal.fire("無法刪除", error.response?.data?.message || "請稍後再試。", "error");
      }
    },
  },
};
</script>

<style scoped>
.recurring-page {
  max-width: var(--compact-page-max-width);
  margin: 0 auto;
  padding: 24px 16px calc(var(--app-bottom-nav-height) + 24px);
  color: var(--text-color);
}

h1,
h2,
h3,
p {
  margin: 0;
}

.intro,
.empty {
  margin: 6px 0 20px;
  color: var(--light-text-color);
  line-height: 1.55;
}

.block {
  display: grid;
  gap: 12px;
  margin-bottom: 24px;
}

.block-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.rule-form {
  display: grid;
  gap: 14px;
  padding: 16px;
}

.rule-form label {
  display: grid;
  gap: 6px;
  font-weight: 600;
}

.rule-form small {
  color: var(--light-text-color);
  font-weight: 400;
}

.rule-form input,
.rule-form select {
  min-height: 44px;
  padding: 0 12px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-color);
  background: var(--card-bg);
  font: inherit;
}

.segmented {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
  padding: 4px;
  border-radius: 10px;
  background: var(--secondary-color);
}

.segmented button {
  min-height: 40px;
  border: 0;
  border-radius: 8px;
  color: var(--text-color);
  background: transparent;
  font-weight: 700;
  cursor: pointer;
}

.segmented button.on {
  color: var(--on-primary);
  background: var(--primary-color);
}

.form-actions {
  display: flex;
  gap: 8px;
}

.rule-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.rule-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 4px 12px;
  align-items: center;
  padding: 12px;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  background: var(--card-bg);
}

.rule-row.paused {
  opacity: 0.65;
}

.rule-main {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.rule-main small {
  color: var(--light-text-color);
}

.rule-amount {
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.rule-amount.expense {
  color: var(--expense-color);
}

.rule-amount.income {
  color: var(--income-color);
}

.rule-actions {
  display: flex;
  grid-column: 1 / -1;
  gap: 4px;
}
</style>
