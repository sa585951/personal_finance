<template>
  <div class="transfer-form">
    <p v-if="accountOptions.length < 2" class="empty-hint">
      至少需要兩個帳戶才能轉帳。
    </p>
    <form @submit.prevent="handleTransfer">
      <div class="transfer-fields">
        <div class="field">
          <label for="sourceAccount">轉出帳戶</label>
          <select id="sourceAccount" v-model="transferData.source_id" required>
            <option value="" disabled>請選擇帳戶</option>
            <option
              v-for="account in accountOptions"
              :key="account.key"
              :value="account.key"
            >
              {{ account.label }}
            </option>
          </select>
        </div>

        <div class="field">
          <label for="destAccount">轉入帳戶</label>
          <select id="destAccount" v-model="transferData.dest_id" required>
            <option value="" disabled>請選擇帳戶</option>
            <option
              v-for="account in accountOptions"
              :key="account.key"
              :value="account.key"
            >
              {{ account.label }}
            </option>
          </select>
        </div>

        <div class="field">
          <label for="amount">轉帳金額</label>
          <input
            type="number"
            id="amount"
            v-model.number="transferData.amount"
            min="1"
            step="1"
            placeholder="請輸入金額"
            required
          />
        </div>

        <div class="field">
          <label for="transferNote">分配用途</label>
          <input
            type="text"
            id="transferNote"
            v-model.trim="transferData.note"
            maxlength="100"
            placeholder="例如：旅費儲蓄、定期定額、生活預備金"
          />
          <div class="note-presets" aria-label="常用分配用途">
            <button
              v-for="preset in notePresets"
              :key="preset"
              type="button"
              class="preset-chip"
              @click="transferData.note = preset"
            >
              {{ preset }}
            </button>
          </div>
        </div>
      </div>
      <button
        type="submit"
        class="confirm-btn"
        :disabled="accountOptions.length < 2"
      >
        確認轉帳
      </button>
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
        note: "",
      },
      notePresets: ["旅費儲蓄", "定期定額", "緊急預備金"],
    };
  },
  computed: {
    accountOptions() {
      return Object.entries(this.assets || {}).map(([key, asset]) => ({
        key,
        label: `${asset.bank_name} - ${this.translateAccountType(asset.account_type)} ($${Number(asset.balance || 0).toLocaleString()})`,
      }));
    },
  },
  methods: {
    async handleTransfer() {
      if (this.transferData.source_id === this.transferData.dest_id) {
        this.$swal.fire("無法轉帳", "轉出和轉入帳戶不能是同一個。", "warning");
        return;
      }
      if (this.transferData.amount <= 0) {
        this.$swal.fire("金額錯誤", "轉帳金額必須大於 0。", "warning");
        return;
      }

      try {
        const response = await apiClient.post(`/api/transfer`, {
          source_id: this.transferData.source_id,
          dest_id: this.transferData.dest_id,
          amount: this.transferData.amount,
          note: this.transferData.note,
        });

        this.$swal.fire("完成", response.data.message, "success");
        this.$emit("transfer-success");
        this.resetTransferForm();
      } catch (error) {
        this.$swal.fire(
          "轉帳失敗",
          error.response?.data?.message || "請稍後再試。",
          "error"
        );
        console.error("轉帳失敗:", error);
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
    resetTransferForm() {
      this.transferData = {
        source_id: "",
        dest_id: "",
        amount: null,
        note: "",
      };
    },
  },
};
</script>

<style scoped>
.transfer-fields {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field label {
  font-weight: bold;
  color: #475569;
}

.field select,
.field input {
  min-height: 44px;
  width: 100%;
  padding: 0.8rem 1rem;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  transition: all 0.3s ease;
}

.note-presets {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.preset-chip {
  min-height: 34px;
  padding: 0 12px;
  border: 1px solid #cbd5e1;
  border-radius: 999px;
  background: #f8fafc;
  color: #334155;
  font-size: 0.88rem;
}

.field select:focus,
.field input:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2);
}

.confirm-btn {
  width: 100%;
  min-height: 46px;
  margin-top: 16px;
  background-color: #0f766e;
}

.confirm-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.empty-hint {
  margin: 0 0 12px;
  color: #64748b;
}
</style>
