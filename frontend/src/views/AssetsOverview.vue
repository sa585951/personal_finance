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
        @update-balance="updateBalance"
        @edit-transfer="startTransferEdit"
        @delete-transfer="deleteTransfer"
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

export default {
  name: "AssetsOverview",
  components: {
    AccountForm,
    AssetsTable,
    TotalCards,
    TransferForm,
    TransferHistory,
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
    async deleteAccount(accountId) {
      try {
        await apiClient.delete(`/api/assets/${accountId}`);
        await this.fetchAssets();
      } catch (err) {
        console.error("刪除失敗", err);
      }
    },
    async updateBalance(accountId, newBalance) {
      if (newBalance === null || newBalance === undefined) {
        return;
      }

      try {
        await apiClient.put(`/api/assets/${accountId}`, {
          new_balance: newBalance,
        });
        await this.fetchAssets();
      } catch (err) {
        console.error("更新失敗", err);
      }
    },
    async updateAccount(accountId, payload) {
      try {
        await apiClient.put(`/api/assets/${accountId}`, {
          bank_name: payload.bank_name,
          account_type: payload.account_type,
          currency: payload.currency,
          balance: payload.balance,
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
