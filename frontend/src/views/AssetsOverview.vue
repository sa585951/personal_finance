<template>
  <div class="assets-screen">
    <header class="assets-header">
      <p class="eyebrow">Accounts</p>
      <h1>帳戶總覽</h1>
    </header>

    <div v-if="loading" class="state-card">載入中...</div>
    <div v-else-if="error" class="state-card error-state">{{ error }}</div>
    <div v-else class="assets-content">
      <TotalCards :totals="totals" />

      <router-link class="allocation-entry" to="/allocation">
        <span class="allocation-entry-icon" aria-hidden="true">
          <TrendCharts />
        </span>
        <span class="allocation-entry-copy">
          <strong>資產配置</strong>
          <small>管理投資標的、投入成本與手動資產快照</small>
        </span>
        <ArrowRight class="allocation-entry-arrow" aria-hidden="true" />
      </router-link>

      <section class="account-health-panel" aria-label="帳戶健康度">
        <div class="section-heading">
          <h2>帳戶健康度</h2>
          <span>{{ accountHealthSummary }}</span>
        </div>
        <div class="health-card-grid">
          <article
            v-for="card in accountHealthCards"
            :key="card.key"
            class="health-card"
            :class="card.tone"
          >
            <div>
              <span>{{ card.label }}</span>
              <strong>{{ card.value }}</strong>
            </div>
            <p>{{ card.hint }}</p>
          </article>
        </div>
      </section>

      <section class="action-panel">
        <div class="action-tabs" aria-label="帳戶操作">
          <button
            type="button"
            class="action-tab"
            :class="{ active: activeAction === 'account' }"
            @click="toggleAction('account')"
          >
            新增帳戶
          </button>
          <button
            type="button"
            class="action-tab"
            :class="{ active: activeAction === 'transfer' }"
            :disabled="assetCount < 2"
            @click="toggleAction('transfer')"
          >
            帳戶轉帳
          </button>
        </div>

        <div v-if="activeAction" class="inline-action">
          <div class="inline-action-header">
            <strong>{{ activeAction === "account" ? "新增帳戶" : "帳戶轉帳" }}</strong>
            <button class="quiet-button" type="button" @click="activeAction = null">收合</button>
          </div>
          <AccountForm
            v-if="activeAction === 'account'"
            @account-added="handleAccountAdded"
          />
          <TransferForm
            v-else
            :assets="assets"
            :editing-transfer="editingTransfer"
            @transfer-success="handleTransferSuccess"
            @cancel-edit="cancelTransferEdit"
          />
        </div>
      </section>

      <AssetsTable
        :assets="assets"
        :account-activities="accountActivities"
        :account-activity-loading="accountActivityLoading"
        :account-activity-errors="accountActivityErrors"
        :account-activity-pagination="accountActivityPagination"
        @delete-account="deleteAccount"
        @request-account-activity="fetchAccountActivity"
        @update-account="updateAccount"
        @adjust-balance="adjustBalance"
        @edit-transfer="startTransferEdit"
        @delete-transfer="deleteTransfer"
        @edit-transaction="openTransactionEdit"
        @delete-transaction="deleteTransaction"
        @open-trip="openTripLedger"
      />

      <TransferHistory
        :transfers="recentTransfers"
        @edit-transfer="startTransferEdit"
        @delete-transfer="deleteTransfer"
      />
    </div>
  </div>
</template>

<script>
import apiClient from "../api";
import AccountForm from "../components/assets/AccountForm.vue";
import AssetsTable from "../components/assets/AssetsTable.vue";
import TotalCards from "../components/assets/TotalCards.vue";
import TransferForm from "../components/assets/TransferForm.vue";
import TransferHistory from "../components/assets/TransferHistory.vue";
import { ArrowRight, TrendCharts } from "@element-plus/icons-vue";

export default {
  name: "AssetsOverview",
  components: {
    AccountForm,
    AssetsTable,
    TotalCards,
    TransferForm,
    TransferHistory,
    ArrowRight,
    TrendCharts,
  },
  data() {
    return {
      loading: true,
      error: null,
      assets: {},
      totals: null,
      recentTransfers: [],
      activeAction: null,
      editingTransfer: null,
      accountActivities: {},
      accountActivityLoading: {},
      accountActivityErrors: {},
      accountActivityPagination: {},
      accountActivityRequests: {},
    };
  },
  computed: {
    assetCount() {
      return Object.keys(this.assets || {}).length;
    },
    assetList() {
      return Object.values(this.assets || {});
    },
    accountHealthSummary() {
      const attentionCount = this.accountHealthCards.filter((card) => card.tone !== "success").length;
      if (this.assetCount === 0) return "尚無帳戶";
      if (attentionCount === 0) return "狀態良好";
      return `${attentionCount} 項需留意`;
    },
    accountHealthCards() {
      if (this.assetCount === 0) {
        return [
          {
            key: "empty",
            label: "尚未建立帳戶",
            value: "先新增常用帳戶",
            hint: "建立現金、銀行或信用卡帳戶後，就能核對收支與資金流向。",
            tone: "neutral",
          },
        ];
      }

      const cards = [];
      const creditDebtAccounts = this.assetList.filter((asset) => (
        asset.account_type === "credit_card" && Number(asset.balance || 0) < 0
      ));
      const zeroBalanceAccounts = this.assetList.filter((asset) => (
        asset.account_type !== "credit_card" && Number(asset.balance || 0) === 0
      ));
      const untrackedAccounts = this.assetList.filter((asset) => asset.track_balance === false);
      const invalidNegativeAccounts = this.assetList.filter((asset) => (
        asset.account_type !== "credit_card" && Number(asset.balance || 0) < 0
      ));

      if (creditDebtAccounts.length > 0) {
        cards.push({
          key: "credit-card",
          label: "信用卡待核對",
          value: `${creditDebtAccounts.length} 個帳戶`,
          hint: this.creditDebtHint(creditDebtAccounts),
          tone: "warning",
        });
      }

      if (invalidNegativeAccounts.length > 0) {
        cards.push({
          key: "negative",
          label: "非信用卡負數",
          value: `${invalidNegativeAccounts.length} 個帳戶`,
          hint: "非信用卡帳戶出現負數，建議檢查餘額或近期交易。",
          tone: "danger",
        });
      }

      if (zeroBalanceAccounts.length > 0) {
        cards.push({
          key: "zero",
          label: "零餘額帳戶",
          value: `${zeroBalanceAccounts.length} 個帳戶`,
          hint: "若已不再使用，可考慮更新名稱、整理分類或刪除前先確認沒有近期活動。",
          tone: "neutral",
        });
      }

      if (untrackedAccounts.length > 0) {
        cards.push({
          key: "untracked",
          label: "未追蹤餘額",
          value: `${untrackedAccounts.length} 個帳戶`,
          hint: "這些帳戶不會參與餘額追蹤，適合作為外部或暫時紀錄用途。",
          tone: "info",
        });
      }

      if (cards.length === 0) {
        return [
          {
            key: "healthy",
            label: "目前沒有需要處理的帳戶提醒",
            value: "狀態良好",
            hint: "信用卡、帳戶餘額與追蹤狀態目前看起來都正常。",
            tone: "success",
          },
        ];
      }

      return cards.slice(0, 4);
    },
  },
  created() {
    this.fetchAssets();
    this.fetchRecentTransfers();
  },
  methods: {
    toggleAction(action) {
      this.activeAction = this.activeAction === action ? null : action;
      if (this.activeAction !== "transfer") {
        this.editingTransfer = null;
      }
    },
    async handleAccountAdded() {
      await this.fetchAssets();
      this.activeAction = null;
    },
    async handleTransferSuccess() {
      await this.fetchAssets();
      await this.fetchRecentTransfers();
      await this.refreshLoadedAccountActivities();
      this.activeAction = null;
      this.editingTransfer = null;
    },
    async fetchAssets() {
      try {
        const response = await apiClient.get(`/api/assets`);
        this.assets = response.data.data;
        this.totals = this.calculateTotals(this.assets);
        this.accountActivities = {};
        this.accountActivityLoading = {};
        this.accountActivityErrors = {};
        this.accountActivityPagination = {};
      } catch (err) {
        console.error("無法載入資產資料:", err);
        this.error = "無法載入資產資料，請檢查後端伺服器或查看主控台錯誤。";
      } finally {
        this.loading = false;
      }
    },
    async fetchRecentTransfers() {
      try {
        const response = await apiClient.get(`/api/transfers/recent?limit=8`);
        this.recentTransfers = response.data.data || [];
      } catch (err) {
        console.error("無法載入轉帳紀錄:", err);
        this.recentTransfers = [];
      }
    },
    async fetchAccountActivity(accountId, page = 1, activityFilter = "all") {
      if (!accountId || this.accountActivityLoading[accountId]) {
        return;
      }

      this.accountActivityLoading = {
        ...this.accountActivityLoading,
        [accountId]: true,
      };
      this.accountActivityErrors = {
        ...this.accountActivityErrors,
        [accountId]: "",
      };
      this.accountActivityRequests = {
        ...this.accountActivityRequests,
        [accountId]: {
          page,
          filter: activityFilter,
        },
      };

      try {
        const response = await apiClient.get(
          `/api/assets/${accountId}/activity?limit=10&page=${page}&filter=${activityFilter}`
        );
        const activityPage = response.data.data || {};
        this.accountActivities = {
          ...this.accountActivities,
          [accountId]: activityPage.items || [],
        };
        this.accountActivityPagination = {
          ...this.accountActivityPagination,
          [accountId]: activityPage.pagination || {
            page,
            limit: 10,
            has_next: false,
            has_prev: page > 1,
          },
        };
      } catch (err) {
        console.error("無法載入帳戶近期活動:", err);
        this.accountActivityErrors = {
          ...this.accountActivityErrors,
          [accountId]: "無法載入此帳戶近期活動。",
        };
      } finally {
        this.accountActivityLoading = {
          ...this.accountActivityLoading,
          [accountId]: false,
        };
      }
    },
    async refreshLoadedAccountActivities() {
      const requests = Object.entries(this.accountActivityRequests);
      if (!requests.length) return;

      await Promise.all(
        requests.map(([accountId, request]) => (
          this.fetchAccountActivity(accountId, request.page || 1, request.filter || "all")
        ))
      );
    },
    calculateTotals(assets) {
      const totalsByCurrency = {};
      for (const accountId in assets) {
        const asset = assets[accountId];
        const currency = asset.currency || "TWD";
        const balance = parseFloat(asset.balance);
        const type = this.translateAccountType(asset.account_type);

        if (isNaN(balance)) {
          console.warn(`Asset ${accountId} has invalid balance: ${asset.balance}`);
          continue;
        }

        if (!totalsByCurrency[currency]) {
          totalsByCurrency[currency] = {
            currency,
            total: 0,
            allocationTotal: 0,
            accountCount: 0,
            byType: {
              銀行: 0,
              現金: 0,
              信用卡: 0,
              電子錢包: 0,
              投資: 0,
              其他: 0,
            },
          };
        }

        totalsByCurrency[currency].total += balance;
        totalsByCurrency[currency].accountCount += 1;
        const typeKey = ["銀行", "現金", "信用卡", "電子錢包", "投資"].includes(type) ? type : "其他";
        if (balance > 0) {
          totalsByCurrency[currency].allocationTotal += balance;
          totalsByCurrency[currency].byType[typeKey] += balance;
        }
      }

      return Object.values(totalsByCurrency).sort((a, b) => a.currency.localeCompare(b.currency));
    },
    translateAccountType(type) {
      const typeMap = {
        bank: "銀行",
        cash: "現金",
        credit_card: "信用卡",
        e_wallet: "電子錢包",
        investment: "投資",
      };
      return typeMap[type] || "其他";
    },
    creditDebtHint(accounts) {
      const totalsByCurrency = accounts.reduce((totals, account) => {
        const currency = account.currency || "TWD";
        totals[currency] = (totals[currency] || 0) + Math.abs(Number(account.balance || 0));
        return totals;
      }, {});
      const totalText = Object.entries(totalsByCurrency)
        .map(([currency, amount]) => this.formatMoney(amount, currency))
        .join("、");
      return `目前累積 ${totalText}，可點開信用卡帳戶核對支出紀錄。`;
    },
    formatMoney(amount, currency = "TWD") {
      const minorUnit = ["TWD", "JPY", "KRW"].includes(currency) ? 0 : 2;
      return `${currency} ${Number(amount || 0).toLocaleString("zh-TW", {
        minimumFractionDigits: minorUnit,
        maximumFractionDigits: minorUnit,
      })}`;
    },
    async deleteAccount(accountId) {
      try {
        await apiClient.delete(`/api/assets/${accountId}`);
        await this.fetchAssets();
      } catch (err) {
        console.error("刪除失敗", err);
      }
    },
    async adjustBalance(accountId, adjustment) {
      if (!adjustment || adjustment.new_balance === null || adjustment.new_balance === undefined) {
        return;
      }

      try {
        const activityRequest = this.accountActivityRequests[accountId] || {
          page: 1,
          filter: "all",
        };
        await apiClient.post(`/api/assets/${accountId}/adjustments`, adjustment);
        await this.fetchAssets();
        await this.fetchAccountActivity(
          accountId,
          activityRequest.page || 1,
          activityRequest.filter || "all"
        );
        this.$swal.fire("校正完成", "帳戶餘額已更新，且不會列入收入或支出。", "success");
      } catch (err) {
        console.error("校正失敗", err);
        this.$swal.fire(
          "校正失敗",
          err.response?.data?.message || "請稍後再試。",
          "error"
        );
      }
    },
    async updateAccount(accountId, payload) {
      try {
        await apiClient.put(`/api/assets/${accountId}`, {
          bank_name: payload.bank_name,
          account_type: payload.account_type,
          currency: payload.currency,
        });
        await this.fetchAssets();
      } catch (err) {
        console.error("更新帳戶失敗", err);
      }
    },
    startTransferEdit(transfer) {
      this.editingTransfer = transfer;
      this.activeAction = "transfer";
      this.$nextTick(() => {
        document.querySelector(".inline-action")?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      });
    },
    cancelTransferEdit() {
      this.editingTransfer = null;
    },
    async deleteTransfer(transfer) {
      const result = await this.$swal.fire({
        title: "刪除轉帳紀錄？",
        text: `這會回復「${transfer.source_name} → ${transfer.target_name}」造成的帳戶餘額變動。`,
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "刪除",
        cancelButtonText: "取消",
      });
      if (!result.isConfirmed) return;

      try {
        await apiClient.delete(`/api/transfers/${transfer.id}`);
        await this.fetchAssets();
        await this.fetchRecentTransfers();
        await this.refreshLoadedAccountActivities();
        this.editingTransfer = null;
        this.$swal.fire("已刪除", "轉帳紀錄已刪除並回復餘額。", "success");
      } catch (err) {
        this.$swal.fire(
          "刪除失敗",
          err.response?.data?.message || "請稍後再試。",
          "error"
        );
      }
    },
    openTransactionEdit(transaction) {
      if (!transaction?.id || transaction.trip_id) return;
      this.$router.push({
        path: "/transactions",
        query: {
          type: transaction.transaction_type === "income" ? "income" : "expense",
          edit: transaction.id,
        },
      });
    },
    openTripLedger(transaction) {
      this.$router.push({
        path: "/trips",
        query: transaction?.trip_id ? { trip_id: transaction.trip_id } : {},
      });
    },
    async deleteTransaction(transaction) {
      if (!transaction?.id || transaction.trip_id || transaction.can_delete === false) return;

      const result = await this.$swal.fire({
        title: "刪除收支紀錄？",
        text: "這會同步回復該筆交易造成的帳戶餘額變動。",
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "刪除",
        cancelButtonText: "取消",
      });
      if (!result.isConfirmed) return;

      try {
        await apiClient.delete(`/api/transactions/${transaction.id}`);
        await this.fetchAssets();
        await this.fetchRecentTransfers();
        await this.refreshLoadedAccountActivities();
        this.$swal.fire("已刪除", "收支紀錄已刪除並回復餘額。", "success");
      } catch (err) {
        this.$swal.fire(
          "刪除失敗",
          err.response?.data?.message || "請稍後再試。",
          "error"
        );
      }
    },
  },
};
</script>

<style scoped>
.assets-screen {
  max-width: 520px;
  min-height: calc(100vh - 80px);
  margin: 0 auto;
  padding: 24px 14px calc(var(--app-bottom-nav-height) + 22px);
  color: #1f2933;
}

.allocation-entry {
  min-height: 76px;
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) 20px;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  color: #1f2933;
  text-decoration: none;
  border: 1px solid #99f6e4;
  border-radius: 10px;
  background: #f0fdfa;
}

.allocation-entry-icon {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  color: #0f766e;
  background: #ccfbf1;
  border-radius: 8px;
}

.allocation-entry-icon svg,
.allocation-entry-arrow {
  width: 20px;
  height: 20px;
}

.allocation-entry-copy {
  min-width: 0;
  display: grid;
  gap: 2px;
}

.allocation-entry-copy strong {
  color: #134e4a;
}

.allocation-entry-copy small {
  color: #475569;
  line-height: 1.45;
}

.allocation-entry-arrow {
  color: #0f766e;
}

.assets-header {
  margin-bottom: 1rem;
}

.eyebrow {
  margin: 0 0 4px;
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
}

h1 {
  color: var(--text-color);
  font-size: 1.85rem;
  margin: 0;
  letter-spacing: 0;
}

.assets-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.state-card {
  padding: 18px;
  border: 1px solid #dbe4ee;
  border-radius: 10px;
  background: #ffffff;
  color: #475569;
}

.error-state {
  border-color: #fecaca;
  color: #b91c1c;
  background: #fef2f2;
}

.account-health-panel {
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

.health-card-grid {
  display: grid;
  gap: 10px;
}

.health-card {
  display: grid;
  gap: 8px;
  min-height: 92px;
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-left: 4px solid #94a3b8;
  border-radius: 8px;
  background: #f8fafc;
}

.health-card.warning {
  background: #fffbeb;
  border-color: #fde68a;
  border-left-color: #f59e0b;
}

.health-card.danger {
  background: #fef2f2;
  border-color: #fecaca;
  border-left-color: #dc2626;
}

.health-card.info {
  background: #eff6ff;
  border-color: #bfdbfe;
  border-left-color: #2563eb;
}

.health-card.success {
  background: #f0fdf4;
  border-color: #bbf7d0;
  border-left-color: #16a34a;
}

.health-card div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.health-card span {
  color: #475569;
  font-size: 0.84rem;
  font-weight: 900;
}

.health-card strong {
  color: #0f172a;
  font-size: 1rem;
  text-align: right;
}

.health-card p {
  margin: 0;
  color: #64748b;
  font-size: 0.82rem;
  font-weight: 700;
  line-height: 1.45;
}

.action-panel {
  padding: 16px;
  border: 1px solid #dbe4ee;
  border-radius: 10px;
  background: #ffffff;
}

.action-tabs {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.action-tab {
  min-height: 72px;
  padding: 12px;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  background: #f8fafc;
  color: #334155;
  box-shadow: none;
  font-size: 1rem;
}

.action-tab:hover {
  transform: none;
  box-shadow: none;
}

.action-tab.active {
  border-color: #0f766e;
  background: #ccfbf1;
  color: #115e59;
}

.action-tab:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.inline-action {
  display: grid;
  gap: 12px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid #e2e8f0;
}

.inline-action-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.quiet-button {
  min-height: 34px;
  padding: 0 10px;
  color: #334155;
  background: #e2e8f0;
  border-radius: 8px;
  box-shadow: none;
}

.quiet-button:hover {
  transform: none;
  box-shadow: none;
}
</style>
