<template>
  <div class="form-container">
    <div class="form-heading">
      <h3>{{ formTitle }}</h3>
      <button
        v-if="isEditing"
        class="cancel-edit-btn"
        type="button"
        @click="cancelEdit"
      >
        取消編輯
      </button>
    </div>
    <form @submit.prevent="submitTransaction">
      <label v-if="shouldShowField('date')" for="transactionDate">
        日期
        <input
          type="date"
          id="transactionDate"
          v-model="newTransaction.date"
          required
        />
      </label>

      <label v-if="shouldShowField('budget_category')" for="budgetCategory">
        {{ categoryLabel }}
        <select
          id="budgetCategory"
          v-model="newTransaction.budget_category"
          required
        >
          <option disabled value="">請選擇預算類別</option>
          <option
            v-for="category in filteredBudgetCategories"
            :key="category.code"
            :value="category.name"
          >
            {{ category.name }}
          </option>
        </select>
      </label>

      <label v-if="shouldShowField('title')" for="transactionCategory">
        項目
        <input
          type="text"
          id="transactionCategory"
          :placeholder="type === 'income' ? '薪資、報銷、利息' : '午餐、捷運、訂閱'"
          v-model="newTransaction.item"
          required
        />
      </label>

      <label v-if="shouldShowField('amount')" for="transactionAmount">
        金額
        <input
          type="number"
          id="transactionAmount"
          v-model.number="newTransaction.amount"
          required
        />
      </label>

      <label v-if="shouldShowField('account_id')" for="transactionAccountSearch">
        搜尋帳戶
        <input
          type="search"
          id="transactionAccountSearch"
          v-model.trim="accountSearchText"
          placeholder="輸入銀行、信用卡、現金或帳戶名稱"
        />
      </label>

      <label v-if="shouldShowField('account_id')" for="transactionAccount">
        帳戶
        <select id="transactionAccount" v-model="newTransaction.account_id">
          <option value="">不連動帳戶</option>
          <optgroup
            v-for="group in groupedAccountOptions"
            :key="group.type"
            :label="group.label"
          >
            <option
              v-for="account in group.accounts"
              :key="account.id"
              :value="account.id"
            >
              {{ account.label }}
            </option>
          </optgroup>
        </select>
      </label>

      <label v-if="shouldShowField('description')" for="transactionDescription" class="full-row">
        備註
        <input
          type="text"
          id="transactionDescription"
          v-model="newTransaction.description"
        />
      </label>

      <div v-if="transactionPreview" class="transaction-preview full-row">
        <span>{{ type === "income" ? "入帳提示" : "扣款提示" }}</span>
        <strong>{{ transactionPreview }}</strong>
      </div>

      <div v-if="aiReview && mode === 'full'" class="ai-review full-row">
        <div class="ai-review-heading">
          <strong>AI 已套用，送出前請確認</strong>
          <span>{{ aiReview.type === "income" ? "收入" : "支出" }}</span>
        </div>
        <div class="ai-review-grid">
          <span>項目：{{ aiReview.title || "未判斷" }}</span>
          <span>金額：{{ aiReview.amount || "未判斷" }}</span>
          <span>備註：{{ aiReview.description || "無" }}</span>
          <span>幣別：{{ aiReview.currency || "預設" }}</span>
        </div>
        <p v-if="aiReview.accountHint && aiReview.accountMatched" class="ai-review-note">
          已依「{{ aiReview.accountHint }}」帶入帳戶。
        </p>
        <p v-else-if="aiReview.accountHint" class="ai-review-note warning">
          找不到「{{ aiReview.accountHint }}」對應帳戶，請手動選擇帳戶。
        </p>
        <p v-if="aiReview.switchedType" class="ai-review-note warning">
          已依解析結果切換為{{ aiReview.type === "income" ? "收入" : "支出" }}表單。
        </p>
      </div>

      <p v-if="submitMessage" class="form-message full-row">{{ submitMessage }}</p>

      <button type="submit" :disabled="isSubmitting">
        {{ isSubmitting ? "儲存中" : submitButtonText }}
      </button>
    </form>
  </div>
</template>

<script>
import apiClient from "@/api";
import { format } from "date-fns";

export default {
  name: "TransactionForm",
  props: {
    type: {
      type: String,
      default: "expense",
      validator: (value) => ["expense", "income"].includes(value),
    },
    draft: {
      type: Object,
      default: null,
    },
    editingTransaction: {
      type: Object,
      default: null,
    },
    mode: {
      type: String,
      default: "full",
      validator: (value) => ["full", "preview"].includes(value),
    },
    missingFields: {
      type: Array,
      default: () => [],
    },
    expanded: {
      type: Boolean,
      default: false,
    },
    clientRequestId: {
      type: String,
      default: "",
    },
    submitLabel: {
      type: String,
      default: "",
    },
  },
  emits: ["transaction-added", "transaction-updated", "edit-cancelled"],
  data() {
    return {
      newTransaction: {
        date: format(new Date(), "yyyy-MM-dd"), // 預設為當天日期
        type: this.type,
        item: "", // 將 category 改為 item
        amount: null,
        budget_category: "", // 新增：預算類別
        account_id: "",
        original_currency: "TWD",
        parse_event_id: "",
        description: "", // 新增：備註
      },
      budgetCategories: [],
      assets: {},
      budgetCategoriesLoaded: false,
      assetsLoaded: false,
      submitMessage: "",
      accountSearchText: "",
      aiReview: null,
      isSubmitting: false,
    };
  },
  computed: {
    isEditing() {
      return Boolean(this.editingTransaction?.id);
    },
    formTitle() {
      if (this.isEditing) {
        return this.type === "income" ? "編輯收入" : "編輯支出";
      }
      if (this.mode === "preview") {
        return this.type === "income" ? "確認收入" : "確認支出";
      }
      return this.type === "income" ? "新增收入" : "新增支出";
    },
    submitButtonText() {
      if (this.submitLabel) return this.submitLabel;
      if (this.isEditing) {
        return this.type === "income" ? "更新收入" : "更新支出";
      }
      return this.type === "income" ? "新增收入" : "新增支出";
    },
    categoryLabel() {
      return this.type === "income" ? "收入類別" : "支出類別";
    },
    filteredBudgetCategories() {
      return this.budgetCategories.filter(
        (category) => category.kind === this.type || category.kind === "both"
      );
    },
    accountOptions() {
      return Object.values(this.assets || {})
        .map((asset) => ({
          id: asset.id,
          type: asset.account_type || "other",
          bankName: asset.bank_name || "",
          currency: asset.currency || "TWD",
          label: `${asset.bank_name} - ${this.translateAccountType(asset.account_type)} (${asset.currency} ${Number(asset.balance || 0).toLocaleString()})`,
        }))
        .sort((a, b) => {
          const typeOrder = this.accountTypeOrder(a.type) - this.accountTypeOrder(b.type);
          if (typeOrder !== 0) return typeOrder;
          return a.bankName.localeCompare(b.bankName, "zh-TW");
        });
    },
    filteredAccountOptions() {
      const keyword = this.accountSearchText.toLowerCase();
      if (!keyword) return this.accountOptions;
      return this.accountOptions.filter((account) => {
        const searchableText = [
          account.bankName,
          account.type,
          this.translateAccountType(account.type),
          account.currency,
        ].join(" ").toLowerCase();
        return searchableText.includes(keyword);
      });
    },
    groupedAccountOptions() {
      return this.groupAccountsByType(this.filteredAccountOptions);
    },
    selectedAccount() {
      if (!this.newTransaction.account_id) return null;
      return Object.values(this.assets || {}).find(
        (asset) => asset.id === this.newTransaction.account_id
      ) || null;
    },
    transactionPreview() {
      const account = this.selectedAccount;
      const amount = Number(this.newTransaction.amount || 0);
      if (!amount) {
        return "";
      }
      if (!account) {
        return "不異動帳戶餘額";
      }
      const action = this.type === "income" ? "將入帳" : "將扣款";
      return `${action}：${account.bank_name} ${this.formatMoney(amount, account.currency)}`;
    },
  },
  watch: {
    type() {
      if (!this.isEditing) {
        this.newTransaction.type = this.type;
        if (!this.draft && this.budgetCategoriesLoaded) {
          this.ensureCategoryMatchesType();
        }
      }
    },
    "newTransaction.account_id"(accountId) {
      const account = Object.values(this.assets || {}).find((asset) => asset.id === accountId);
      if (account?.currency) {
        this.newTransaction.original_currency = account.currency;
      }
    },
    draft: {
      handler(value) {
        this.applyIncomingState();
      },
      immediate: true,
      deep: true,
    },
    editingTransaction: {
      handler(value, oldValue) {
        if (value) {
          this.applyIncomingState();
        } else if (oldValue) {
          this.resetForm();
        }
      },
      immediate: true,
      deep: true,
    },
  },
  methods: {
    shouldShowField(field) {
      if (this.isEditing || this.mode === "full" || this.expanded) return true;
      return this.missingFields.includes(field);
    },
    accountTypeOrder(type) {
      const order = ["bank", "cash", "credit_card", "e_wallet", "prepaid_card", "investment", "external", "other"];
      const index = order.indexOf(type);
      return index === -1 ? order.length : index;
    },
    groupAccountsByType(accounts) {
      const groups = [];
      for (const account of accounts) {
        let group = groups.find((item) => item.type === account.type);
        if (!group) {
          group = {
            type: account.type,
            label: this.translateAccountType(account.type),
            accounts: [],
          };
          groups.push(group);
        }
        group.accounts.push(account);
      }
      return groups;
    },
    ensureCategoryMatchesType() {
      if (
        this.filteredBudgetCategories.some(
          (category) => category.name === this.newTransaction.budget_category
        )
      ) {
        return;
      }
      this.newTransaction.budget_category = this.filteredBudgetCategories[0]?.name || "";
    },
    applyIncomingState() {
      if (!this.budgetCategoriesLoaded || !this.assetsLoaded) {
        return;
      }
      if (this.editingTransaction) {
        this.applyEditingTransaction(this.editingTransaction);
        return;
      }
      if (this.draft) {
        this.applyDraft(this.draft);
        return;
      }
      this.ensureCategoryMatchesType();
    },
    applyDraft(draft) {
      const transactionType = ["expense", "income"].includes(draft.type)
        ? draft.type
        : this.type;
      const amount = draft.amount === null || draft.amount === undefined
        ? null
        : Number(draft.amount);
      const matchedAccountId = this.findAccountIdByHint(draft.account_hint, draft.currency);

      this.newTransaction = {
        ...this.newTransaction,
        date: draft.date || this.newTransaction.date,
        type: transactionType,
        item: draft.title || this.newTransaction.item,
        amount: Number.isFinite(amount) ? amount : this.newTransaction.amount,
        budget_category: draft.budget_category || this.newTransaction.budget_category,
        description: draft.description || "",
        original_currency: draft.currency || this.newTransaction.original_currency,
        account_id: matchedAccountId || this.newTransaction.account_id,
        parse_event_id: draft.parse_event_id || "",
      };
      this.aiReview = {
        type: transactionType,
        title: draft.title || "",
        amount: Number.isFinite(amount) ? this.formatMoney(amount, draft.currency || this.newTransaction.original_currency) : "",
        description: draft.description || "",
        currency: draft.currency || "",
        accountHint: draft.account_hint || "",
        accountMatched: Boolean(draft.account_hint && matchedAccountId),
        switchedType: Boolean(draft.switchedType),
      };
      if (this.mode === "preview" && this.missingFields.includes("budget_category")) {
        this.newTransaction.budget_category = "";
      } else {
        this.ensureCategoryMatchesType();
      }
      this.submitMessage = draft.account_hint && !matchedAccountId
        ? "已套用 AI 解析結果，但帳戶需要手動確認。"
        : "已套用 AI 解析結果，送出前請再確認欄位。";
    },
    applyEditingTransaction(transaction) {
      this.newTransaction = {
        date: transaction.date || format(new Date(), "yyyy-MM-dd"),
        type: transaction.type || this.type,
        item: transaction.category || "",
        amount: transaction.amount === null || transaction.amount === undefined
          ? null
          : Number(transaction.amount),
        budget_category: transaction.budget_category || "",
        account_id: transaction.account_id || "",
        original_currency: transaction.currency || "TWD",
        parse_event_id: "",
        description: transaction.description || "",
      };
      this.ensureCategoryMatchesType();
      this.submitMessage = "正在編輯既有交易，更新後會同步重算帳戶餘額。";
      this.aiReview = null;
    },
    async submitTransaction() {
      if (this.isSubmitting) return;
      this.isSubmitting = true;
      this.submitMessage = "";
      try {
        if (this.isEditing) {
          await apiClient.put(
            `/api/transactions/${this.editingTransaction.id}`,
            this.transactionPayload()
          );
          await this.fetchAssets();
          this.$emit("transaction-updated");
          this.resetForm();
          this.$swal.fire("更新成功", "交易已成功更新。", "success");
          return;
        }

        const response = await apiClient.post(`/api/transactions`, this.transactionPayload());

        await this.fetchAssets();
        this.$emit("transaction-added", {
          type: this.type,
          transactionId: response.data?.data?.transaction_id || null,
          replayed: response.data?.replayed === true,
        });
        this.resetForm();
      } catch (error) {
        console.error(this.isEditing ? "更新失敗:" : "新增失敗:", error);
        this.$swal.fire(
          this.isEditing ? "更新失敗" : "新增失敗",
          error.response?.data?.message || "交易儲存失敗，請稍後再試。",
          "error"
        );
      } finally {
        this.isSubmitting = false;
      }
    },
    async fetchBudgetCategories() {
      try {
        const response = await apiClient.get(`/api/budgets/categories?include_meta=true`);
        this.budgetCategories = response.data.data || [];
        this.budgetCategoriesLoaded = true;
        this.applyIncomingState();
      } catch (error) {
        console.error("無法載入預算類別:", error);
        this.budgetCategoriesLoaded = true;
        this.applyIncomingState();
      }
    },
    async fetchAssets() {
      try {
        const response = await apiClient.get(`/api/assets`);
        this.assets = response.data.data || {};
        this.assetsLoaded = true;
        this.applyIncomingState();
      } catch (error) {
        console.error("無法載入帳戶資料:", error);
        this.assets = {};
        this.assetsLoaded = true;
        this.applyIncomingState();
      }
    },
    translateAccountType(type) {
      const typeMap = {
        bank: "銀行",
        cash: "現金",
        credit_card: "信用卡",
        e_wallet: "電子錢包",
        prepaid_card: "預付卡",
        external: "外部帳戶",
        investment: "投資",
        other: "其他",
      };
      return typeMap[type] || type || "其他";
    },
    transactionPayload() {
      const accountCurrency = this.selectedAccount?.currency;
      return {
        ...this.newTransaction,
        original_currency: accountCurrency || this.newTransaction.original_currency || "TWD",
        ...(this.isEditing || !this.clientRequestId
          ? {}
          : { client_request_id: this.clientRequestId }),
      };
    },
    findAccountIdByHint(accountHint, currencyHint = null) {
      if (!accountHint) return "";
      const normalizedHint = String(accountHint).trim().toLowerCase();
      const normalizedCurrency = currencyHint ? String(currencyHint).trim().toUpperCase() : "";
      const candidates = Object.values(this.assets || {}).filter((asset) => {
        const bankName = String(asset.bank_name || "").toLowerCase();
        const accountType = this.translateAccountType(asset.account_type).toLowerCase();
        return (
          normalizedHint.includes(bankName)
          || bankName.includes(normalizedHint)
          || normalizedHint.includes(accountType)
        );
      });
      const matchedAccount = candidates.find((asset) => asset.currency === normalizedCurrency) || candidates[0];
      return matchedAccount?.id || "";
    },
    formatMoney(amount, currency = "TWD") {
      const minorUnit = ["TWD", "JPY", "KRW"].includes(currency) ? 0 : 2;
      return `${currency} ${Number(amount || 0).toLocaleString("zh-TW", {
        minimumFractionDigits: minorUnit,
        maximumFractionDigits: minorUnit,
      })}`;
    },
    resetForm() {
      this.newTransaction = {
        date: format(new Date(), "yyyy-MM-dd"),
        type: this.type,
        item: "", // 將 category 改為 item
        amount: null,
        budget_category: "",
        account_id: "",
        original_currency: "TWD",
        parse_event_id: "",
        description: "",
      };
      this.submitMessage = "";
      this.aiReview = null;
    },
    cancelEdit() {
      this.resetForm();
      this.$emit("edit-cancelled");
    },
  },
  created() {
    this.fetchBudgetCategories();
    this.fetchAssets();
  },
};
</script>

<style scoped>
/* 表單容器樣式 - 與 AccountForm 一致 */
.form-container {
  margin-bottom: 1rem;
  padding: 16px;
  border: 1px solid #dbe4ee;
  border-radius: 10px;
  background-color: #ffffff;
  box-shadow: none;
}

.form-container h3 {
  margin-top: 0;
  color: #1f2933;
  margin-bottom: 1rem;
}

.form-container form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
  align-items: end;
}

.form-container label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
  font-weight: bold;
  color: #475569;
  text-align: left;
}

.form-container input,
.form-container select {
  box-sizing: border-box;
  min-height: 44px;
  min-width: 0;
  padding: 0.8rem 1rem;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  transition: all 0.3s ease;
  width: 100%;
  background-color: #fff;
}

.form-container input[type="date"] {
  appearance: none;
  -webkit-appearance: none;
  line-height: 1.2;
}

.form-container input[type="date"]::-webkit-date-and-time-value {
  min-height: 1.2em;
  text-align: left;
}

.form-container input[type="date"]::-webkit-calendar-picker-indicator {
  margin: 0;
}

.full-row {
  grid-column: 1 / -1;
}

.transaction-preview {
  display: grid;
  gap: 4px;
  min-height: 60px;
  padding: 12px;
  color: #134e4a;
  background: #f0fdfa;
  border: 1px solid #99f6e4;
  border-radius: 8px;
}

.transaction-preview span {
  color: #0f766e;
  font-size: 0.82rem;
  font-weight: 800;
}

.transaction-preview strong {
  line-height: 1.35;
}

.ai-review {
  padding: 12px;
  color: #1e3a8a;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
}

.ai-review-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.ai-review-heading span {
  flex: 0 0 auto;
  padding: 3px 8px;
  border-radius: 999px;
  background: #dbeafe;
  font-size: 0.78rem;
  font-weight: 800;
}

.ai-review-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px 10px;
  margin-top: 8px;
  color: #334155;
  font-size: 0.86rem;
  font-weight: 700;
}

.ai-review-grid span {
  min-width: 0;
  overflow-wrap: anywhere;
}

.ai-review-note {
  margin: 8px 0 0;
  color: #1d4ed8;
  font-size: 0.86rem;
  font-weight: 800;
}

.ai-review-note.warning {
  color: #b45309;
}

.form-message {
  margin: 0;
  padding: 10px 12px;
  color: #475569;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-weight: 700;
}

.form-container input:focus,
.form-container select:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2);
}

.form-container form > button[type="submit"] {
  min-height: 46px;
  background-color: #0f766e;
  grid-column: 1 / -1;
  width: auto;
  justify-self: stretch;
  margin-top: 1rem;
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  color: white;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.form-container form > button[type="submit"]:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
}

.form-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 1rem;
}

.form-heading h3 {
  margin: 0;
}

.cancel-edit-btn {
  min-height: 34px;
  padding: 0 10px;
  color: #475569;
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  box-shadow: none;
  font-weight: 800;
}

@media (max-width: 768px) {
  .form-container form {
    grid-template-columns: 1fr;
  }

  .form-container form > button[type="submit"] {
    width: 100%;
    justify-self: stretch;
  }

  .ai-review-grid {
    grid-template-columns: 1fr;
  }
}
</style>
