<template>
  <div class="assets-screen">
    <header class="assets-header">
      <h1>帳戶</h1>
    </header>

    <AppStatePanel
      v-if="loading"
      title="正在載入帳戶"
      message="整理帳戶餘額與近期活動。"
      loading
    />
    <AppStatePanel
      v-else-if="error"
      title="帳戶資料暫時無法載入"
      :message="error"
      action-label="重新整理"
      tone="error"
      @action="fetchAssets"
    />
    <div v-else class="assets-content">
      <TotalCards :totals="totals" />

      <p v-for="card in accountAlerts" :key="card.key" class="account-alert" role="status">
        <strong>{{ card.label }}：{{ card.value }}</strong>
        <span>{{ card.hint }}</span>
      </p>

      <section class="action-panel app-surface">
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

      <section v-if="lastTransferResult?.impact" class="transfer-result-panel app-surface">
        <div class="transfer-result-heading">
          <div>
            <p>轉帳完成</p>
            <h2>{{ lastTransferResult.isEditing ? "轉帳已更新" : "轉帳完成" }}</h2>
          </div>
          <button type="button" aria-label="關閉轉帳結果" @click="lastTransferResult = null">關閉</button>
        </div>
        <AccountImpactCard
          kind="transfer"
          :amount="lastTransferResult.impact.amount"
          :source-account="lastTransferResult.impact.sourceAccount"
          :target-account="lastTransferResult.impact.targetAccount"
          :currency="lastTransferResult.impact.currency"
          confirmed
        />
      </section>

      <p v-if="adjustmentError" role="alert">{{ adjustmentError }}</p>
      <template v-if="adjustmentGroup">
        <template v-for="(command, accountId) in adjustmentCommands" :key="accountId">
          <PendingTransactionRecovery
            v-if="command.pending"
            :payload="command.pending.payload"
            :details="adjustmentDetails(accountId, command.pending.payload)"
            panel-label="待確認校正"
            heading="餘額校正結果尚未確認"
            explanation="已保留原始資料，請以原資料核對這次校正。"
            :message="adjustmentMessages[accountId]"
            :busy="Boolean(adjustmentBusy[accountId])"
            @retry="adjustBalance(accountId)"
          />
        </template>
      </template>

      <AssetsTable
        :assets="assets"
        :adjustment-disabled="isAdjustmentDisabled"
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
import AccountImpactCard from "../components/shared/AccountImpactCard.vue";
import { openPendingCommand, openPendingCommandGroup } from "@/utils/pendingFinancialCommand";
import PendingTransactionRecovery from "../components/shared/PendingTransactionRecovery.vue";
import AppStatePanel from "../components/shared/AppStatePanel.vue";
import AssetsTable from "../components/assets/AssetsTable.vue";
import TotalCards from "../components/assets/TotalCards.vue";
import TransferForm from "../components/assets/TransferForm.vue";
import TransferHistory from "../components/assets/TransferHistory.vue";

const ADJUSTMENT_SCOPE = "account:adjust:";
const ADJUSTMENT_REASON_LABELS = {
  statement_reconciliation: "與帳單或實際餘額核對",
  balance_correction: "修正先前輸入",
  opening_balance: "補登期初餘額",
  other: "其他",
};

export default {
  name: "AssetsOverview",
  components: {
    AccountForm,
    AccountImpactCard,
    AppStatePanel,
    AssetsTable,
    PendingTransactionRecovery,
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
      activeAction: this.$route.query.action === "account" ? "account" : null,
      editingTransfer: null,
      lastTransferResult: null,
      accountActivities: {},
      accountActivityLoading: {},
      accountActivityErrors: {},
      accountActivityPagination: {},
      accountActivityRequests: {},
      adjustmentGroup: null,
      adjustmentCommands: Object.create(null),
      adjustmentBusy: Object.create(null),
      adjustmentMessages: Object.create(null),
      adjustmentError: "",
    };
  },
  computed: {
    assetCount() {
      return Object.keys(this.assets || {}).length;
    },
    assetList() {
      return Object.values(this.assets || {});
    },
    accountAlerts() {
      // Only states that need action. A credit card owing money is normal, not an alert.
      return this.accountHealthCards.filter((card) => card.tone === "danger");
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
    if (!this.activeAction) this.restorePendingAccountCreate();
    this.restorePendingAdjustments();
  },
  methods: {
    async restorePendingAccountCreate() {
      try {
        const command = await openPendingCommand("account:create");
        if (command.pending && !this.activeAction) this.activeAction = "account";
      } catch {
        // Opening the form shows its recovery error if storage or auth is unavailable.
      }
    },
    toggleAction(action) {
      this.activeAction = this.activeAction === action ? null : action;
      if (this.activeAction === "transfer") {
        this.lastTransferResult = null;
      }
      if (this.activeAction !== "transfer") {
        this.editingTransfer = null;
      }
    },
    async handleAccountAdded() {
      await this.fetchAssets();
      this.activeAction = null;
    },
    async handleTransferSuccess(result) {
      await this.fetchAssets();
      await this.fetchRecentTransfers();
      await this.refreshLoadedAccountActivities();
      this.lastTransferResult = result || null;
      this.activeAction = null;
      this.editingTransfer = null;
      this.$nextTick(() => {
        document.querySelector(".transfer-result-panel")?.scrollIntoView({
          behavior: "smooth",
          block: "center",
        });
      });
    },
    async fetchAssets() {
      this.loading = true;
      this.error = null;
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
          `/api/assets/${accountId}/activity?limit=20&page=${page}&filter=${activityFilter}`
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
            limit: 20,
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
    async restorePendingAdjustments() {
      try {
        const group = await openPendingCommandGroup(ADJUSTMENT_SCOPE);
        for (const command of group.commands) {
          this.adjustmentCommands[command.scope.slice(ADJUSTMENT_SCOPE.length)] = command;
        }
        this.adjustmentGroup = group;
      } catch {
        this.adjustmentError = "無法讀取待確認校正，請核對紀錄並確認登入及瀏覽器儲存可用。";
      }
    },
    isAdjustmentDisabled(accountId) {
      return !this.adjustmentGroup || Boolean(
        this.adjustmentBusy[accountId] || this.adjustmentCommands[accountId]?.pending
      );
    },
    adjustmentDetails(accountId, intent) {
      const account = this.assets[accountId];
      return [
        { label: "帳戶", value: account?.bank_name || accountId },
        { label: "餘額", value: `${intent.new_balance} ${account?.currency || ""}` },
        { label: "原因", value: ADJUSTMENT_REASON_LABELS[intent.reason] },
        { label: "備註", value: intent.note || "—" },
      ];
    },
    async adjustBalance(accountId, adjustment) {
      if (!this.adjustmentGroup || this.adjustmentBusy[accountId]) return;
      if (adjustment && this.isAdjustmentDisabled(accountId)) return;
      this.adjustmentBusy[accountId] = true;
      this.adjustmentError = "";
      this.adjustmentMessages[accountId] = "";
      let command;
      let requestId;
      try {
        if (!this.adjustmentCommands[accountId]) {
          this.adjustmentCommands[accountId] = this.adjustmentGroup.open(ADJUSTMENT_SCOPE + accountId);
        }
        command = this.adjustmentCommands[accountId];
        // Capture confirmed values before awaiting authentication.
        const intent = adjustment ? { ...adjustment } : command.pending?.payload;
        if (!intent) return;
        await command.verifyOwner();
        const request = command.prepare(intent);
        requestId = request.client_request_id;
        const response = await apiClient.post(`/api/assets/${accountId}/adjustments`, request, {
          headers: { "X-Nomica-Request-Owner": command.ownerId },
        });
        if (response.data?.success !== true) throw new Error("結果尚未確認");
        command.clear(requestId);
      } catch (error) {
        const response = error.response;
        if (error.ownerChanged || response?.data?.code === "REQUEST_OWNER_CHANGED") {
          this.adjustmentGroup = null;
          this.adjustmentError = "登入使用者已變更，請重新載入後核對餘額校正紀錄。";
        } else if (requestId && response?.status === 400) {
          try {
            command.clear(requestId);
            this.$swal.fire("校正失敗", response.data?.message || "請調整資料後重試。", "error");
          } catch {
            this.adjustmentMessages[accountId] = "無法清除本機待確認狀態，請確認瀏覽器儲存可用。";
          }
        } else if (command?.pending) {
          this.adjustmentMessages[accountId] = response?.data?.message || "結果尚未確認，請以保留的原資料重試。";
        } else {
          this.adjustmentError = "無法保存待確認校正或確認登入，未送出校正請求。";
        }
        return;
      } finally {
        this.adjustmentBusy[accountId] = false;
      }

      await this.fetchAssets();
      if (this.assets[accountId]) {
        const activity = this.accountActivityRequests[accountId];
        await this.fetchAccountActivity(accountId, activity?.page || 1, activity?.filter || "all");
      }
      this.$swal.fire("校正完成", "帳戶餘額已更新，且不會列入收入或支出。", "success");
    },
    async updateAccount(accountId, payload, onComplete) {
      try {
        await apiClient.put(`/api/assets/${accountId}`, {
          bank_name: payload.bank_name,
          account_type: payload.account_type,
          currency: payload.currency,
          ...(payload.account_type === "credit_card" ? { credit_card_billing: payload.credit_card_billing } : {}),
        });
        await this.fetchAssets();
        onComplete?.(true);
      } catch (err) {
        console.error("更新帳戶失敗", err);
        this.$swal.fire("更新失敗", err.response?.data?.message || "請稍後再試。", "error");
        onComplete?.(false);
      }
    },
    startTransferEdit(transfer) {
      this.editingTransfer = transfer;
      this.lastTransferResult = null;
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
  color: var(--text-color);
}

.allocation-entry {
  min-height: 76px;
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) 20px;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  color: var(--text-color);
  text-decoration: none;
  border: 1px solid var(--brand-border);
  border-radius: 10px;
  background: var(--primary-soft);
}

.allocation-entry-icon {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  color: var(--primary-color);
  background: var(--primary-soft);
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
  color: var(--primary-hover);
}

.allocation-entry-copy small {
  color: var(--light-text-color);
  line-height: 1.45;
}

.allocation-entry-arrow {
  color: var(--primary-color);
}

.assets-header {
  margin-bottom: 1rem;
}

.eyebrow {
  margin: 0 0 4px;
  color: var(--light-text-color);
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

.account-health-panel {
  padding: 16px;
  border: 1px solid var(--border-color);
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
  color: var(--text-color);
  font-size: 1.15rem;
  letter-spacing: 0;
}

.section-heading span {
  color: var(--light-text-color);
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
  border: 1px solid var(--border-color);
  border-left: 4px solid var(--light-text-color);
  border-radius: 8px;
  background: var(--secondary-color);
}

.health-card.warning {
  background: var(--warning-soft);
  border-color: var(--warning-color);
  border-left-color: var(--warning-color);
}

.health-card.danger {
  background: var(--expense-soft);
  border-color: var(--expense-color);
  border-left-color: var(--expense-color);
}

.health-card.info {
  background: var(--primary-soft);
  border-color: var(--brand-border);
  border-left-color: var(--primary-color);
}

.health-card.success {
  background: var(--income-soft);
  border-color: var(--income-color);
  border-left-color: var(--income-color);
}

.health-card div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.health-card span {
  color: var(--light-text-color);
  font-size: 0.84rem;
  font-weight: 900;
}

.health-card strong {
  color: var(--text-color);
  font-size: 1rem;
  text-align: right;
}

.health-card p {
  margin: 0;
  color: var(--light-text-color);
  font-size: 0.82rem;
  font-weight: 700;
  line-height: 1.45;
}

.action-panel {
  padding: 16px;
  border: 1px solid var(--border-color);
}

.transfer-result-panel {
  display: grid;
  gap: 12px;
  padding: 16px;
  border: 1px solid var(--border-color);
}

.transfer-result-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.transfer-result-heading p,
.transfer-result-heading h2 {
  margin: 0;
}

.transfer-result-heading p {
  color: var(--primary-color);
  font-size: 0.72rem;
  font-weight: 900;
  text-transform: uppercase;
}

.transfer-result-heading h2 {
  margin-top: 2px;
  font-size: 1.08rem;
  letter-spacing: 0;
}

.transfer-result-heading button {
  min-height: 36px;
  padding: 0 11px;
  color: var(--primary-color);
  background: var(--card-bg);
  border: 1px solid var(--brand-border);
  border-radius: 8px;
  box-shadow: none;
  font-weight: 800;
}

.action-tabs {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.action-tab {
  min-height: 72px;
  padding: 12px;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  background: var(--secondary-color);
  color: var(--text-color);
  box-shadow: none;
  font-size: 1rem;
}

.action-tab:hover {
  transform: none;
  box-shadow: none;
}

.action-tab.active {
  border-color: var(--primary-color);
  background: var(--primary-soft);
  color: var(--primary-color);
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
  border-top: 1px solid var(--border-color);
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
  color: var(--text-color);
  background: var(--border-color);
  border-radius: 8px;
  box-shadow: none;
}

.quiet-button:hover {
  transform: none;
  box-shadow: none;
}
.account-alert {
  display: grid;
  gap: 2px;
  margin: 0;
  padding: 12px 14px;
  border: 1px solid var(--expense-color);
  border-radius: 10px;
  color: var(--expense-color);
  background: var(--expense-soft);
}

.account-alert span {
  color: var(--text-color);
  font-size: 0.88rem;
}
</style>
