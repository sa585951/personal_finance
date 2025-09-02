<template>
  <div class="form-container">
    <h3>新增帳戶</h3>
    <form @submit.prevent="addAccount">
      <label for="bankName">銀行名稱:</label>
      <input
        type="text"
        id="bankName"
        v-model="newAccount.bank_name"
        required
      />

      <label for="accountType">帳戶類型:</label>
      <input
        type="text"
        id="accountType"
        v-model="newAccount.account_type"
        required
      />

      <label for="balance">初始餘額:</label>
      <input
        type="number"
        id="balance"
        v-model.number="newAccount.balance"
        required
      />

      <button type="submit">新增</button>
    </form>
    <div v-if="submitMessage" class="message">{{ submitMessage }}</div>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "AccountForm",
  data() {
    return {
      newAccount: {
        bank_name: "",
        account_type: "",
        balance: null,
      },
      submitMessage: "",
    };
  },
  methods: {
    async addAccount() {
      try {
        const response = await axios.post("/api/assets", this.newAccount);
        this.submitMessage = response.data.message;

        await this.fetchAssets();

        this.newAccount.bank_name = "";
        this.newAccount.account_type = "";
        this.newAccount.balance = null;
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
.form-container {
  margin-bottom: 2rem;
  padding: 2rem;
  border: 1px solid #e0e0e0;
  border-radius: 10px;
  background-color: #fafafa;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.form-container h3 {
  margin-top: 0;
  color: var(--light-text-color);
}

.form-container form {
  display: grid;
  grid-template-columns: repeat(3, 1fr) auto;
  gap: 1.5rem;
  align-items: end;
}

.form-container label {
  font-weight: bold;
  color: var(--light-text-color);
  margin-bottom: 0.5rem;
}

.form-container input {
  padding: 0.8rem 1rem;
  border: 1px solid #ccc;
  border-radius: 6px;
  transition: all 0.3s ease;
}

.form-container input:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2);
}

.form-container button {
  background-color: var(--primary-color);
  justify-self: end;
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

button {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  color: white;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
}
</style>
