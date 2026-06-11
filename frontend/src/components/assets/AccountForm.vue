<template>
  <div class="account-form">
    <form @submit.prevent="addAccount">
      <div class="form-group">
        <label for="bankName">帳戶名稱</label>
        <input
          type="text"
          id="bankName"
          v-model.trim="newAccount.bank_name"
          placeholder="例如：台幣銀行、日幣現金"
          required
        />
      </div>

      <div class="form-group">
        <label for="accountType">帳戶類型</label>
        <select id="accountType" v-model="newAccount.account_type" required>
          <option
            v-for="type in accountTypes"
            :key="type.value"
            :value="type.value"
          >
            {{ type.label }}
          </option>
        </select>
      </div>

      <div class="form-group">
        <label for="balance">初始餘額</label>
        <input
          type="number"
          id="balance"
          v-model.number="newAccount.balance"
          :min="newAccount.account_type === 'credit_card' ? null : 0"
          step="1"
          placeholder="0"
          required
        />
      </div>

      <div class="form-group">
        <label for="currency">幣別</label>
        <select id="currency" v-model="newAccount.currency" required>
          <option
            v-for="currency in currencies"
            :key="currency"
            :value="currency"
          >
            {{ currency }}
          </option>
        </select>
      </div>

      <button type="submit">新增</button>
    </form>
    <div v-if="submitMessage" class="message">{{ submitMessage }}</div>
  </div>
</template>

<script>
import apiClient from "../../api";

export default {
  name: "AccountForm",
  data() {
    return {
      newAccount: {
        bank_name: "",
        account_type: "bank",
        balance: null,
        currency: "TWD",
      },
      currencies: ["TWD", "JPY", "KRW", "USD", "EUR"],
      accountTypes: [
        { value: "bank", label: "銀行" },
        { value: "cash", label: "現金" },
        { value: "credit_card", label: "信用卡" },
        { value: "e_wallet", label: "電子錢包" },
        { value: "prepaid_card", label: "預付卡" },
        { value: "external", label: "外部帳戶" },
        { value: "investment", label: "投資" },
        { value: "other", label: "其他" },
      ],
      submitMessage: "",
    };
  },
  methods: {
    async addAccount() {
      try {
        const payload = {
          bank_name: this.newAccount.bank_name,
          account_type: this.newAccount.account_type,
          balance: this.newAccount.balance,
          currency: this.newAccount.currency,
        };

        const response = await apiClient.post(`/api/assets`, payload);
        this.submitMessage = response.data.message;

        this.$emit("account-added");

        this.newAccount.bank_name = "";
        this.newAccount.account_type = "bank";
        this.newAccount.balance = null;
        this.newAccount.currency = "TWD";
      } catch (err) {
        if (err.response) {
          this.submitMessage = `新增失敗：${err.response.data.message}`;
        } else {
          this.submitMessage = "無法連接到後端伺服器。";
        }
      }
    },
  },
};
</script>
<style scoped>
.account-form form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-weight: bold;
  color: #475569;
}

.form-group input,
.form-group select {
  min-height: 44px;
  width: 100%;
  padding: 0.8rem 1rem;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  transition: all 0.3s ease;
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2);
}

.account-form button {
  min-height: 46px;
  margin-top: 4px;
  background-color: #0f766e;
}

.message {
  margin-top: 1rem;
  padding: 1rem;
  border-radius: 6px;
  font-weight: bold;
  background-color: #e8f5e9;
  color: #2e7d32;
  text-align: center;
}
</style>
