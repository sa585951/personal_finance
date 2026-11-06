<template>
  <div class="account-form">
    <p v-if="loading" role="status">讀取待確認帳戶…</p>
    <p v-else-if="recoveryError" role="alert">{{ recoveryError }}</p>
    <PendingTransactionRecovery
      v-else-if="command?.pending"
      :payload="command.pending.payload"
      :details="pendingDetails"
      panel-label="待確認帳戶"
      heading="帳戶新增結果尚未確認"
      explanation="已保留原始資料，請勿另外建立相同帳戶。"
      :message="submitMessage"
      :busy="submitting"
      @retry="addAccount"
    />
    <form v-else @submit.prevent="addAccount">
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
        <select
          id="accountType"
          v-model="newAccount.account_type"
          required
        >
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

      <CreditCardBillingFields
        v-if="newAccount.account_type === 'credit_card'"
        v-model="newAccount.credit_card_billing"
      />

      <AccountAppearancePicker
        v-model:icon-key="newAccount.icon_key"
        v-model:color-key="newAccount.color_key"
      />

      <button type="submit" :disabled="submitting">新增</button>
    </form>
    <div v-if="submitMessage && !command?.pending && !recoveryError" class="message" role="status">{{ submitMessage }}</div>
  </div>
</template>

<script>
import apiClient from "../../api";
import PendingTransactionRecovery from "../shared/PendingTransactionRecovery.vue";
import { openPendingCommand } from "@/utils/pendingFinancialCommand";
import AccountAppearancePicker from "./AccountAppearancePicker.vue";
import CreditCardBillingFields from "./CreditCardBillingFields.vue";
import { defaultAccountAppearance } from "@/constants/accountAppearance";

export default {
  name: "AccountForm",
  components: { AccountAppearancePicker, CreditCardBillingFields, PendingTransactionRecovery },
  data() {
    const defaultAppearance = defaultAccountAppearance("bank");
    return {
      newAccount: {
        bank_name: "",
        account_type: "bank",
        balance: null,
        currency: "TWD",
        icon_key: defaultAppearance.iconKey,
        color_key: defaultAppearance.colorKey,
        credit_card_billing: null,
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
      recoveryError: "",
      command: null,
      loading: true,
      submitting: false,
    };
  },
  computed: {
    pendingDetails() {
      const payload = this.command.pending.payload;
      return [
        { label: "帳戶", value: payload.bank_name },
        { label: "類型", value: this.accountTypes.find(type => type.value === payload.account_type)?.label },
        { label: "餘額", value: `${payload.balance} ${payload.currency}` },
      ];
    },
  },
  async created() {
    try {
      this.command = await openPendingCommand("account:create");
    } catch {
      this.recoveryError = "無法讀取待確認帳戶，請先核對紀錄並確認瀏覽器儲存可用。";
    } finally {
      this.loading = false;
    }
  },
  methods: {
    async addAccount() {
      if (!this.command || this.recoveryError || this.submitting) return;
      this.submitting = true;
      this.submitMessage = "";
      const command = this.command;
      let requestId;
      try {
        const payload = this.newAccount.account_type === "credit_card" ? this.newAccount : {
          bank_name: this.newAccount.bank_name,
          account_type: this.newAccount.account_type,
          balance: this.newAccount.balance,
          currency: this.newAccount.currency,
          icon_key: this.newAccount.icon_key,
          color_key: this.newAccount.color_key,
        };
        const intent = command.pending?.payload ?? JSON.parse(JSON.stringify(payload));
        await command.verifyOwner();
        const request = command.prepare(intent);
        requestId = request.client_request_id;
        const response = await apiClient.post("/api/assets", request, {
          headers: { "X-Nomica-Request-Owner": command.ownerId },
        });
        if (response.data?.success !== true) throw new Error("結果尚未確認");
        command.clear(requestId);
        this.submitMessage = response.data.message;
        this.$emit("account-added");

        this.newAccount.bank_name = "";
        this.newAccount.account_type = "bank";
        this.newAccount.balance = null;
        this.newAccount.currency = "TWD";
        this.newAccount.credit_card_billing = null;
        this.resetAppearance();
      } catch (error) {
        const response = error.response;
        if (error.ownerChanged || response?.data?.code === "REQUEST_OWNER_CHANGED") {
          this.recoveryError = "登入使用者已變更，請重新載入頁面後核對帳戶。";
        } else if (requestId && response?.status === 400) {
          try {
            command.clear(requestId);
            this.submitMessage = response.data?.message || "帳戶未建立，請調整資料後重試。";
          } catch {
            this.submitMessage = "無法清除本機待確認狀態，請確認瀏覽器儲存可用。";
          }
        } else if (command.pending) {
          this.submitMessage = response?.data?.message || "結果尚未確認，請以保留的原資料重試。";
        } else {
          this.recoveryError = "無法確認登入或保存待確認帳戶，未送出新增請求。";
        }
      } finally {
        this.submitting = false;
      }
    },
    resetAppearance() {
      const appearance = defaultAccountAppearance("bank");
      this.newAccount.icon_key = appearance.iconKey;
      this.newAccount.color_key = appearance.colorKey;
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
  color: var(--light-text-color);
}

.form-group input,
.form-group select {
  min-height: 44px;
  width: 100%;
  padding: 0.8rem 1rem;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: var(--card-bg);
  transition: all 0.3s ease;
}

.form-group input:focus,
.form-group select:focus {
  outline: 3px solid var(--primary-color);
  outline-offset: 3px;
  border-color: var(--primary-color);
  box-shadow: none;
}

.account-form button {
  min-height: 46px;
  margin-top: 4px;
  background-color: var(--primary-color);
}

.message {
  margin-top: 1rem;
  padding: 1rem;
  border-radius: 6px;
  font-weight: bold;
  background-color: var(--income-soft);
  color: var(--income-color);
  text-align: center;
}
</style>
