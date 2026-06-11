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
      <label for="transactionDate">
        日期
        <input
          type="date"
          id="transactionDate"
          v-model="newTransaction.date"
          required
        />
      </label>

      <label for="budgetCategory">
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

      <label for="transactionCategory">
        項目
        <input
          type="text"
          id="transactionCategory"
          :placeholder="type === 'income' ? '薪資、報銷、利息' : '午餐、捷運、訂閱'"
          v-model="newTransaction.item"
          required
        />
      </label>

      <label for="transactionAmount">
        金額
        <input
          type="number"
          id="transactionAmount"
          v-model.number="newTransaction.amount"
          required
        />
      </label>

      <label for="transactionAccount">
        帳戶
        <select id="transactionAccount" v-model="newTransaction.account_id">
          <option value="">不連動帳戶</option>
          <option
            v-for="account in accountOptions"
            :key="account.id"
            :value="account.id"
          >
            {{ account.label }}
          </option>
        </select>
      </label>

      <label for="transactionDescription" class="full-row">
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

      <p v-if="submitMessage" class="form-message full-row">{{ submitMessage }}</p>

      <button type="submit">{{ submitButtonText }}</button>
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
        parse_event_id: "",
        description: "", // 新增：備註
      },
      budgetCategories: [],
      assets: {},
      submitMessage: "",
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
      return this.type === "income" ? "新增收入" : "新增支出";
    },
    submitButtonText() {
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
        .filter((asset) => asset.currency === "TWD")
        .map((asset) => ({
          id: asset.id,
          label: `${asset.bank_name} - ${this.translateAccountType(asset.account_type)} (${asset.currency} ${Number(asset.balance || 0).toLocaleString()})`,
        }));
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
        this.ensureCategoryMatchesType();
      }
    },
    budgetCategories() {
      this.ensureCategoryMatchesType();
    },
    draft: {
      handler(value) {
        if (value && !this.isEditing) {
          this.applyDraft(value);
        }
      },
      deep: true,
    },
    editingTransaction: {
      handler(value, oldValue) {
        if (value) {
          this.applyEditingTransaction(value);
        } else if (oldValue) {
          this.resetForm();
        }
      },
      deep: true,
    },
  },
  methods: {
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
    applyDraft(draft) {
      const transactionType = ["expense", "income"].includes(draft.type)
        ? draft.type
        : this.type;
      const amount = draft.amount === null || draft.amount === undefined
        ? null
        : Number(draft.amount);

      this.newTransaction = {
        ...this.newTransaction,
        type: transactionType,
        item: draft.title || this.newTransaction.item,
        amount: Number.isFinite(amount) ? amount : this.newTransaction.amount,
        budget_category: draft.budget_category || this.newTransaction.budget_category,
        description: draft.description || "",
        account_id: this.findAccountIdByHint(draft.account_hint) || this.newTransaction.account_id,
        parse_event_id: draft.parse_event_id || "",
      };
      this.ensureCategoryMatchesType();
      this.submitMessage = "已套用 AI 解析結果，送出前請再確認欄位。";
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
        parse_event_id: "",
        description: transaction.description || "",
      };
      this.ensureCategoryMatchesType();
      this.submitMessage = "正在編輯既有交易，更新後會同步重算帳戶餘額。";
    },
    async submitTransaction() {
      this.submitMessage = "";
      try {
        if (this.isEditing) {
          await apiClient.put(
            `/api/transactions/${this.editingTransaction.id}`,
            this.newTransaction
          );
          await this.fetchAssets();
          this.$emit("transaction-updated");
          this.resetForm();
          this.$swal.fire("更新成功", "交易已成功更新。", "success");
          return;
        }

        await apiClient.post(`/api/transactions`, this.newTransaction);

        await this.fetchAssets();
        this.$emit("transaction-added");
        this.resetForm();
      } catch (error) {
        console.error(this.isEditing ? "更新失敗:" : "新增失敗:", error);
        this.$swal.fire(
          this.isEditing ? "更新失敗" : "新增失敗",
          error.response?.data?.message || "交易儲存失敗，請稍後再試。",
          "error"
        );
      }
    },
    async fetchBudgetCategories() {
      try {
        const response = await apiClient.get(`/api/budgets/categories?include_meta=true`);
        this.budgetCategories = response.data.data || [];
      } catch (error) {
        console.error("無法載入預算類別:", error);
      }
    },
    async fetchAssets() {
      try {
        const response = await apiClient.get(`/api/assets`);
        this.assets = response.data.data || {};
      } catch (error) {
        console.error("無法載入帳戶資料:", error);
        this.assets = {};
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
    findAccountIdByHint(accountHint) {
      if (!accountHint) return "";
      const normalizedHint = String(accountHint).trim().toLowerCase();
      const matchedAccount = Object.values(this.assets || {}).find((asset) => {
        if (asset.currency !== "TWD") return false;
        const bankName = String(asset.bank_name || "").toLowerCase();
        const accountType = this.translateAccountType(asset.account_type).toLowerCase();
        return (
          normalizedHint.includes(bankName)
          || bankName.includes(normalizedHint)
          || normalizedHint.includes(accountType)
        );
      });
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
        parse_event_id: "",
        description: "",
      };
      this.submitMessage = "";
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
}
</style>
