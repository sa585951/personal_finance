<template>
  <section class="accounts-list">
    <div class="section-heading">
      <h2>帳戶列表</h2>
      <span>{{ accountList.length }} 個帳戶</span>
    </div>

    <div v-if="accountList.length > 0" class="account-search">
      <input
        v-model.trim="searchText"
        type="search"
        placeholder="搜尋帳戶名稱、類型或幣別"
      />
    </div>

    <div v-if="filteredAccountList.length > 0" class="account-groups">
      <section
        v-for="group in groupedAccounts"
        :key="group.type"
        class="account-group"
      >
        <button
          type="button"
          class="group-header"
          @click="toggleGroup(group.type)"
        >
          <span>{{ isGroupCollapsed(group.type) ? ">" : "v" }}</span>
          <span class="group-title">
            <strong>{{ group.label }}</strong>
            <small>{{ group.accounts.length }} 個帳戶</small>
          </span>
          <span class="group-totals">
            <small
              v-for="item in group.currencyTotals"
              :key="`${group.type}-${item.currency}`"
            >
              {{ item.currency }} {{ percentage(item.amount, currencyAllocationTotals[item.currency]) }}%
            </small>
          </span>
        </button>

        <div v-if="!isGroupCollapsed(group.type)" class="account-cards">
          <div class="group-allocation">
            <div
              v-for="item in group.currencyTotals"
              :key="`${group.type}-${item.currency}-summary`"
              class="group-allocation-row"
            >
              <div>
                <strong>{{ item.currency }}</strong>
                <span>{{ formatMoney(item.amount, item.currency) }}</span>
              </div>
              <small>{{ percentage(item.amount, currencyAllocationTotals[item.currency]) }}%</small>
              <div class="allocation-track">
                <div
                  class="allocation-fill"
                  :style="{ width: percentage(item.amount, currencyAllocationTotals[item.currency]) + '%' }"
                ></div>
              </div>
            </div>
          </div>

          <article
            v-for="account in group.accounts"
            :key="account.key"
            class="account-card"
            :class="{ expanded: expandedAccountId === account.key }"
          >
            <button
              type="button"
              class="account-summary-button"
              @click="toggleAccountActivity(account.key)"
            >
              <div class="account-main">
                <div>
                  <h3>{{ account.asset.bank_name }}</h3>
                  <p>{{ translateAccountType(account.asset.account_type) }}</p>
                </div>
                <strong>{{ formatMoney(account.asset.balance, account.asset.currency) }}</strong>
              </div>
              <span class="activity-hint">
                {{ expandedAccountId === account.key ? "收合近期活動" : "查看近期活動" }}
              </span>
            </button>
            <div class="account-meta">
              <span>{{ account.asset.currency || "TWD" }}</span>
              <span>{{ account.asset.track_balance ? "追蹤餘額" : "不追蹤餘額" }}</span>
              <span>
                佔 {{ account.asset.currency || "TWD" }}
                {{ percentage(positiveBalance(account.asset), currencyAllocationTotals[account.asset.currency || "TWD"]) }}%
              </span>
            </div>
            <div class="account-ratio">
              <div
                class="account-ratio-fill"
                :style="{
                  width: percentage(
                    positiveBalance(account.asset),
                    currencyAllocationTotals[account.asset.currency || 'TWD']
                  ) + '%'
                }"
              ></div>
            </div>
            <div class="account-actions">
              <button class="edit-btn" @click="startEdit(account)">
                編輯帳戶
              </button>
              <button class="update-btn" @click="promptUpdate(account)">
                更新餘額
              </button>
              <button class="delete-btn" @click="promptDelete(account.key)">
                刪除
              </button>
            </div>

            <form
              v-if="editingAccountId === account.key"
              class="edit-form"
              @submit.prevent="submitEdit(account.key)"
            >
              <div class="field">
                <label :for="`account-name-${account.key}`">帳戶名稱</label>
                <input
                  :id="`account-name-${account.key}`"
                  v-model.trim="editDraft.bank_name"
                  maxlength="100"
                  required
                />
              </div>
              <div class="field-grid">
                <div class="field">
                  <label :for="`account-type-${account.key}`">帳戶類型</label>
                  <select :id="`account-type-${account.key}`" v-model="editDraft.account_type">
                    <option
                      v-for="type in accountTypes"
                      :key="type.value"
                      :value="type.value"
                    >
                      {{ type.label }}
                    </option>
                  </select>
                </div>
                <div class="field">
                  <label :for="`account-currency-${account.key}`">幣別</label>
                  <select :id="`account-currency-${account.key}`" v-model="editDraft.currency">
                    <option v-for="currency in currencies" :key="currency" :value="currency">
                      {{ currency }}
                    </option>
                  </select>
                </div>
              </div>
              <div class="field">
                <label :for="`account-balance-${account.key}`">目前餘額</label>
                <input
                  :id="`account-balance-${account.key}`"
                  v-model.number="editDraft.balance"
                  type="number"
                  :min="editDraft.account_type === 'credit_card' ? null : 0"
                  step="1"
                  required
                />
              </div>
              <div class="edit-actions">
                <button class="update-btn" type="submit">儲存</button>
                <button class="cancel-btn" type="button" @click="cancelEdit">取消</button>
              </div>
            </form>

            <AccountActivityPanel
              v-if="expandedAccountId === account.key"
              :activities="accountActivityList(account.key)"
              :error="accountActivityErrors[account.key] || ''"
              :loading="Boolean(accountActivityLoading[account.key])"
              :pagination="accountActivityPage(account.key)"
              @page-change="requestActivityPage(account.key, $event)"
            />
          </article>
        </div>
      </section>
    </div>
    <div v-else-if="accountList.length > 0" class="no-data">
      找不到符合搜尋條件的帳戶。
    </div>
    <div v-else class="no-data">
      目前沒有帳戶，先新增一個常用帳戶即可開始記錄。
    </div>
  </section>
</template>

<script>
import AccountActivityPanel from "./AccountActivityPanel.vue";

export default {
  name: "AssetsTable",
  components: {
    AccountActivityPanel,
  },
  props: {
    assets: {
      type: Object,
      required: true,
      default: () => ({}),
    },
    accountActivities: {
      type: Object,
      default: () => ({}),
    },
    accountActivityLoading: {
      type: Object,
      default: () => ({}),
    },
    accountActivityErrors: {
      type: Object,
      default: () => ({}),
    },
    accountActivityPagination: {
      type: Object,
      default: () => ({}),
    },
  },
  emits: ["delete-account", "request-account-activity", "update-balance", "update-account"],
  data() {
    return {
      searchText: "",
      collapsedGroups: {},
      expandedAccountId: "",
      editingAccountId: "",
      editDraft: {
        bank_name: "",
        account_type: "bank",
        currency: "TWD",
        balance: 0,
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
    };
  },
  computed: {
    accountList() {
      return Object.entries(this.assets || {}).map(([key, asset]) => ({
        key,
        asset,
      })).sort((a, b) => {
        const typeOrder = this.accountTypeOrder(a.asset.account_type) - this.accountTypeOrder(b.asset.account_type);
        if (typeOrder !== 0) return typeOrder;
        return String(a.asset.bank_name || "").localeCompare(String(b.asset.bank_name || ""), "zh-TW");
      });
    },
    filteredAccountList() {
      const keyword = this.searchText.toLowerCase();
      if (!keyword) return this.accountList;
      return this.accountList.filter((account) => {
        const asset = account.asset;
        const searchableText = [
          asset.bank_name,
          asset.account_type,
          this.translateAccountType(asset.account_type),
          asset.currency,
        ].join(" ").toLowerCase();
        return searchableText.includes(keyword);
      });
    },
    groupedAccounts() {
      const groups = [];
      for (const account of this.filteredAccountList) {
        const type = account.asset.account_type || "other";
        let group = groups.find((item) => item.type === type);
        if (!group) {
          group = {
            type,
            label: this.translateAccountType(type),
            currency: account.asset.currency || "TWD",
            currencySet: new Set(),
            total: 0,
            totalsByCurrency: {},
            accounts: [],
          };
          groups.push(group);
        }
        const currency = account.asset.currency || "TWD";
        const positiveBalance = this.positiveBalance(account.asset);
        group.accounts.push(account);
        group.currencySet.add(currency);
        group.total += Number(account.asset.balance || 0);
        group.totalsByCurrency[currency] = (group.totalsByCurrency[currency] || 0) + positiveBalance;
      }
      return groups.map((group) => ({
        ...group,
        currencyTotals: Object.entries(group.totalsByCurrency)
          .map(([currency, amount]) => ({ currency, amount }))
          .filter((item) => item.amount > 0)
          .sort((a, b) => a.currency.localeCompare(b.currency)),
      }));
    },
    currencyAllocationTotals() {
      const totals = {};
      for (const account of this.accountList) {
        const currency = account.asset.currency || "TWD";
        totals[currency] = (totals[currency] || 0) + this.positiveBalance(account.asset);
      }
      return totals;
    },
  },
  methods: {
    toggleGroup(type) {
      this.collapsedGroups = {
        ...this.collapsedGroups,
        [type]: !this.isGroupCollapsed(type),
      };
    },
    toggleAccountActivity(accountId) {
      this.expandedAccountId = this.expandedAccountId === accountId ? "" : accountId;
      if (this.expandedAccountId && !this.accountActivities[accountId]) {
        this.requestActivityPage(accountId, 1);
      }
    },
    requestActivityPage(accountId, page) {
      if (page < 1) return;
      this.$emit("request-account-activity", accountId, page);
    },
    accountActivityList(accountId) {
      return this.accountActivities[accountId] || [];
    },
    accountActivityPage(accountId) {
      return this.accountActivityPagination[accountId] || {
        page: 1,
        limit: 10,
        has_next: false,
        has_prev: false,
      };
    },
    isGroupCollapsed(type) {
      return this.collapsedGroups[type] !== false;
    },
    accountTypeOrder(type) {
      const order = ["bank", "cash", "credit_card", "e_wallet", "prepaid_card", "investment", "external", "other"];
      const index = order.indexOf(type);
      return index === -1 ? order.length : index;
    },
    startEdit(account) {
      this.editingAccountId = account.key;
      this.editDraft = {
        bank_name: account.asset.bank_name || "",
        account_type: account.asset.account_type || "bank",
        currency: account.asset.currency || "TWD",
        balance: Number(account.asset.balance || 0),
      };
    },
    cancelEdit() {
      this.editingAccountId = "";
    },
    submitEdit(accountId) {
      if (!this.editDraft.bank_name) {
        this.$swal.fire("欄位未完整", "請輸入帳戶名稱。", "warning");
        return;
      }
      if (
        this.editDraft.balance === null
        || (this.editDraft.balance < 0 && this.editDraft.account_type !== "credit_card")
      ) {
        this.$swal.fire("金額錯誤", "只有信用卡餘額可為負數。", "warning");
        return;
      }
      this.$emit("update-account", accountId, { ...this.editDraft });
      this.editingAccountId = "";
    },
    async promptUpdate(account) {
      const { value: newBalance } = await this.$swal.fire({
        title: "更新餘額",
        input: "number",
        inputLabel: "請輸入新的餘額：",
        inputValue: account.asset.balance,
        showCancelButton: true,
        confirmButtonText: "確定",
        cancelButtonText: "取消",
        inputValidator: (value) => {
          if (value === "" || isNaN(value)) {
            return "請輸入有效的數字金額。";
          }
          if (parseFloat(value) < 0 && account.asset.account_type !== "credit_card") {
            return "只有信用卡餘額可為負數。";
          }
        },
      });

      if (newBalance !== undefined) {
        this.$emit("update-balance", account.key, parseFloat(newBalance));
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
    positiveBalance(asset) {
      return Math.max(0, Number(asset?.balance || 0));
    },
    percentage(amount, totalAmount) {
      const total = Number(totalAmount || 0);
      if (total <= 0) {
        return 0;
      }
      return Math.min(100, (Number(amount || 0) / total) * 100).toFixed(1);
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

.account-search {
  margin-bottom: 12px;
}

.account-search input {
  min-height: 42px;
  width: 100%;
  padding: 0.7rem 0.8rem;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
}

.account-groups {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.account-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.group-header {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  min-height: 42px;
  padding: 8px 10px;
  border: 1px solid #dbe4ee;
  border-radius: 8px;
  background: #f1f5f9;
  color: #1f2933;
  box-shadow: none;
}

.group-header:hover {
  transform: none;
  box-shadow: none;
}

.group-header strong {
  overflow: hidden;
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.group-title {
  display: grid;
  gap: 2px;
  min-width: 0;
  text-align: left;
}

.group-totals {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
}

.group-header small,
.group-totals small {
  color: #64748b;
  font-size: 0.82rem;
  white-space: nowrap;
}

.group-totals small {
  padding: 3px 7px;
  border-radius: 999px;
  background: #e0f2fe;
  color: #075985;
  font-weight: 800;
}

.account-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.group-allocation {
  display: grid;
  gap: 8px;
  padding: 10px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
}

.group-allocation-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 6px 10px;
}

.group-allocation-row div:first-child {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.group-allocation-row strong {
  color: #1f2933;
  font-size: 0.9rem;
}

.group-allocation-row span,
.group-allocation-row small {
  color: #64748b;
  font-size: 0.82rem;
}

.allocation-track {
  grid-column: 1 / -1;
  height: 7px;
  overflow: hidden;
  border-radius: 999px;
  background: #e2e8f0;
}

.allocation-fill {
  height: 100%;
  border-radius: 999px;
  background: #14b8a6;
  transition: width 0.25s ease;
}

.account-card {
  padding: 14px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #f8fafc;
}

.account-card.expanded {
  border-color: #94a3b8;
  background: #ffffff;
}

.account-summary-button {
  width: 100%;
  padding: 0;
  color: inherit;
  background: transparent;
  border: 0;
  border-radius: 0;
  box-shadow: none;
  text-align: left;
}

.account-summary-button:hover {
  transform: none;
  box-shadow: none;
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

.activity-hint {
  display: inline-flex;
  margin-top: 8px;
  color: #475569;
  font-size: 0.82rem;
  font-weight: 800;
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

.account-ratio {
  height: 6px;
  margin-top: 10px;
  overflow: hidden;
  border-radius: 999px;
  background: #e2e8f0;
}

.account-ratio-fill {
  height: 100%;
  border-radius: 999px;
  background: #0f766e;
  transition: width 0.25s ease;
}

.account-actions {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
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

.edit-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid #e2e8f0;
}

.field,
.field-grid {
  display: grid;
  gap: 8px;
}

.field-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.field label {
  color: #475569;
  font-size: 0.86rem;
  font-weight: 700;
}

.field input,
.field select {
  min-height: 42px;
  width: 100%;
  padding: 0.7rem 0.8rem;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
}

.edit-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.edit-btn {
  background-color: #0f766e;
}

.cancel-btn {
  background-color: #64748b;
}

.no-data {
  padding: 18px;
  border: 1px dashed #cbd5e1;
  border-radius: 10px;
  color: #64748b;
  text-align: center;
}

@media (max-width: 420px) {
  .account-actions,
  .field-grid {
    grid-template-columns: 1fr;
  }

  .group-header {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .group-totals {
    grid-column: 2 / -1;
    justify-self: end;
  }
}
</style>
