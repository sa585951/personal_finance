<template>
  <div class="form-container">
    <h3>帳戶間轉帳</h3>
    <form @submit.prevent="handleTransfer">
      <div class="transfer-fields">
        <div class="field">
          <label for="sourceAccount">轉出帳戶:</label>
          <select id="sourceAccount" v-model="transferData.source_id" required>
            <option value="" disabled>請選擇帳戶</option>
            <option v-for="(asset, key) in assets" :key="key" :value="key">
              {{ asset.bank_name }} - {{ asset.account_type }} (${{
                asset.balance.toLocaleString()
              }})
            </option>
          </select>
        </div>

        <div class="field">
          <label for="destAccount">轉入帳戶:</label>
          <select id="destAccount" v-model="transferData.dest_id" required>
            <option value="" disabled>請選擇帳戶</option>
            <option v-for="(asset, key) in assets" :key="key" :value="key">
              {{ asset.bank_name }} - {{ asset.account_type }} (${{
                asset.balance.toLocaleString()
              }})
            </option>
          </select>
        </div>

        <div class="field">
          <label for="amount">轉帳金額:</label>
          <input
            type="number"
            id="amount"
            v-model.number="transferData.amount"
            placeholder="請輸入金額"
            required
          />
        </div>
      </div>
      <button type="submit" class="confirm-btn" style="margin-top: 10px;">確認轉帳</button>
    </form>
  </div>
</template>

<script>
import apiClient from "../../api";

export default {
  name: "TransferForm",
  props: {
    assets: {
      type: Object,
      required: true,
    },
  },
  emits: ["transfer-success"],
  data() {
    return {
      transferData: {
        source_id: "",
        dest_id: "",
        amount: null,
      },
    };
  },
  methods: {
    async handleTransfer() {
      if (this.transferData.source_id === this.transferData.dest_id) {
        alert("轉出和轉入帳戶不能是同一個！");
        return;
      }
      if (this.transferData.amount <= 0) {
        alert("轉帳金額必須大於0！");
        return;
      }

      try {
        const response = await apiClient.post(`/api/transfer`, {
          source_id: this.transferData.source_id,
          dest_id: this.transferData.dest_id,
          amount: this.transferData.amount,
        });

        alert(response.data.message);
        this.$emit("transfer-success");
        this.resetTransferForm();
      } catch (error) {
        alert(error.response?.data?.message || "轉帳失敗，請稍後再試。");
        console.error("轉帳失敗:", error);
      }
    },
    resetTransferForm() {
      this.transferData = {
        source_id: "",
        dest_id: "",
        amount: null,
      };
    },
  },
};
</script>

<style scoped>
/* 將轉帳表單的樣式複製到這裡 */
.form-container {
  margin-top: 2rem;
  padding: 1.5rem;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  background-color: var(--secondary-color);
}
.form-container h3 {
  margin-top: 0;
  color: var(--light-text-color);
}
.transfer-fields {
  display: flex;
  justify-content: space-around;
  gap: 1.5rem;
}
.field {
  flex: 1;
}
.field label {
  display: block;
  font-weight: bold;
  color: var(--light-text-color);
  margin-bottom: 0.5rem;
}
.field select,
.field input {
  width: 100%;
  padding: 0.8rem 1rem;
  border: 1px solid #ccc;
  border-radius: 6px;
  transition: all 0.3s ease;
}
</style>
