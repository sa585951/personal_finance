<template>
  <section class="account-impact" :class="[kind, { confirmed }]" aria-live="polite">
    <div class="impact-heading">
      <div>
        <p>{{ confirmed ? "Recorded movement" : "Before you confirm" }}</p>
        <h3>{{ confirmed ? "這筆資金異動已完成" : "這筆紀錄會如何影響帳戶" }}</h3>
      </div>
      <span>{{ confirmed ? "已完成" : "預估" }}</span>
    </div>

    <div v-if="kind === 'transfer'" class="transfer-flow">
      <div class="flow-account outgoing">
        <div class="flow-account-heading">
          <AccountIcon
            :icon-key="accountIconKey(sourceAccount)"
            :color-key="accountColorKey(sourceAccount)"
            :label="`${accountName(sourceAccount)}圖示`"
            size="small"
          />
          <div>
            <small>轉出</small>
            <strong>{{ accountName(sourceAccount) }}</strong>
          </div>
        </div>
        <b>-{{ formatMoney(amount, accountCurrency(sourceAccount)) }}</b>
      </div>
      <ArrowRight class="flow-arrow" aria-hidden="true" />
      <div class="flow-account incoming">
        <div class="flow-account-heading">
          <AccountIcon
            :icon-key="accountIconKey(targetAccount)"
            :color-key="accountColorKey(targetAccount)"
            :label="`${accountName(targetAccount)}圖示`"
            size="small"
          />
          <div>
            <small>轉入</small>
            <strong>{{ accountName(targetAccount) }}</strong>
          </div>
        </div>
        <b>+{{ formatMoney(amount, accountCurrency(targetAccount)) }}</b>
      </div>
    </div>

    <div v-else class="transaction-impact">
      <AccountIcon
        v-if="account"
        :icon-key="accountIconKey(account)"
        :color-key="accountColorKey(account)"
        :label="`${accountName(account)}圖示`"
      />
      <div v-else class="direction-mark" :class="kind" aria-hidden="true">
        {{ kind === "income" ? "+" : "−" }}
      </div>
      <div>
        <small>{{ account ? (kind === "income" ? "存入帳戶" : "付款帳戶") : "帳戶餘額" }}</small>
        <strong>{{ account ? accountName(account) : "不連動帳戶" }}</strong>
      </div>
      <b v-if="account">
        {{ kind === "income" ? "+" : "-" }}{{ formatMoney(amount, accountCurrency(account)) }}
      </b>
      <b v-else class="unchanged">不變</b>
    </div>

    <div class="report-impact">
      <span>本月統計</span>
      <strong v-if="kind === 'transfer'">收入與支出不變</strong>
      <strong v-else>
        {{ kind === "income" ? "收入" : "支出" }} +{{ formatMoney(amount, reportCurrency) }}
      </strong>
    </div>

    <p v-if="kind === 'transfer'" class="impact-note">
      這是帳戶間的資金移動，不會被當成新的收入或支出。
    </p>
    <p v-else-if="!account" class="impact-note">
      交易仍會進入本月統計，但不會改變任何帳戶餘額。
    </p>
  </section>
</template>

<script>
import { ArrowRight } from "@element-plus/icons-vue";
import AccountIcon from "@/components/assets/AccountIcon.vue";
import { defaultAccountAppearance } from "@/constants/accountAppearance";

export default {
  name: "AccountImpactCard",
  components: { AccountIcon, ArrowRight },
  props: {
    kind: {
      type: String,
      required: true,
      validator: (value) => ["expense", "income", "transfer"].includes(value),
    },
    amount: {
      type: Number,
      required: true,
    },
    account: {
      type: Object,
      default: null,
    },
    sourceAccount: {
      type: Object,
      default: null,
    },
    targetAccount: {
      type: Object,
      default: null,
    },
    currency: {
      type: String,
      default: "TWD",
    },
    confirmed: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    reportCurrency() {
      return this.accountCurrency(this.account) || this.currency || "TWD";
    },
  },
  methods: {
    accountName(account) {
      return account?.bank_name || account?.name || "尚未選擇帳戶";
    },
    accountCurrency(account) {
      return account?.currency || this.currency || "TWD";
    },
    accountIconKey(account) {
      return account?.icon_key || defaultAccountAppearance(account?.account_type).iconKey;
    },
    accountColorKey(account) {
      return account?.color_key || defaultAccountAppearance(account?.account_type).colorKey;
    },
    formatMoney(amount, currency = "TWD") {
      const minorUnit = ["TWD", "JPY", "KRW"].includes(currency) ? 0 : 2;
      return `${currency} ${Number(amount || 0).toLocaleString("zh-TW", {
        minimumFractionDigits: minorUnit,
        maximumFractionDigits: minorUnit,
      })}`;
    },
  },
};
</script>

<style scoped>
.account-impact {
  display: grid;
  gap: 12px;
  padding: 14px;
  color: #0f172a;
  background: #f8fafc;
  border: 1px solid #dbe4ee;
  border-radius: 8px;
}

.account-impact.confirmed {
  background: #f0fdfa;
  border-color: #99f6e4;
}

.impact-heading,
.transaction-impact,
.report-impact {
  display: flex;
  align-items: center;
  gap: 10px;
}

.impact-heading {
  justify-content: space-between;
}

.impact-heading p,
.impact-heading h3,
.impact-note {
  margin: 0;
}

.impact-heading p {
  color: #64748b;
  font-size: 0.7rem;
  font-weight: 900;
  text-transform: uppercase;
}

.impact-heading h3 {
  margin-top: 2px;
  font-size: 0.98rem;
  letter-spacing: 0;
}

.impact-heading > span {
  flex: 0 0 auto;
  padding: 4px 8px;
  color: #475569;
  background: #e2e8f0;
  border-radius: 999px;
  font-size: 0.74rem;
  font-weight: 900;
}

.confirmed .impact-heading > span {
  color: #0f766e;
  background: #ccfbf1;
}

.transaction-impact {
  min-width: 0;
  padding: 10px 0;
  border-top: 1px solid #e2e8f0;
  border-bottom: 1px solid #e2e8f0;
}

.transaction-impact > div:nth-child(2) {
  display: grid;
  min-width: 0;
}

.transaction-impact small,
.flow-account small,
.report-impact span {
  color: #64748b;
  font-size: 0.76rem;
  font-weight: 800;
}

.transaction-impact strong,
.flow-account strong {
  overflow-wrap: anywhere;
}

.transaction-impact > b {
  margin-left: auto;
  font-size: 0.92rem;
  white-space: nowrap;
}

.transaction-impact > b.unchanged {
  color: #64748b;
}

.direction-mark {
  display: grid;
  flex: 0 0 34px;
  width: 34px;
  height: 34px;
  place-items: center;
  border-radius: 50%;
  font-size: 1.1rem;
  font-weight: 900;
}

.direction-mark.expense {
  color: #b91c1c;
  background: #fee2e2;
}

.direction-mark.income {
  color: #0f766e;
  background: #ccfbf1;
}

.transfer-flow {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 28px minmax(0, 1fr);
  align-items: center;
  gap: 8px;
}

.flow-account {
  display: grid;
  min-width: 0;
  gap: 3px;
  padding: 10px;
  background: #ffffff;
  border-left: 3px solid #cbd5e1;
}

.flow-account-heading {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 8px;
}

.flow-account-heading > div {
  display: grid;
  min-width: 0;
}

.flow-account.outgoing {
  border-left-color: #f87171;
}

.flow-account.incoming {
  border-left-color: #2dd4bf;
}

.flow-account b {
  font-size: 0.84rem;
  overflow-wrap: anywhere;
}

.flow-account.outgoing b {
  color: #b91c1c;
}

.flow-account.incoming b {
  color: #0f766e;
}

.flow-arrow {
  width: 20px;
  margin: 0 auto;
  color: #64748b;
}

.report-impact {
  justify-content: space-between;
  gap: 14px;
}

.report-impact strong {
  text-align: right;
  font-size: 0.88rem;
}

.impact-note {
  color: #64748b;
  font-size: 0.78rem;
  line-height: 1.5;
}

@media (max-width: 390px) {
  .transfer-flow {
    grid-template-columns: 1fr;
  }

  .flow-arrow {
    transform: rotate(90deg);
  }

  .transaction-impact {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .transaction-impact > b {
    width: 100%;
    margin-left: 44px;
  }
}
</style>
