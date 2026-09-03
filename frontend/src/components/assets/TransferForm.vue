<template>
  <div class="transfer-form">
    <p v-if="accountOptions.length < 2" class="empty-hint">
      至少需要兩個帳戶才能轉帳。
    </p>
    <form @submit.prevent="handleTransfer">
      <div class="transfer-fields">
        <AccountPicker
          v-model="transferData.source_id"
          :accounts="accountOptions"
          label="轉出帳戶"
          placeholder="請選擇轉出帳戶"
          :allow-none="false"
        />

        <AccountPicker
          v-model="transferData.dest_id"
          :accounts="accountOptions"
          label="轉入帳戶"
          placeholder="請選擇轉入帳戶"
          :allow-none="false"
        />

        <div class="field">
          <label for="amount">轉帳金額</label>
          <input
            type="number"
            id="amount"
          v-model.number="transferData.amount"
          min="1"
          step="0.01"
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
      <AccountImpactCard
        v-if="transferImpact"
        class="transfer-impact-preview"
        kind="transfer"
        :amount="transferImpact.amount"
        :source-account="transferImpact.sourceAccount"
        :target-account="transferImpact.targetAccount"
        :currency="transferImpact.currency"
      />
      <p v-if="hasCurrencyMismatch" class="currency-warning">
        目前帳戶互轉只支援同幣別，請改選相同幣別的帳戶。
      </p>
      <button
        type="submit"
        class="confirm-btn"
        :disabled="accountOptions.length < 2 || hasCurrencyMismatch"
      >
        {{ isEditing ? "更新轉帳" : "確認轉帳" }}
      </button>
      <button
        v-if="isEditing"
        type="button"
        class="cancel-btn"
        @click="cancelEditing"
      >
        取消編輯
      </button>
    </form>
  </div>
</template>

<script>
import apiClient from "../../api";
import AccountImpactCard from "@/components/shared/AccountImpactCard.vue";
import AccountPicker from "@/components/shared/AccountPicker.vue";

export default {
  name: "TransferForm",
  components: { AccountImpactCard, AccountPicker },
  props: {
    assets: {
      type: Object,
      required: true,
    },
    editingTransfer: {
      type: Object,
      default: null,
    },
  },
  emits: ["transfer-success", "cancel-edit"],
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
    isEditing() {
      return Boolean(this.editingTransfer?.id);
    },
    accountOptions() {
      return Object.entries(this.assets || {}).map(([key, asset]) => ({
        ...asset,
        id: asset.id || key,
      }));
    },
    selectedSourceAccount() {
      return this.findAsset(this.transferData.source_id);
    },
    selectedTargetAccount() {
      return this.findAsset(this.transferData.dest_id);
    },
    hasCurrencyMismatch() {
      return Boolean(
        this.selectedSourceAccount
        && this.selectedTargetAccount
        && this.selectedSourceAccount.currency !== this.selectedTargetAccount.currency
      );
    },
    transferImpact() {
      const amount = Number(this.transferData.amount || 0);
      if (amount <= 0 || !this.selectedSourceAccount || !this.selectedTargetAccount) {
        return null;
      }
      return {
        amount,
        sourceAccount: this.selectedSourceAccount,
        targetAccount: this.selectedTargetAccount,
        currency: this.selectedSourceAccount.currency || "TWD",
      };
    },
  },
  watch: {
    editingTransfer: {
      immediate: true,
      handler(transfer) {
        if (!transfer) return;
        this.transferData = {
          source_id: transfer.source_account_id || "",
          dest_id: transfer.target_account_id || "",
          amount: transfer.source_amount ?? transfer.target_amount ?? null,
          note: transfer.note || "",
        };
      },
    },
  },
  methods: {
    findAsset(accountId) {
      if (!accountId) return null;
      return this.assets?.[accountId]
        || Object.values(this.assets || {}).find((asset) => asset.id === accountId)
        || null;
    },
    async handleTransfer() {
      if (!this.transferData.source_id || !this.transferData.dest_id) {
        this.$swal.fire("欄位未完整", "請選擇轉出與轉入帳戶。", "warning");
        return;
      }
      if (this.transferData.source_id === this.transferData.dest_id) {
        this.$swal.fire("無法轉帳", "轉出和轉入帳戶不能是同一個。", "warning");
        return;
      }
      if (this.transferData.amount <= 0) {
        this.$swal.fire("金額錯誤", "轉帳金額必須大於 0。", "warning");
        return;
      }
      if (this.hasCurrencyMismatch) {
        this.$swal.fire("幣別不同", "目前帳戶互轉只支援相同幣別。", "warning");
        return;
      }

      try {
        const submittedImpact = this.transferImpact
          ? {
              ...this.transferImpact,
              sourceAccount: { ...this.transferImpact.sourceAccount },
              targetAccount: { ...this.transferImpact.targetAccount },
            }
          : null;
        const payload = {
          source_id: this.transferData.source_id,
          dest_id: this.transferData.dest_id,
          amount: this.transferData.amount,
          note: this.transferData.note,
        };
        const response = this.isEditing
          ? await apiClient.put(`/api/transfers/${this.editingTransfer.id}`, payload)
          : await apiClient.post(`/api/transfer`, payload);

        this.$emit("transfer-success", {
          message: response.data.message,
          impact: submittedImpact,
          isEditing: this.isEditing,
        });
        this.resetTransferForm();
      } catch (error) {
        this.$swal.fire(
          this.isEditing ? "更新失敗" : "轉帳失敗",
          error.response?.data?.message || "請稍後再試。",
          "error"
        );
        console.error("轉帳失敗:", error);
      }
    },
    resetTransferForm() {
      this.transferData = {
        source_id: "",
        dest_id: "",
        amount: null,
        note: "",
      };
    },
    cancelEditing() {
      this.resetTransferForm();
      this.$emit("cancel-edit");
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

.transfer-impact-preview {
  margin-top: 16px;
}

.currency-warning {
  margin: 10px 0 0;
  padding: 10px 12px;
  color: #92400e;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
  font-size: 0.86rem;
  font-weight: 800;
}

.confirm-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.cancel-btn {
  width: 100%;
  min-height: 42px;
  margin-top: 8px;
  color: #475569;
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  box-shadow: none;
}

.empty-hint {
  margin: 0 0 12px;
  color: #64748b;
}
</style>
