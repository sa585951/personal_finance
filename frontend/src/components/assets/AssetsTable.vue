<template>
  <section class="accounts-list">
    <div class="section-heading">
      <h2>帳戶列表</h2>
      <span>{{ accountList.length }} 個帳戶</span>
    </div>

    <div v-if="accountList.length > 0" class="account-cards">
      <article
        v-for="account in accountList"
        :key="account.key"
        class="account-card"
      >
        <div class="account-main">
          <div>
            <h3>{{ account.asset.bank_name }}</h3>
            <p>{{ translateAccountType(account.asset.account_type) }}</p>
          </div>
          <strong>{{ formatMoney(account.asset.balance, account.asset.currency) }}</strong>
        </div>
        <div class="account-meta">
          <span>{{ account.asset.currency || "TWD" }}</span>
          <span>{{ account.asset.track_balance ? "追蹤餘額" : "不追蹤餘額" }}</span>
        </div>
        <div class="account-actions">
          <button class="update-btn" @click="promptUpdate(account.key)">
            更新餘額
          </button>
          <button class="delete-btn" @click="promptDelete(account.key)">
            刪除
          </button>
        </div>
      </article>
    </div>
    <div v-else class="no-data">
      目前沒有帳戶，先新增一個常用帳戶即可開始記錄。
    </div>
  </section>
</template>

<script>
export default {
  name: "AssetsTable",
  props: {
    assets: {
      type: Object,
      required: true,
      default: () => ({}),
    },
  },
  computed: {
    accountList() {
      return Object.entries(this.assets || {}).map(([key, asset]) => ({
        key,
        asset,
      }));
    },
  },
  methods: {
    async promptUpdate(accountId) {
      const { value: newBalance } = await this.$swal.fire({
        title: "更新餘額",
        input: "number",
        inputLabel: "請輸入新的餘額：",
        showCancelButton: true,
        confirmButtonText: "確定",
        cancelButtonText: "取消",
        inputValidator: (value) => {
          if (!value || isNaN(value) || parseFloat(value) < 0) {
            return "輸入無效，餘額必須為非負數！";
          }
        },
      });

      if (newBalance) {
        this.$emit("update-balance", accountId, parseFloat(newBalance));
      }
    },
    async promptDelete(accountId) {
      const result = await this.$swal.fire({
        title: "確定刪除？",
        text: "此操作無法復原。",
        icon: "warning",
        showCancelButton: true,
        confirmButtonColor: "#d33",
        cancelButtonColor: "#3085d6",
        confirmButtonText: "確定刪除",
        cancelButtonText: "取消",
      });

      if (result.isConfirmed) {
        this.$emit("delete-account", accountId);
      }
    },
    formatMoney(amount, currency = "TWD") {
      const minorUnit = ["TWD", "JPY", "KRW"].includes(currency) ? 0 : 2;
      return `${currency} ${Number(amount || 0).toLocaleString("zh-TW", {
        minimumFractionDigits: minorUnit,
        maximumFractionDigits: minorUnit,
      })}`;
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
  },
};
</script>
<style scoped>
.accounts-list {
  padding: 16px;
  border: 1px solid #dbe4ee;
  border-radius: 10px;
  background: #ffffff;
}

.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.section-heading h2 {
  margin: 0;
  color: #1f2933;
  font-size: 1.15rem;
  letter-spacing: 0;
}

.section-heading span {
  color: #64748b;
  font-size: 0.9rem;
}

.account-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.account-card {
  padding: 14px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #f8fafc;
}

.account-main {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.account-main h3 {
  margin: 0 0 2px;
  color: #1f2933;
  font-size: 1rem;
  letter-spacing: 0;
}

.account-main p {
  margin: 0;
  color: #64748b;
}

.account-main strong {
  flex-shrink: 0;
  color: #0f172a;
  font-size: 1.2rem;
}

.account-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.account-meta span {
  padding: 4px 8px;
  border-radius: 999px;
  background: #e0f2fe;
  color: #075985;
  font-size: 0.78rem;
  font-weight: 700;
}

.account-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 12px;
}

.account-actions button {
  min-height: 40px;
  padding: 8px 12px;
  border-radius: 8px;
  box-shadow: none;
}

.account-actions button:hover {
  transform: none;
  box-shadow: none;
}

.no-data {
  padding: 18px;
  border: 1px dashed #cbd5e1;
  border-radius: 10px;
  color: #64748b;
  text-align: center;
}
</style>
