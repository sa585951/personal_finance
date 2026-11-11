<template>
  <div class="trips-page">
    <header class="trip-head">
      <button class="back-link" type="button" @click="returnToTripList">
        <ArrowLeft aria-hidden="true" />旅行
      </button>
      <div v-if="selectedTrip" class="trip-cover" :style="{ background: tripCover(selectedTrip).color }">
        <span class="cover-tag">{{ tripTimeLabel(selectedTrip, today) }}</span>
        <h1>{{ selectedTrip.name }}</h1>
        <p class="trip-meta">
          {{ selectedTrip.destination || "未設定地點" }} · {{ formatRange(selectedTrip) }} ·
          {{ selectedTrip.members.length }} 人 · {{ selectedTrip.default_currency }}
          <span v-if="tripReportLabel(selectedTrip)"> · {{ tripReportLabel(selectedTrip) }}</span>
        </p>
      </div>
      <h1 v-else>旅行</h1>
    </header>

    <div v-if="loading" class="loading-state">載入中...</div>
    <div v-else-if="!selectedTrip" class="trip-route-state">
      <strong>無法開啟旅行帳本</strong>
      <span>{{ tripLoadError || "這趟旅行可能已封存、刪除，或你沒有存取權限。" }}</span>
      <button class="secondary-action" type="button" @click="returnToTripList">回到旅行列表</button>
    </div>
    <section v-else class="trips-layout">
      <article v-if="selectedTrip" class="trip-detail">
        <section
          v-if="currentMemberMonthlyReportPreference === 'pending'"
          class="monthly-preference-panel"
          ref="monthlyPreferencePanel"
        >
          <div>
            <strong>這趟旅行要納入你的個人月報嗎？</strong>
            <p>只有你的分攤金額會影響你的首頁、收支分析與預算統計。</p>
          </div>
          <div class="monthly-preference-actions">
            <button
              type="button"
              class="primary-action app-primary-action"
              :disabled="updatingTripSettings"
              @click="updateMonthlyReportPreference('include')"
            >
              納入我的月報
            </button>
            <button
              type="button"
              class="secondary-action"
              :disabled="updatingTripSettings"
              @click="updateMonthlyReportPreference('exclude')"
            >
              不納入
            </button>
            <button
              type="button"
              class="quiet-action"
              :disabled="updatingTripSettings"
              @click="updateMonthlyReportPreference('pending')"
            >
              稍後再決定
            </button>
          </div>
        </section>

        <TripResultBanner v-if="tripResult" :result="tripResult" @open-split="activeSection = 'split'" />

        <button
          v-for="alert in tripAlerts"
          :key="alert.key"
          type="button"
          class="trip-alert"
          @click="activeSection = alert.section"
        >
          <span>{{ alert.text }}</span>
          <ArrowRight aria-hidden="true" />
        </button>

        <nav class="trip-tabs" aria-label="旅行操作">
          <button
            v-for="tab in operationTabs"
            :key="tab.key"
            type="button"
            :class="{ active: activeSection === tab.key }"
            @click="activeSection = tab.key"
          >
            <component :is="tab.icon" />
            <span>{{ tab.label }}</span>
          </button>
        </nav>

        <TripBreakdown
          v-show="activeSection === 'transactions'"
          :category-totals="tripTransactionSummary.category_totals"
          :currency="selectedTrip.base_currency"
          :days-elapsed="tripDaysElapsed(selectedTrip, today)"
        />

        <TripMembersPanel
          v-show="activeSection === 'members'"
          :members="selectedTrip.members"
          :current-member-id="selectedTrip.current_member_id || ''"
          :is-owner="isTripOwner"
          :trip-timezone="selectedTrip.timezone"
          :current-member="currentTripMember"
          :active-invite="activeInvite"
          :latest-invite-url="latestInviteUrl"
          :submitting-invite="submittingInvite"
          :submitting-member="submittingMember"
          :invite-message="inviteMessage"
          :member-message="memberMessage"
          :new-member="newMember"
          @update-role="updateMemberRole"
          @rename-member="renameMember"
          @release-member="releaseMember"
          @delete-member="deleteMember"
          @close-invite="closeInvite"
          @copy-invite="copyInviteLink"
          @create-invite="createInvite"
          @add-member="addMember"
          @leave="leaveSelectedTrip"
          @update-new-member="newMember = { ...newMember, ...$event }"
        />

        <div v-if="activeSection === 'expense' && !editingTransactionId" class="expense-form-head">
          <button type="button" class="text-button" @click="activeSection = 'transactions'">收起</button>
        </div>
        <p v-if="expenseCommandError && activeSection === 'expense'" role="alert">{{ expenseCommandError }}</p>
        <PendingTransactionRecovery
          v-if="expenseCommand?.pending && activeSection === 'expense' && !editingTransactionId"
          :key="selectedTrip.id"
          :payload="expenseCommand.pending.payload"
          :message="expenseMessage"
          :transaction-id="legacyExpenseId"
          :busy="submittingExpense"
          @retry="addTripExpense"
          @acknowledge="acknowledgeExpensePending"
        />
        <TripExpensePanel
          v-if="canCreateTripTransaction && !expenseCommandError && (!expenseCommand?.pending || editingTransactionId)"
          v-show="activeSection === 'expense'"
          :expense="newExpense"
          :quick-currencies="quickCurrencies"
          :expense-categories="expenseCategories"
          :members="selectedTrip.members"
          :accounts="compatibleTripAccounts"
          :is-current-user-payer="isCurrentUserPayer"
          :expense-preview="expensePreview"
          :rate-hint="expenseRateHint"
          :split-member-summary="splitMemberSummary"
          :custom-split-total="customSplitTotal"
          :custom-split-difference="customSplitDifference"
          :show-member-options="showSplitMemberOptions"
          :show-advanced="showExpenseAdvanced"
          :editing-transaction-id="editingTransactionId || ''"
          :submitting="submittingExpense || expenseCommandLoading"
          :message="expenseMessage"
          @update-expense="newExpense = { ...newExpense, ...$event }"
          @set-split-mode="setSplitMode"
          @toggle-member-options="showSplitMemberOptions = !showSplitMemberOptions"
          @toggle-advanced="showExpenseAdvanced = !showExpenseAdvanced"
          @cancel-edit="cancelEditExpense"
          @submit="addTripExpense"
        />

        <TripTransactionsPanel
          ref="tripTransactionsPanel"
          v-show="activeSection === 'transactions'"
          :transactions="tripTransactions"
          :filtered-transactions="filteredTripTransactions"
          :date-filters="tripDateFilters"
          :selected-date="selectedTransactionDate"
          :missing-split-count="tripTransactionSummary.missing_split_count"
          :selected-transaction="selectedTransactionDetail"
          :current-member-id="selectedTrip.current_member_id || ''"
          :pagination="tripTransactionPagination"
          :current-page="tripTransactionPager.page"
          :loading="isTripTransactionsLoading"
          :load-error="tripTransactionLoadError"
          @export="exportTripTransactionsCsv"
          @next-page="loadNextTripTransactionPage"
          @previous-page="loadPreviousTripTransactionPage"
          @retry-page="retryTripTransactionPage"
          @select-date="selectTripTransactionDate"
          @select-transaction="loadTransactionDetail"
          @delete-transaction="deleteTripTransaction"
          @edit-transaction="startEditTransaction"
        />

        <TripSettlementPanel
          v-show="activeSection === 'split'"
          :members="selectedTrip.members"
          :suggestions="settlementSuggestions"
          :summary="splitSummary"
          :records="settlementRecords"
          :show-details="showSplitDetails"
          :form="settlementForm"
          :submitting="submittingSettlement"
          :pending="Boolean(settlementCommand?.pending)"
          :current-member-id="selectedTrip.current_member_id || ''"
          :is-owner="isTripOwner"
          @copy-summary="copySettlementSummary"
          @select-suggestion="selectSettlementSuggestion"
          @update-form="settlementForm = { ...settlementForm, ...$event }"
          @submit="saveSettlement"
          @edit="editSettlement"
          @cancel-edit="resetSettlementForm"
          @post-account="postSettlementAccountEntry"
          @reverse-account="reverseSettlementAccountEntry"
          @toggle-details="showSplitDetails = !showSplitDetails"
          @void="deleteSettlement"
        />

        <section v-show="activeSection === 'settings'" class="trip-settings" aria-label="旅行設定">
          <div class="settings-row">
            <span>
              <strong>個人月報</strong>
              <small>{{ currentMemberMonthlyReportPreference === "include" ? "你的分攤會計入首頁、分析與預算" : "只保留在旅行帳本" }}</small>
            </span>
            <button
              v-if="currentMemberMonthlyReportPreference !== 'pending'"
              class="quiet-action"
              type="button"
              :disabled="updatingTripSettings"
              @click="toggleSelectedTripReportScope"
            >
              {{ currentMemberMonthlyReportPreference === "include" ? "改為不納入" : "改為納入" }}
            </button>
          </div>
          <div v-if="isTripOwner" class="settings-row settings-row--stack">
            <CoverPicker
              :model-value="tripCover(selectedTrip).key"
              label="封面"
              :disabled="updatingTripSettings"
              @update:model-value="updateCoverTheme"
            />
          </div>
          <TripRatesPanel
            v-if="tripRates"
            :rates="tripRates"
            :is-owner="isTripOwner"
            :default-currency="selectedTrip.default_currency"
            :busy="ratesBusy"
            @set-rate="setTripRate"
            @apply-rate="applyTripRate"
          />
          <div class="settings-row">
            <span><strong>切換旅行</strong></span>
            <button class="quiet-action" type="button" @click="showTripSwitcher = true">選擇</button>
          </div>
          <TripManagementPanel
            v-if="isTripOwner"
            :expanded="showTripManagement"
            :archived-trips="archivedManagedTrips"
            :deleted-trips="deletedManagedTrips"
            @toggle="toggleTripManagement"
            @archive="archiveSelectedTrip"
            @delete="deleteSelectedTrip"
            @unarchive="unarchiveTrip"
            @restore="restoreTrip"
        />
        </section>
      </article>
    </section>

    <button
      v-if="selectedTrip && canCreateTripTransaction && activeSection !== 'expense'"
      type="button"
      class="trip-fab"
      @click="openExpenseForm"
    >
      <Plus aria-hidden="true" />記一筆旅行支出
    </button>

    <TripSwitcherModal
      v-if="showTripSwitcher"
      :items="tripSwitcherItems"
      :selected-id="selectedTrip ? selectedTrip.id : ''"
      @close="showTripSwitcher = false"
      @select="switchTrip"
    />
  </div>
</template>

<script>
import { copyDialogOptions } from "@/utils/safeDialogs";
import { ArrowLeft, ArrowRight, Calendar, List, Location, Money, Plus, Refresh, Setting, TrendCharts, User } from "@element-plus/icons-vue";
import apiClient from "@/api";
import { openPendingCommand } from '@/utils/pendingFinancialCommand';
import PendingTransactionRecovery from '@/components/shared/PendingTransactionRecovery.vue';
import TripExpensePanel from "@/components/trips/TripExpensePanel.vue";
import TripManagementPanel from "@/components/trips/TripManagementPanel.vue";
import TripRatesPanel from "@/components/trips/TripRatesPanel.vue";
import TripMembersPanel from "@/components/trips/TripMembersPanel.vue";
import TripSettlementPanel from "@/components/trips/TripSettlementPanel.vue";
import TripBreakdown from "@/components/trips/TripBreakdown.vue";
import TripResultBanner from "@/components/trips/TripResultBanner.vue";
import TripSwitcherModal from "@/components/trips/TripSwitcherModal.vue";
import TripTransactionsPanel from "@/components/trips/TripTransactionsPanel.vue";
import { defaultAccountId, rememberLastAccount } from "@/utils/lastAccount";
import { localDateKey } from "@/utils/money";
import { tripCover, tripDaysElapsed, tripTimeLabel } from "@/constants/tripCovers";
import { formatAmount } from "@/utils/money";
import { buildSettlementSummary } from "@/utils/settlementSummary";
import CoverPicker from "@/components/trips/CoverPicker.vue";
import {
  createCursorPager,
  cursorForPage,
  recordCursorPage,
  resetCursorPager,
} from "@/utils/cursorPagination";

export default {
  name: "TripsView",
  components: {
    PendingTransactionRecovery,
    CoverPicker,
    ArrowLeft,
    ArrowRight,
    Calendar,
    List,
    Location,
    Money,
    Plus,
    Refresh,
    Setting,
    TrendCharts,
    TripExpensePanel,
    TripManagementPanel,
    TripRatesPanel,
    TripMembersPanel,
    TripSettlementPanel,
    TripBreakdown,
    TripResultBanner,
    TripSwitcherModal,
    TripTransactionsPanel,
    User,
  },
  data() {
    const today = new Date().toISOString().slice(0, 10);
    return {
      loading: true,
      submittingMember: false,
      submittingExpense: false,
      expenseCommand: null,
      expenseCommandLoading: true,
      expenseCommandError: '',
      legacyExpenseId: '',
      expenseCommandEpoch: 0,
      tripRates: null,
      ratesBusy: false,
      submittingInvite: false,
      updatingTripSettings: false,
      showTripSwitcher: false,
      showTripManagement: false,
      activeSection: "expense",
      today: localDateKey(),
      trips: [],
      managedTrips: [],
      selectedTrip: null,
      assets: {},
      tripTransactions: [],
      tripTransactionPagination: {
        next_cursor: null,
        has_more: false,
        limit: 20,
        total_count: 0,
      },
      tripTransactionPager: createCursorPager(20),
      tripTransactionSummary: {
        total_count: 0,
        expense_count: 0,
        missing_split_count: 0,
        date_counts: [],
        category_totals: [],
      },
      isTripTransactionsLoading: false,
      tripTransactionLoadError: "",
      tripTransactionRetry: null,
      selectedTransactionDetail: null,
      splitSummary: [],
      settlementSuggestions: [],
      settlementRecords: [],
      submittingSettlement: false,
      settlementCommand: null,
      settlementForm: {
        id: null,
        from_member_id: "",
        to_member_id: "",
        amount: "",
        settled_on: new Date().toLocaleDateString("sv-SE"),
      },
      tripLoadError: "",
      splitDetailsLoaded: false,
      inviteStatusLoaded: false,
      activeInvite: null,
      latestInviteUrl: "",
      expenseCategories: [],
      editingTransactionId: null,
      selectedTransactionDate: "all",
      showExpenseAdvanced: false,
      showSplitDetails: false,
      showSplitMemberOptions: false,
      newMember: {
        display_name: "",
        role: "viewer",
      },
      newExpense: {
        date: today,
        item: "",
        merchant: "",
        budget_category: "伙食",
        amount: null,
        original_currency: "JPY",
        exchange_rate: 0.22,
        paid_by_member_id: "",
        account_id: "",
        description: "",
        review_status: "confirmed",
        split_mode: "equal",
        split_member_ids: [],
        split_allocations: {},
      },
      memberMessage: "",
      expenseMessage: "",
      inviteMessage: "",
    };
  },
  computed: {
    expenseRateHint() {
      const currency = this.newExpense.original_currency;
      const base = this.selectedTrip?.base_currency;
      if (!currency || !base || currency === base) return "";
      const tripRate = this.tripRates?.rates?.find((row) => row.currency === currency)?.rate;
      if (tripRate && Number(this.newExpense.exchange_rate) === Number(tripRate)) return "旅行共用匯率，由旅行擁有者設定";
      if (tripRate) return `旅行共用匯率是 ${tripRate}，這筆使用你填的匯率`;
      return "目前是參考匯率，建議請旅行擁有者先設定這趟旅行的匯率";
    },
    routeTripId() {
      return this.$route.params.tripId || "";
    },
    operationTabs() {
      return [
        { key: "transactions", label: "支出", icon: "List" },
        { key: "split", label: "分帳", icon: "TrendCharts" },
        { key: "members", label: "旅伴", icon: "User" },
        { key: "settings", label: "設定", icon: "Setting" },
      ];
    },
    quickCurrencies() {
      if (!this.selectedTrip) {
        return ["TWD"];
      }
      return Array.from(new Set([
        this.selectedTrip.default_currency,
        this.selectedTrip.base_currency,
        "TWD",
      ].filter(Boolean)));
    },
    tripExpenseTotal() {
      return (this.tripTransactionSummary.category_totals || []).reduce(
        (sum, item) => sum + Number(item.amount || 0),
        0
      );
    },
    tripDateFilters() {
      const dates = (this.tripTransactionSummary.date_counts || []).map((item) => ({
        key: item.date,
        label: this.formatDateChip(item.date),
        count: Number(item.count || 0),
      }));

      return [
        {
          key: "all",
          label: "全部",
          count: this.tripTransactionSummary.total_count,
        },
        ...dates,
      ];
    },
    filteredTripTransactions() {
      if (this.selectedTransactionDate === "all") {
        return this.tripTransactions;
      }
      return this.tripTransactions.filter(
        (transaction) => transaction.date === this.selectedTransactionDate
      );
    },
    tripResult() {
      // Shown only when there is something to settle between at least two people.
      const me = this.selectedTrip?.current_member_id;
      if (!this.splitDetailsLoaded) return null;
      if (!me || (this.selectedTrip.members || []).length < 2) return null;
      if (!(this.tripTransactionSummary.expense_count > 0)) return null;
      const money = (amount, currency) => `${currency} ${formatAmount(amount, currency)}`;
      const detail = `你的成本 ${money(this.myTripShareAmount, this.selectedTrip.base_currency)} · 整團 ${money(this.tripExpenseTotal, this.selectedTrip.base_currency)}`;
      const suggestions = this.settlementSuggestions;
      const toMe = suggestions.filter((item) => item.to_member_id === me);
      const fromMe = suggestions.filter((item) => item.from_member_id === me);
      const sum = (items) => items.reduce((total, item) => total + Number(item.amount || 0), 0);
      if (toMe.length) {
        const currency = toMe[0].currency;
        return {
          tone: "owed", detail,
          headline: toMe.length === 1
            ? `${toMe[0].from_display_name} 要給你 ${money(toMe[0].amount, currency)}`
            : `${toMe.length} 位旅伴要給你共 ${money(sum(toMe), currency)}`,
        };
      }
      if (fromMe.length) {
        const currency = fromMe[0].currency;
        return {
          tone: "owing", detail,
          headline: fromMe.length === 1
            ? `你要給 ${fromMe[0].to_display_name} ${money(fromMe[0].amount, currency)}`
            : `你要給 ${fromMe.length} 位旅伴共 ${money(sum(fromMe), currency)}`,
        };
      }
      return {
        tone: "even", detail,
        headline: suggestions.length ? "你不用結算" : "已平衡，不用結算",
      };
    },
    tripAlerts() {
      // Only states that need action; nothing is shown when the trip is fine or empty.
      const alerts = [];
      const missing = this.tripTransactionSummary.missing_split_count || 0;
      if (missing > 0) {
        alerts.push({ key: "split", text: `${missing} 筆支出還沒分攤`, section: "transactions" });
      }
      return alerts;
    },
    tripSwitcherItems() {
      return this.trips.map((trip) => ({
        id: trip.id,
        name: trip.name,
        description: `${trip.destination || "未設定地點"} · ${this.formatRange(trip)}`,
        reportLabel: this.tripReportLabel(trip),
        reportClass: this.tripReportPreferenceClass(trip),
      }));
    },
    currentMemberSummary() {
      if (!this.selectedTrip || !this.selectedTrip.current_member_id) return null;
      return this.splitSummary.find(
        (member) => member.member_id === this.selectedTrip.current_member_id
      ) || null;
    },
    canManageSelectedTrip() {
      if (!this.selectedTrip || !this.selectedTrip.current_member_id) return false;
      const currentMember = this.selectedTrip.members.find(
        (member) => member.id === this.selectedTrip.current_member_id
      );
      return currentMember?.role === "owner";
    },
    myTripShareAmount() {
      return Number(this.currentMemberSummary?.share_amount || 0);
    },
    myTripNetAmount() {
      return Number(this.currentMemberSummary?.net_amount || 0);
    },
    myTripNetStatus() {
      const amount = Number(this.myTripNetAmount || 0);
      if (amount > 0) {
        return {
          label: "待收",
          hint: "旅伴需還你",
          tone: "positive",
          amountClass: "positive-net",
        };
      }
      if (amount < 0) {
        return {
          label: "待付",
          hint: "你需要補給旅伴",
          tone: "negative",
          amountClass: "negative-net",
        };
      }
      return {
        label: "已平衡",
        hint: "目前不用結算",
        tone: "balanced",
        amountClass: "",
      };
    },
    compatibleTripAccounts() {
      if (!this.selectedTrip || !this.isCurrentUserPayer) return [];
      const compatibleCurrencies = new Set([
        this.newExpense.original_currency,
        this.selectedTrip.base_currency,
      ]);
      return Object.values(this.assets || {})
        .filter((asset) => compatibleCurrencies.has(asset.currency))
        .map((asset) => ({ ...asset }))
        .sort((a, b) => {
          const typeOrder = this.accountTypeOrder(a.account_type) - this.accountTypeOrder(b.account_type);
          if (typeOrder !== 0) return typeOrder;
          return (a.bank_name || "").localeCompare(b.bank_name || "", "zh-TW");
        });
    },
    archivedManagedTrips() {
      return this.managedTrips.filter((trip) => !trip.deleted_at && trip.status === "archived");
    },
    deletedManagedTrips() {
      return this.managedTrips.filter((trip) => trip.deleted_at);
    },
    selectedPaymentAccount() {
      if (!this.newExpense.account_id) return null;
      return Object.values(this.assets || {}).find(
        (asset) => asset.id === this.newExpense.account_id
      ) || null;
    },
    isCurrentUserPayer() {
      return Boolean(
        this.selectedTrip?.current_member_id &&
        this.newExpense.paid_by_member_id === this.selectedTrip.current_member_id
      );
    },
    expensePreview() {
      if (!this.selectedTrip || !Number(this.newExpense.amount)) {
        return null;
      }

      const amount = Number(this.newExpense.amount || 0);
      const exchangeRate = Number(this.newExpense.exchange_rate || 0);
      const convertedAmount = amount * exchangeRate;
      const baseCurrency = this.selectedTrip.base_currency;
      const account = this.selectedPaymentAccount;
      let accountDebitText = "未連動帳戶";

      if (account) {
        const debitAmount = account.currency === this.newExpense.original_currency
          ? amount
          : convertedAmount;
        accountDebitText = `${account.bank_name} ${this.formatMoney(debitAmount, account.currency)}`;
      }

      return {
        convertedText: `${this.formatMoney(amount, this.newExpense.original_currency)} ≈ ${this.formatMoney(convertedAmount, baseCurrency)}`,
        accountDebitText,
      };
    },
    customSplitTotal() {
      return Object.values(this.newExpense.split_allocations || {})
        .reduce((sum, amount) => sum + Number(amount || 0), 0);
    },
    customSplitDifference() {
      return Number(this.newExpense.amount || 0) - this.customSplitTotal;
    },
    splitMemberSummary() {
      const selectedCount = this.newExpense.split_member_ids.length;
      const totalCount = this.selectedTrip?.members.length || 0;
      if (selectedCount === 0) {
        return "尚未選擇分帳成員";
      }
      if (selectedCount === 1) {
        const selectedMemberId = this.newExpense.split_member_ids[0];
        const selectedMember = this.selectedTrip?.members.find((member) => member.id === selectedMemberId);
        if (selectedMemberId === this.selectedTrip?.current_member_id) {
          return "僅自己負擔";
        }
        return selectedMember ? `僅 ${selectedMember.display_name} 負擔` : "僅 1 人負擔";
      }
      if (selectedCount === totalCount) {
        return `全員均分 ${selectedCount} 人`;
      }
      return `選擇 ${selectedCount}/${totalCount} 人均分`;
    },
    currentTripMember() {
      if (!this.selectedTrip?.current_member_id) return null;
      return this.selectedTrip.members.find(
        (member) => member.id === this.selectedTrip.current_member_id
      ) || null;
    },
    currentMemberMonthlyReportPreference() {
      return this.currentTripMember?.monthly_report_preference || null;
    },
    isTripOwner() {
      return this.currentTripMember?.role === "owner";
    },
    canCreateTripTransaction() {
      return ["owner", "editor"].includes(this.currentTripMember?.role);
    },
  },
  watch: {
    routeTripId(nextTripId, previousTripId) {
      if (nextTripId === previousTripId) return;
      if (!nextTripId) {
        this.selectedTrip = null;
        this.tripLoadError = "";
        return;
      }
      this.selectTrip(nextTripId);
    },
    "newExpense.original_currency"() {
      this.applyDefaultExchangeRate();
      if (
        this.newExpense.account_id &&
        !this.compatibleTripAccounts.some((account) => account.id === this.newExpense.account_id)
      ) {
        this.newExpense.account_id = "";
      }
    },
    "newExpense.paid_by_member_id"() {
      if (!this.isCurrentUserPayer) {
        this.newExpense.account_id = "";
      }
    },
    activeSection(section) {
      this.ensureActiveSectionData(section);
    },
  },
  methods: {
    accountTypeOrder(type) {
      const order = ["bank", "cash", "credit_card", "e_wallet", "prepaid_card", "investment", "external", "other"];
      const index = order.indexOf(type);
      return index === -1 ? order.length : index;
    },
    setSplitMode(mode) {
      this.newExpense.split_mode = mode;
      if (mode === "custom") {
        this.showSplitMemberOptions = false;
        this.initializeCustomSplitAllocations();
      }
    },
    initializeCustomSplitAllocations() {
      if (!this.selectedTrip) return;
      const amount = Number(this.newExpense.amount || 0);
      const members = this.selectedTrip.members;
      const allocations = {};
      const splitMemberIds = this.newExpense.split_member_ids.length > 0
        ? this.newExpense.split_member_ids
        : this.getDefaultSplitMemberIds();

      members.forEach((member) => {
        allocations[member.id] = 0;
      });

      if (amount > 0 && splitMemberIds.length > 0) {
        const baseShare = Math.floor(amount / splitMemberIds.length);
        const remainder = amount % splitMemberIds.length;
        splitMemberIds.forEach((memberId, index) => {
          allocations[memberId] = baseShare + (index === 0 ? remainder : 0);
        });
      }

      this.newExpense.split_allocations = allocations;
    },
    getDefaultSplitMemberIds() {
      if (!this.selectedTrip) return [];
      const defaultMemberId = this.selectedTrip.current_member_id ||
        this.newExpense.paid_by_member_id ||
        this.selectedTrip.members[0]?.id ||
        "";
      return defaultMemberId ? [defaultMemberId] : [];
    },
    getDefaultExchangeRate(originalCurrency, baseCurrency) {
      if (!originalCurrency || !baseCurrency || originalCurrency === baseCurrency) {
        return 1;
      }
      // The trip's shared rate wins over the built-in reference table.
      const tripRate = this.tripRates?.rates?.find((row) => row.currency === originalCurrency)?.rate;
      if (tripRate) return Number(tripRate);

      const defaultRates = {
        "JPY:TWD": 0.22,
        "KRW:TWD": 0.023,
        "USD:TWD": 32,
        "EUR:TWD": 35,
        "TWD:JPY": 4.55,
        "TWD:KRW": 43.5,
        "TWD:USD": 0.031,
        "TWD:EUR": 0.029,
        "USD:JPY": 145,
        "JPY:USD": 0.0069,
        "EUR:JPY": 158,
        "JPY:EUR": 0.0063,
        "USD:EUR": 0.92,
        "EUR:USD": 1.09,
        "KRW:JPY": 0.11,
        "JPY:KRW": 9.1,
      };

      return defaultRates[`${originalCurrency}:${baseCurrency}`] || 1;
    },
    applyDefaultExchangeRate() {
      if (!this.selectedTrip) return;
      this.newExpense.exchange_rate = this.getDefaultExchangeRate(
        this.newExpense.original_currency,
        this.selectedTrip.base_currency
      );
    },
    normalizeActiveSection() {
      if (this.activeSection === "expense" && this.canCreateTripTransaction) return;
      if (!this.operationTabs.some((tab) => tab.key === this.activeSection)) {
        this.activeSection = this.operationTabs[0]?.key || "transactions";
      }
    },
    async fetchTrips() {
      this.loading = true;
      try {
        const response = await apiClient.get("/api/trips");
        this.trips = response.data.data || [];
        if (this.routeTripId) {
          await this.selectTrip(this.routeTripId);
        } else {
          this.selectedTrip = null;
          this.tripLoadError = "";
        }
      } catch (error) {
        console.error("無法載入旅行資料", error);
        this.trips = [];
        this.selectedTrip = null;
      } finally {
        this.loading = false;
      }
    },
    async fetchManagedTrips() {
      try {
        const response = await apiClient.get("/api/trips?include_archived=true&include_deleted=true");
        this.managedTrips = response.data.data || [];
      } catch (error) {
        console.error("無法載入旅行管理資料", error);
        this.managedTrips = [];
      }
    },
    async toggleTripManagement() {
      this.showTripManagement = !this.showTripManagement;
      if (this.showTripManagement) {
        await this.fetchManagedTrips();
      }
    },
    async selectTrip(tripId) {
      this.tripLoadError = "";
      if (this.selectedTrip?.id !== tripId) this.tripRates = null;
      try {
        const response = await apiClient.get(`/api/trips/${tripId}/overview`);
        this.applyTripOverview(response.data.data);
        this.fetchTripRates();
        // An empty trip opens on the form; otherwise the expense list comes first.
        this.activeSection = this.canCreateTripTransaction && !(this.tripTransactionSummary.total_count > 0)
          ? "expense" : "transactions";
        await this.ensureActiveSectionData(this.activeSection);
        // The overview leaves suggestions out for speed; the banner loads them without blocking.
        if (!this.splitDetailsLoaded && this.selectedTrip.members.length > 1) this.fetchSplitState();
      } catch (error) {
        console.error("無法載入旅行明細", error);
        this.selectedTrip = null;
        this.tripLoadError = error.response?.data?.message || "旅行資料載入失敗，請稍後再試。";
      }
    },
    returnToTripList() {
      this.showTripSwitcher = false;
      this.selectedTrip = null;
      this.$router.push({ name: "Trips" });
    },
    applyTripOverview(overview) {
      this.selectedTrip = overview.trip;
      this.tripTransactions = overview.transactions || [];
      this.tripTransactionPagination = overview.transaction_pagination || {
        next_cursor: null,
        has_more: false,
        limit: 20,
        total_count: this.tripTransactions.length,
      };
      this.tripTransactionPager = resetCursorPager(this.tripTransactionPager);
      this.tripTransactionSummary = overview.transaction_summary || {
        total_count: this.tripTransactions.length,
        expense_count: this.tripTransactions.filter((item) => item.type === "expense").length,
        missing_split_count: 0,
        date_counts: [],
        category_totals: [],
      };
      this.isTripTransactionsLoading = false;
      this.tripTransactionLoadError = "";
      this.tripTransactionRetry = null;
      this.splitSummary = overview.split_summary || [];
      this.settlementSuggestions = overview.settlement_suggestions || [];
      this.settlementRecords = overview.settlements || [];
      this.settlementCommand = null;
      this.resetSettlementForm();
      this.restoreSettlementCommand();
      this.splitDetailsLoaded = false;
      this.inviteStatusLoaded = false;
      this.activeInvite = overview.invite || null;
      this.latestInviteUrl = "";
      this.selectedTransactionDetail = null;
      this.selectedTransactionDate = "all";
      this.showTripManagement = false;
      this.normalizeActiveSection();
      this.prepareExpenseDefaults();
      this.expenseCommand = null;
      this.legacyExpenseId = '';
      this.expenseCommandError = '';
      this.expenseMessage = '';
      this.restoreExpenseCommand();
      this.memberMessage = "";
      if (this.activeInvite) {
        this.inviteStatusLoaded = true;
        this.inviteMessage = "安全起見，既有邀請連結只在建立當下顯示；若遺失可關閉後重建。";
      } else {
        this.inviteMessage = "";
      }
    },
    async ensureActiveSectionData(section = this.activeSection) {
      if (!this.selectedTrip) return;
      if (section === "split" && !this.splitDetailsLoaded) {
        await this.fetchSplitState();
      }
      if (section === "members" && !this.inviteStatusLoaded) {
        await this.fetchTripInvite();
      }
    },
    async switchTrip(tripId) {
      this.showTripSwitcher = false;
      if (tripId === this.routeTripId) return;
      await this.$router.push({ name: "TripDetail", params: { tripId } });
    },
    async toggleSelectedTripReportScope() {
      if (!this.selectedTrip || this.updatingTripSettings) return;

      const nextPreference = this.currentMemberMonthlyReportPreference === "include" ? "exclude" : "include";
      const result = await this.$swal.fire({
        title: nextPreference === "include" ? "納入我的月報？" : "不納入我的月報？",
        text: nextPreference === "include"
          ? "你的分攤金額會出現在首頁、收支統計與預算中。"
          : "你的分攤金額將只保留在旅行帳本內，不併入個人月報。",
        icon: "question",
        showCancelButton: true,
        confirmButtonText: nextPreference === "include" ? "納入我的月報" : "不納入",
        cancelButtonText: "取消",
      });
      if (!result.isConfirmed) return;

      await this.updateMonthlyReportPreference(nextPreference);
    },
    async updateMonthlyReportPreference(preference) {
      if (!this.selectedTrip || this.updatingTripSettings) return;

      this.updatingTripSettings = true;
      try {
        const response = await apiClient.patch(`/api/trips/${this.selectedTrip.id}/members/me/monthly-report-preference`, {
          monthly_report_preference: preference,
        });
        const updatedTrip = response.data.data?.trip;
        if (updatedTrip) {
          this.selectedTrip = updatedTrip;
          this.trips = this.trips.map((trip) => (
            trip.id === updatedTrip.id ? { ...trip, ...updatedTrip } : trip
          ));
        }
        if (preference !== "pending") {
          this.$swal.fire("已更新", response.data.message || "個人月報偏好已更新。", "success");
        }
      } catch (error) {
        this.$swal.fire(
          "更新失敗",
          error.response?.data?.message || "請稍後再試。",
          "error"
        );
      } finally {
        this.updatingTripSettings = false;
      }
    },
    async addMember() {
      if (!this.selectedTrip) return;
      this.submittingMember = true;
      this.memberMessage = "";
      try {
        const response = await apiClient.post(
          `/api/trips/${this.selectedTrip.id}/members`,
          this.newMember
        );
        this.memberMessage = response.data.message;
        this.selectedTrip.members = [
          ...this.selectedTrip.members,
          response.data.data,
        ];
        this.newMember.display_name = "";
        this.newMember.role = "viewer";
        this.prepareExpenseDefaults();
      } catch (error) {
        this.memberMessage = error.response?.data?.message || "旅伴新增失敗";
      } finally {
        this.submittingMember = false;
      }
    },
    async deleteMember(member) {
      if (!this.selectedTrip) return;
      const result = await this.$swal.fire({
        title: "刪除旅伴？",
        text: `確定要刪除 ${member.display_name}？已有付款、分攤或結算紀錄的旅伴會被系統阻擋。`,
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "刪除",
        cancelButtonText: "取消",
      });
      if (!result.isConfirmed) return;

      try {
        const response = await apiClient.delete(
          `/api/trips/${this.selectedTrip.id}/members/${member.id}`
        );
        this.memberMessage = response.data.message;
        this.selectedTrip.members = this.selectedTrip.members.filter(
          (tripMember) => tripMember.id !== member.id
        );
        this.prepareExpenseDefaults();
      } catch (error) {
        this.$swal.fire(
          "刪除失敗",
          error.response?.data?.message || "旅伴刪除失敗，請稍後再試。",
          "error"
        );
      }
    },
    async updateMemberRole(member, role) {
      if (!this.selectedTrip || member.role === role) return;
      try {
        const response = await apiClient.patch(
          `/api/trips/${this.selectedTrip.id}/members/${member.id}/role`,
          { role }
        );
        this.memberMessage = response.data.message;
        this.selectedTrip.members = this.selectedTrip.members.map((tripMember) => (
          tripMember.id === member.id ? { ...tripMember, ...response.data.data } : tripMember
        ));
        this.normalizeActiveSection();
      } catch (error) {
        this.$swal.fire("更新失敗", error.response?.data?.message || "權限更新失敗", "error");
        await this.selectTrip(this.selectedTrip.id);
      }
    },
    async releaseMember(member) {
      const confirmed = await this.$swal.fire({
        title: `釋放「${member.display_name}」？`,
        text: "對方會失去這趟旅行的存取權，帳務紀錄仍留在這位旅伴上，之後可以讓別人認領。",
        icon: "question",
        showCancelButton: true,
        confirmButtonText: "釋放",
        cancelButtonText: "取消",
      });
      if (!confirmed.isConfirmed) return;
      try {
        await apiClient.post(`/api/trips/${this.selectedTrip.id}/members/${member.id}/release`);
        await this.selectTrip(this.selectedTrip.id);
      } catch (error) {
        this.$swal.fire("無法釋放", error.response?.data?.message || "請稍後再試。", "error");
      }
    },
    async renameMember(member) {
      if (!this.selectedTrip) return;
      const result = await this.$swal.fire({
        title: "修改旅伴名稱",
        input: "text",
        inputValue: member.display_name,
        inputAttributes: { maxlength: "40", "aria-label": "旅伴名稱" },
        showCancelButton: true,
        confirmButtonText: "儲存",
        cancelButtonText: "取消",
        inputValidator: (value) => (String(value || "").trim() ? undefined : "名稱不可為空"),
      });
      if (!result.isConfirmed || result.value.trim() === member.display_name) return;
      try {
        const response = await apiClient.patch(
          `/api/trips/${this.selectedTrip.id}/members/${member.id}`,
          { display_name: result.value }
        );
        this.memberMessage = response.data.message;
        // Names are copied into settlement rows and expense lists, so reload them.
        await this.selectTrip(this.selectedTrip.id);
      } catch (error) {
        this.$swal.fire("修改失敗", error.response?.data?.message || "名稱更新失敗", "error");
      }
    },
    async leaveSelectedTrip() {
      if (!this.selectedTrip || !this.currentTripMember) return;
      const result = await this.$swal.fire({
        title: "退出旅行帳本？",
        text: `退出後將不會在列表看到 ${this.selectedTrip.name}，有效邀請連結仍可重新加入。`,
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "退出",
        cancelButtonText: "取消",
      });
      if (!result.isConfirmed) return;

      try {
        await apiClient.post(`/api/trips/${this.selectedTrip.id}/leave`);
        await this.$router.push({ name: "Trips" });
        this.selectedTrip = null;
        await this.fetchTrips();
        this.$swal.fire("已退出", "你已離開此旅行帳本。", "success");
      } catch (error) {
        this.$swal.fire("退出失敗", error.response?.data?.message || "請稍後再試", "error");
      }
    },
    async fetchTripInvite() {
      this.activeInvite = null;
      this.latestInviteUrl = "";
      this.inviteMessage = "";
      if (!this.selectedTrip || !this.isTripOwner) {
        this.inviteStatusLoaded = true;
        return;
      }

      try {
        const response = await apiClient.get(`/api/trips/${this.selectedTrip.id}/invite`);
        this.activeInvite = response.data.data || null;
        if (this.activeInvite) {
          this.inviteMessage = "安全起見，既有邀請連結只在建立當下顯示；若遺失可關閉後重建。";
        }
        this.inviteStatusLoaded = true;
      } catch (error) {
        this.inviteMessage = error.response?.data?.message || "無法載入邀請狀態";
        this.inviteStatusLoaded = false;
      }
    },
    async createInvite() {
      if (!this.selectedTrip) return;
      this.submittingInvite = true;
      this.inviteMessage = "";
      try {
        const response = await apiClient.post(`/api/trips/${this.selectedTrip.id}/invite`, {
          role: "editor",
        });
        this.activeInvite = response.data.data;
        this.latestInviteUrl = this.activeInvite.invite_url || "";
        this.inviteStatusLoaded = true;
        this.inviteMessage = "邀請連結已建立，請複製後傳給旅伴。";
      } catch (error) {
        this.inviteMessage = error.response?.data?.message || "邀請連結建立失敗";
      } finally {
        this.submittingInvite = false;
      }
    },
    async closeInvite() {
      if (!this.selectedTrip) return;
      const result = await this.$swal.fire({
        title: "關閉邀請連結？",
        text: "關閉後，舊連結將無法再加入此帳本。",
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "關閉",
        cancelButtonText: "取消",
      });
      if (!result.isConfirmed) return;

      try {
        await apiClient.delete(`/api/trips/${this.selectedTrip.id}/invite`);
        this.activeInvite = null;
        this.latestInviteUrl = "";
        this.inviteStatusLoaded = true;
        this.inviteMessage = "邀請連結已關閉。";
      } catch (error) {
        this.inviteMessage = error.response?.data?.message || "邀請連結關閉失敗";
      }
    },
    async copyInviteLink() {
      if (!this.latestInviteUrl) return;
      try {
        await this.writeTextToClipboard(this.latestInviteUrl);
        this.$swal.fire("已複製", "邀請連結已複製到剪貼簿。", "success");
      } catch (error) {
        this.$swal.fire(copyDialogOptions(this.latestInviteUrl));
      }
    },
    async fetchExpenseCategories() {
      try {
        const response = await apiClient.get("/api/budgets/categories?include_meta=true");
        this.expenseCategories = (response.data.data || [])
          .filter((category) => category.kind === "expense" || category.kind === "both")
          .map((category) => category.name);
        if (!this.expenseCategories.includes(this.newExpense.budget_category)) {
          this.newExpense.budget_category = this.expenseCategories[0] || "伙食";
        }
      } catch (error) {
        console.error("無法載入交易類別", error);
        this.expenseCategories = ["伙食", "交通", "住宿", "購物", "娛樂", "醫療", "工作", "生活", "其他"];
      }
    },
    async fetchAssets() {
      try {
        const response = await apiClient.get("/api/assets");
        this.assets = response.data.data || {};
      } catch (error) {
        console.error("無法載入帳戶資料", error);
        this.assets = {};
      }
    },
    async loadNextTripTransactionPage() {
      if (!this.tripTransactionPagination.has_more || this.isTripTransactionsLoading) return;
      const loaded = await this.fetchTripTransactions(
        this.tripTransactionPagination.next_cursor,
        this.tripTransactionPager.page + 1
      );
      if (loaded) this.scrollTripTransactionsIntoView();
    },
    async loadPreviousTripTransactionPage() {
      if (this.tripTransactionPager.page <= 1 || this.isTripTransactionsLoading) return;
      const targetPage = this.tripTransactionPager.page - 1;
      const loaded = await this.fetchTripTransactions(
        cursorForPage(this.tripTransactionPager, targetPage),
        targetPage
      );
      if (loaded) this.scrollTripTransactionsIntoView();
    },
    async retryTripTransactionPage() {
      const retry = this.tripTransactionRetry;
      await this.fetchTripTransactions(
        retry?.cursor ?? cursorForPage(this.tripTransactionPager, this.tripTransactionPager.page),
        retry?.page ?? this.tripTransactionPager.page
      );
    },
    async selectTripTransactionDate(date) {
      if (date === this.selectedTransactionDate || this.isTripTransactionsLoading) return;
      this.selectedTransactionDate = date;
      this.tripTransactionPager = resetCursorPager(this.tripTransactionPager);
      await this.fetchTripTransactions();
    },
    async fetchTripTransactions(cursor = null, targetPage = 1) {
      if (!this.selectedTrip || this.isTripTransactionsLoading) return;
      this.isTripTransactionsLoading = true;
      this.tripTransactionLoadError = "";
      this.tripTransactionRetry = null;
      try {
        let requestedCursor = cursor;
        let requestedPage = targetPage;
        let response;
        while (true) {
          const params = {
            trip_id: this.selectedTrip.id,
            limit: this.tripTransactionPager.pageSize,
          };
          if (this.selectedTransactionDate !== "all") {
            params.date = this.selectedTransactionDate;
          }
          if (requestedCursor) {
            params.cursor = requestedCursor;
          }
          response = await apiClient.get("/api/transactions", { params });
          const incoming = response.data.data || [];
          const summary = response.data.trip_transaction_summary;
          const selectedDateStillExists = (summary?.date_counts || []).some(
            (item) => item.date === this.selectedTransactionDate
          );
          if (
            incoming.length === 0
            && this.selectedTransactionDate !== "all"
            && !selectedDateStillExists
          ) {
            this.selectedTransactionDate = "all";
            requestedPage = 1;
            requestedCursor = null;
            continue;
          }
          if (incoming.length > 0 || requestedPage === 1) break;
          requestedPage -= 1;
          requestedCursor = cursorForPage(this.tripTransactionPager, requestedPage);
        }

        this.tripTransactions = response.data.data || [];
        this.tripTransactionPagination = response.data.pagination || {
          next_cursor: null,
          has_more: false,
          limit: this.tripTransactionPager.pageSize,
          total_count: this.tripTransactions.length,
        };
        this.tripTransactionPager = recordCursorPage(
          this.tripTransactionPager,
          requestedPage,
          requestedCursor
        );
        if (response.data.trip_transaction_summary) {
          this.tripTransactionSummary = response.data.trip_transaction_summary;
        }
        this.syncSelectedTransactionDate();
        if (
          this.selectedTransactionDetail &&
          !this.tripTransactions.some((transaction) => transaction.id === this.selectedTransactionDetail.id)
        ) {
          this.selectedTransactionDetail = null;
        }
        this.tripTransactionRetry = null;
        return true;
      } catch (error) {
        console.error("無法載入旅行交易", error);
        this.tripTransactionRetry = { cursor, page: targetPage };
        if (targetPage === 1) {
          this.tripTransactions = [];
          this.tripTransactionPager = resetCursorPager(this.tripTransactionPager);
          this.tripTransactionPagination = {
            next_cursor: null,
            has_more: false,
            limit: this.tripTransactionPager.pageSize,
            total_count: 0,
          };
        }
        this.tripTransactionLoadError = error.response?.data?.message || "無法載入這一頁交易，請稍後再試。";
        return false;
      } finally {
        this.isTripTransactionsLoading = false;
      }
    },
    scrollTripTransactionsIntoView() {
      this.$nextTick(() => {
        this.$refs.tripTransactionsPanel?.$el?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      });
    },
    syncSelectedTransactionDate() {
      if (this.selectedTransactionDate === "all") return;
      const hasSelectedDate = this.tripTransactions.some(
        (transaction) => transaction.date === this.selectedTransactionDate
      );
      if (!hasSelectedDate) {
        this.selectedTransactionDate = "all";
      }
    },
    async loadTransactionDetail(transactionId, options = {}) {
      if (!options.force && this.selectedTransactionDetail && this.selectedTransactionDetail.id === transactionId) {
        this.selectedTransactionDetail = null;
        return;
      }

      try {
        const response = await apiClient.get(`/api/transactions/${transactionId}`);
        this.selectedTransactionDetail = response.data.data;
      } catch (error) {
        this.$swal.fire("載入失敗", error.response?.data?.message || "請稍後再試", "error");
      }
    },
    async startEditTransaction(transactionId) {
      try {
        if (this.settlementRecords.length > 0) {
          const result = await this.$swal.fire({
            title: "此旅行已有確認結算",
            text: "修改交易可能會影響剩餘待收/待付金額，但不會自動撤銷已確認付款。",
            icon: "warning",
            showCancelButton: true,
            confirmButtonText: "仍要編輯",
            cancelButtonText: "取消",
          });
          if (!result.isConfirmed) return;
        }

        const response = await apiClient.get(`/api/transactions/${transactionId}`);
        const transaction = response.data.data;
        if (transaction.can_edit === false) {
          await this.fetchTripTransactions();
          this.$swal.fire("沒有編輯權限", "你目前只能檢視這筆交易。", "warning");
          return;
        }
        const splitMethod = transaction.splits[0]?.split_method || "equal";

        this.editingTransactionId = transaction.id;
        this.newExpense.date = transaction.date;
        this.newExpense.item = transaction.category;
        this.newExpense.merchant = transaction.merchant || "";
        this.newExpense.budget_category = transaction.budget_category;
        this.newExpense.amount = transaction.amount;
        this.newExpense.original_currency = transaction.currency;
        this.newExpense.exchange_rate = transaction.exchange_rate;
        this.newExpense.paid_by_member_id = transaction.paid_by_member_id || "";
        this.newExpense.account_id = transaction.account_id || "";
        this.newExpense.description = transaction.description || "";
        this.newExpense.review_status = transaction.review_status || "confirmed";
        this.newExpense.split_mode = splitMethod === "custom" ? "custom" : "equal";
        this.newExpense.split_member_ids = transaction.splits.map((split) => split.trip_member_id);
        this.newExpense.split_allocations = transaction.splits.reduce((allocations, split) => {
          allocations[split.trip_member_id] = split.share_amount;
          return allocations;
        }, {});
        this.selectedTransactionDetail = transaction;
        this.showExpenseAdvanced = true;
        this.showSplitMemberOptions = false;
        this.activeSection = "expense";
      } catch (error) {
        this.$swal.fire("載入失敗", error.response?.data?.message || "請稍後再試", "error");
      }
    },
    cancelEditExpense() {
      this.resetExpenseForm();
      this.expenseMessage = "";
    },
    async fetchSplitSummary() {
      if (!this.selectedTrip) return;
      try {
        const response = await apiClient.get(`/api/trips/${this.selectedTrip.id}/split-summary`);
        this.splitSummary = response.data.data || [];
      } catch (error) {
        console.error("無法載入分帳狀態", error);
        this.splitSummary = [];
      }
    },
    async fetchSplitState() {
      if (!this.selectedTrip) return;
      const tripId = this.selectedTrip.id;
      try {
        const response = await apiClient.get(`/api/trips/${tripId}/split-state`);
        if (this.selectedTrip?.id !== tripId) return;
        const splitState = response.data.data || {};
        this.splitSummary = splitState.split_summary || [];
        this.settlementSuggestions = splitState.settlement_suggestions || [];
        this.settlementRecords = splitState.settlements || [];
        this.splitDetailsLoaded = true;
      } catch (error) {
        console.error("無法載入分帳狀態", error);
        this.splitDetailsLoaded = false;
      }
    },
    invalidateSplitDetails() {
      this.splitDetailsLoaded = false;
      this.settlementSuggestions = [];
      this.settlementRecords = [];
      // The result banner needs fresh suggestions; load them in the background.
      this.fetchSplitState();
    },
    async fetchSettlementSuggestions() {
      if (!this.selectedTrip) return;
      try {
        const response = await apiClient.get(`/api/trips/${this.selectedTrip.id}/settlement-suggestions`);
        this.settlementSuggestions = response.data.data || [];
      } catch (error) {
        console.error("無法載入建議結算", error);
        this.settlementSuggestions = [];
      }
    },
    async fetchSettlements() {
      if (!this.selectedTrip) return;
      try {
        const response = await apiClient.get(`/api/trips/${this.selectedTrip.id}/settlements`);
        this.settlementRecords = response.data.data || [];
      } catch (error) {
        console.error("無法載入已確認結算", error);
        this.settlementRecords = [];
      }
    },
    prepareExpenseDefaults() {
      if (!this.selectedTrip) return;
      const owner = this.selectedTrip.members.find((member) => member.role === "owner");
      this.newExpense.original_currency = this.selectedTrip.default_currency;
      this.applyDefaultExchangeRate();
      this.newExpense.paid_by_member_id = owner ? owner.id : this.selectedTrip.members[0]?.id || "";
      if (this.selectedTrip.current_member_id) {
        this.newExpense.paid_by_member_id = this.selectedTrip.current_member_id;
      }
      if (
        this.newExpense.account_id &&
        !this.compatibleTripAccounts.some((account) => account.id === this.newExpense.account_id)
      ) {
        this.newExpense.account_id = "";
      }
      if (!this.newExpense.account_id && this.isCurrentUserPayer) {
        this.newExpense.account_id = defaultAccountId("trip", this.compatibleTripAccounts, {
          requiredCurrency: this.newExpense.original_currency,
        });
      }
      this.newExpense.split_member_ids = this.getDefaultSplitMemberIds();
      this.initializeCustomSplitAllocations();
    },
    tripCover,
    tripDaysElapsed,
    tripTimeLabel,
    async fetchTripRates() {
      const tripId = this.selectedTrip?.id;
      if (!tripId) return;
      try {
        const response = await apiClient.get(`/api/trips/${tripId}/exchange-rates`);
        const data = response.data?.data;
        if (this.selectedTrip?.id === tripId && Array.isArray(data?.rates)) {
          this.tripRates = data;
          // An untouched form follows the trip's rate as soon as it is known.
          if (!this.editingTransactionId) this.applyDefaultExchangeRate();
        }
      } catch (error) {
        console.error("無法載入旅行匯率", error);
      }
    },
    async setTripRate(row) {
      const base = this.tripRates.base_currency;
      const answer = await this.$swal.fire({
        title: `${row.currency} 對 ${base} 的匯率`,
        text: `1 ${row.currency} = ? ${base}。只影響之後新增的支出，已記的不會變動。`,
        input: "text",
        inputValue: row.rate || row.default_rate || "",
        inputAttributes: { inputmode: "decimal", autocomplete: "off" },
        showCancelButton: true,
        confirmButtonText: "儲存",
        cancelButtonText: "取消",
        inputValidator: (value) => (/^\d+(\.\d{1,8})?$/.test(String(value || "").trim()) && Number(value) > 0
          ? undefined : "請輸入大於 0 的數字（最多 8 位小數）"),
      });
      if (!answer.isConfirmed) return;
      this.ratesBusy = true;
      try {
        const response = await apiClient.put(
          `/api/trips/${this.selectedTrip.id}/exchange-rates/${row.currency}`, { rate: answer.value.trim() });
        await this.fetchTripRates();
        const different = response.data.data.different_count;
        this.$swal.fire(
          "匯率已更新",
          different > 0
            ? `已記的 ${different} 筆 ${row.currency} 支出沒有變動。需要的話，可以按「套用到已記的支出」。`
            : "之後新增的支出會自動使用這個匯率。",
          "success",
        );
      } catch (error) {
        this.$swal.fire("無法更新匯率", error.response?.data?.message || "請稍後再試。", "error");
      } finally {
        this.ratesBusy = false;
      }
    },
    buildRatePreview(preview) {
      // Member names are user content: assigned as text, never parsed as dialog HTML.
      const box = document.createElement("div");
      box.className = "rate-preview";
      const line = (text, bold = false) => {
        const element = document.createElement(bold ? "strong" : "p");
        element.textContent = text;
        box.appendChild(element);
      };
      const base = preview.base_currency;
      line(`共 ${preview.count} 筆 ${preview.currency} 支出，總額 ${formatAmount(preview.old_total, base)} → ${formatAmount(preview.new_total, base)} ${base}`);
      if (preview.members.length) {
        line("每個人的結算變化（正數＝多拿回，負數＝多付）", true);
        preview.members.forEach((member) => {
          const value = Number(member.change);
          const sign = value > 0 ? "+" : "−";
          line(`${member.display_name || "旅伴"}：${sign}${formatAmount(Math.abs(value), base)} ${base}`);
        });
      }
      if (preview.account_adjustment_count > 0) {
        line(`其中 ${preview.account_adjustment_count} 筆連動了付款人的 ${base} 帳戶，餘額會同步調整 ${formatAmount(preview.account_adjustment_total, base)} ${base}。`);
      }
      line("套用後，這幾筆支出和分帳都會改用新匯率。若要再改，需要重新套用另一個匯率。");
      return box;
    },
    async applyTripRate(row) {
      this.ratesBusy = true;
      try {
        const preview = (await apiClient.get(
          `/api/trips/${this.selectedTrip.id}/exchange-rates/${row.currency}/apply-preview`)).data.data;
        if (preview.locked) {
          this.$swal.fire("無法套用", "這趟旅行已經有還款紀錄，已記的支出不能再改動匯率。", "info");
          return;
        }
        if (preview.count === 0) {
          this.$swal.fire("不需要套用", `已記的 ${row.currency} 支出都已經是這個匯率。`, "info");
          return;
        }
        const answer = await this.$swal.fire({
          title: `把 ${preview.rate} 套用到已記的支出？`,
          html: this.buildRatePreview(preview),
          icon: "warning",
          showCancelButton: true,
          confirmButtonText: `套用到 ${preview.count} 筆`,
          cancelButtonText: "取消",
        });
        if (!answer.isConfirmed) return;
        await apiClient.post(
          `/api/trips/${this.selectedTrip.id}/exchange-rates/${row.currency}/apply`, { confirm: true });
        this.invalidateSplitDetails();
        const section = this.activeSection;
        await this.selectTrip(this.selectedTrip.id);
        this.activeSection = section; // stay on the settings tab the owner was using
        this.$swal.fire("已套用", `${preview.count} 筆支出已改用新匯率。`, "success");
      } catch (error) {
        this.$swal.fire("無法套用", error.response?.data?.message || "請稍後再試。", "error");
      } finally {
        this.ratesBusy = false;
      }
    },
    async updateCoverTheme(theme) {
      if (!this.selectedTrip || this.updatingTripSettings || theme === this.selectedTrip.cover_theme) return;
      const previous = this.selectedTrip.cover_theme;
      this.selectedTrip.cover_theme = theme;
      this.updatingTripSettings = true;
      try {
        await apiClient.patch(`/api/trips/${this.selectedTrip.id}`, { cover_theme: theme });
      } catch (error) {
        this.selectedTrip.cover_theme = previous;
        this.$swal.fire("封面更新失敗", error.response?.data?.message || "請稍後再試。", "error");
      } finally {
        this.updatingTripSettings = false;
      }
    },
    openExpenseForm() {
      this.activeSection = "expense";
      window.scrollTo({ top: 0, behavior: "smooth" });
    },
    buildExpensePayload() {
      const splitAllocations = Object.entries(this.newExpense.split_allocations || {})
        .map(([memberId, amount]) => ({
          trip_member_id: memberId,
          amount: Number(amount || 0),
        }))
        .filter((allocation) => allocation.amount > 0);

      return {
        date: this.newExpense.date,
        item: this.newExpense.item,
        amount: this.newExpense.amount,
        type: "expense",
        budget_category: this.newExpense.budget_category,
        description: this.newExpense.description,
        review_status: this.newExpense.review_status,
        trip_id: this.selectedTrip.id,
        paid_by_member_id: this.newExpense.paid_by_member_id,
        account_id: this.newExpense.account_id,
        merchant: this.newExpense.merchant,
        original_currency: this.newExpense.original_currency,
        exchange_rate: this.newExpense.exchange_rate,
        timezone: this.selectedTrip.timezone,
        split_member_ids: this.newExpense.split_mode === "equal" ? this.newExpense.split_member_ids : undefined,
        split_allocations: this.newExpense.split_mode === "custom" ? splitAllocations : undefined,
      };
    },
    resetExpenseForm() {
      this.newExpense.item = "";
      this.newExpense.merchant = "";
      this.newExpense.amount = null;
      this.newExpense.description = "";
      this.newExpense.review_status = "confirmed";
      this.editingTransactionId = null;
      this.showExpenseAdvanced = false;
      this.showSplitMemberOptions = false;
      this.prepareExpenseDefaults();
    },
    async restoreExpenseCommand() {
      const tripId = this.selectedTrip?.id;
      const epoch = ++this.expenseCommandEpoch;
      this.expenseCommandLoading = true;
      try {
        const command = await openPendingCommand(`transaction:trip:${tripId}`);
        if (this.selectedTrip?.id !== tripId || epoch !== this.expenseCommandEpoch) return;
        this.expenseCommand = command;
      } catch {
        if (this.selectedTrip?.id === tripId && epoch === this.expenseCommandEpoch) {
          this.expenseCommandError = '無法讀取待確認請求，請先核對紀錄並確認瀏覽器儲存可用。';
        }
      } finally {
        if (this.selectedTrip?.id === tripId && epoch === this.expenseCommandEpoch) this.expenseCommandLoading = false;
      }
    },
    acknowledgeExpensePending() {
      if (!this.legacyExpenseId || this.submittingExpense || !this.expenseCommand?.pending) return;
      try {
        this.expenseCommand.clear();
        this.legacyExpenseId = '';
        this.expenseMessage = '';
        this.resetExpenseForm();
      } catch { this.expenseCommandError = '無法清除本機待確認狀態；既有交易未被修改，請確認瀏覽器儲存可用。'; }
    },
    async addTripExpense() {
      if (this.submittingExpense || this.expenseCommandLoading || this.expenseCommandError || !this.selectedTrip) return;
      this.submittingExpense = true;
      const tripId = this.selectedTrip.id;
      const editingId = this.editingTransactionId;
      let command = this.expenseCommand;
      let sent = false;
      let requestId;
      try {
        let intent;
        if (editingId || !command?.pending) {
          const validationMessage = this.validateTripExpenseForm();
          if (validationMessage) { this.expenseMessage = validationMessage; return; }
          // Freeze the validated click intent before any confirmation/auth await.
          intent = JSON.parse(JSON.stringify(this.buildExpensePayload()));
          if (this.shouldConfirmExchangeRate()) {
            const result = await this.$swal.fire({
              title: "確認匯率？",
              text: `${this.newExpense.original_currency} 與 ${this.selectedTrip.base_currency} 不同，但目前匯率為 1。請確認是否仍要送出。`,
              icon: "warning", showCancelButton: true, confirmButtonText: "仍要送出", cancelButtonText: "返回修改",
            });
            if (!result.isConfirmed) return;
          }
        } else {
          intent = JSON.parse(JSON.stringify(command.pending.payload));
        }
        if (this.selectedTrip?.id !== tripId) return;
        let payload;
        if (editingId) payload = intent;
        else {
          command = command || await openPendingCommand(`transaction:trip:${tripId}`);
          if (this.selectedTrip?.id !== tripId) return;
          this.expenseCommand = command;
          await command.verifyOwner();
          if (this.selectedTrip?.id !== tripId) return;
          payload = command.prepare(intent);
          requestId = payload.client_request_id;
        }
        sent = true;
        const response = editingId
          ? await apiClient.put(`/api/transactions/${editingId}`, payload)
          : await apiClient.post('/api/transactions', payload, { headers: { 'X-Nomica-Request-Owner': command.ownerId } });
        if (response.data?.success !== true) throw new Error('結果尚未確認');
        if (!editingId) command.clear(requestId);
        if (!editingId && payload.paid_by_member_id === this.selectedTrip?.current_member_id) {
          rememberLastAccount("trip", payload.account_id);
        }
        if (this.selectedTrip?.id !== tripId) return;
        this.legacyExpenseId = '';
        this.expenseMessage = response.data.message;
        this.resetExpenseForm();
        if (this.activeSection === 'split') {
          await Promise.all([this.fetchTripTransactions(), this.fetchSplitState(), this.fetchAssets()]);
        } else {
          await Promise.all([this.fetchTripTransactions(), this.fetchSplitSummary(), this.fetchAssets()]);
          this.invalidateSplitDetails();
        }
        if (this.selectedTrip?.id !== tripId) return;
        if (this.selectedTransactionDetail) await this.loadTransactionDetail(this.selectedTransactionDetail.id, { force: true });
        this.activeSection = 'transactions';
      } catch (error) {
        if (!editingId && sent && error.response?.status === 400) command?.clear(requestId);
        if (this.selectedTrip?.id !== tripId) return;
        if (error.ownerChanged || error.response?.data?.code === 'REQUEST_OWNER_CHANGED') {
          this.expenseCommandError = error.response?.data?.message || error.message;
        } else if (!editingId && command?.pending) {
          this.expenseMessage = error.response?.data?.message || '結果尚未確認，請以保留的原資料重試。';
          this.legacyExpenseId = error.response?.data?.code === 'LEGACY_REQUEST_UNVERIFIABLE'
            ? String(error.response.data.data?.transaction_id || '') : '';
        } else if (!editingId && !sent) {
          this.expenseCommandError = '無法保存待確認請求，未送出交易。請確認瀏覽器儲存可用後重試。';
        } else {
          this.$swal.fire(editingId ? '更新失敗' : '新增失敗', error.response?.data?.message || '旅行支出儲存失敗，請稍後再試。', 'error');
        }
      } finally { this.submittingExpense = false; }
    },
    validateTripExpenseForm() {
      if (!this.newExpense.paid_by_member_id) {
        return "請選擇付款人。";
      }
      if (this.newExpense.split_mode === "equal" && this.newExpense.split_member_ids.length === 0) {
        return "請至少選擇一位分帳成員。";
      }
      if (this.newExpense.split_mode === "custom") {
        if (this.customSplitTotal <= 0) {
          return "請輸入自訂分帳金額。";
        }
        if (this.customSplitDifference !== 0) {
          return `自訂分帳合計需等於交易金額，目前差額 ${this.formatMoney(this.customSplitDifference, this.newExpense.original_currency)}。`;
        }
      }
      return "";
    },
    shouldConfirmExchangeRate() {
      return (
        this.newExpense.original_currency !== this.selectedTrip.base_currency &&
        Number(this.newExpense.exchange_rate) === 1
      );
    },
    async deleteTripTransaction(transaction) {
      try {
        const permissionResponse = await apiClient.get(`/api/transactions/${transaction.id}`);
        if (permissionResponse.data.data?.can_delete === false) {
          await this.fetchTripTransactions();
          this.$swal.fire("沒有刪除權限", "你目前只能檢視這筆交易。", "warning");
          return;
        }
      } catch (error) {
        this.$swal.fire("檢查權限失敗", error.response?.data?.message || "請稍後再試", "error");
        return;
      }

      const result = await this.$swal.fire({
        title: "刪除交易？",
        text: `${transaction.category} · ${this.formatMoney(transaction.amount, transaction.currency)}`,
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "刪除",
        cancelButtonText: "取消",
      });
      if (!result.isConfirmed) return;

      try {
        await apiClient.delete(`/api/transactions/${transaction.id}`);
        if (this.activeSection === "split") {
          await Promise.all([
            this.fetchTripTransactions(),
            this.fetchSplitState(),
            this.fetchAssets(),
          ]);
        } else {
          await Promise.all([
            this.fetchTripTransactions(),
            this.fetchSplitSummary(),
            this.fetchAssets(),
          ]);
          this.invalidateSplitDetails();
        }
      } catch (error) {
        this.$swal.fire("刪除失敗", error.response?.data?.message || "請稍後再試", "error");
      }
    },
    resetSettlementForm() {
      if (this.settlementCommand?.pending) {
        this.settlementForm = { id: null, ...this.settlementCommand.pending.payload };
        return;
      }
      this.settlementForm = {
        id: null,
        from_member_id: "",
        to_member_id: "",
        amount: "",
        settled_on: this.tripToday(),
      };
    },
    tripToday() {
      return new Date().toLocaleDateString("sv-SE", {
        timeZone: this.selectedTrip?.timezone || "Asia/Taipei",
      });
    },
    selectSettlementSuggestion(suggestion) {
      if (this.settlementCommand?.pending) {
        this.resetSettlementForm();
        this.focusSettlementAmount();
        return;
      }
      this.settlementForm = {
        id: null,
        from_member_id: suggestion.from_member_id,
        to_member_id: suggestion.to_member_id,
        amount: suggestion.amount,
        settled_on: this.tripToday(),
      };
      this.focusSettlementAmount();
    },
    editSettlement(settlement) {
      if (this.settlementCommand?.pending) {
        this.resetSettlementForm();
        return;
      }
      this.settlementForm = {
        id: settlement.id,
        from_member_id: settlement.from_member_id,
        to_member_id: settlement.to_member_id,
        amount: settlement.amount,
        settled_on: settlement.settled_on || this.tripToday(),
      };
      this.focusSettlementAmount();
    },
    focusSettlementAmount() {
      this.$nextTick(() => {
        const input = this.$el.querySelector(".settlement-form input[type='number']");
        input?.scrollIntoView({ behavior: "smooth", block: "center" });
        input?.focus({ preventScroll: true });
      });
    },
    async restoreSettlementCommand() {
      const tripId = this.selectedTrip?.id;
      if (!tripId) return;
      try {
        const command = await openPendingCommand(`settlement:${tripId}`);
        if (this.selectedTrip?.id !== tripId || this.settlementCommand) return;
        this.settlementCommand = command;
        if (command.pending) this.settlementForm = { id: null, ...command.pending.payload };
      } catch (error) {
        console.error('無法載入待確認的還款', error);
      }
    },
    async saveSettlement() {
      if (this.submittingSettlement || !this.selectedTrip) return;
      this.submittingSettlement = true;
      const tripId = this.selectedTrip.id;
      try {
        if (this.settlementForm.id) {
          await apiClient.patch(`/api/trips/${tripId}/settlements/${this.settlementForm.id}`, {
            amount: this.settlementForm.amount,
            settled_on: this.settlementForm.settled_on,
          });
        } else {
          const command = this.settlementCommand || await openPendingCommand(`settlement:${tripId}`);
          if (this.selectedTrip?.id !== tripId) return;
          this.settlementCommand = command;
          const payload = command.prepare({
            from_member_id: this.settlementForm.from_member_id,
            to_member_id: this.settlementForm.to_member_id,
            amount: this.settlementForm.amount,
            settled_on: this.settlementForm.settled_on,
          });
          await apiClient.post(`/api/trips/${tripId}/settlements`, payload);
          command.clear();
        }
        this.resetSettlementForm();
        await this.fetchSplitState();
      } catch (error) {
        if (error.response?.status === 400) this.settlementCommand?.clear();
        if (this.settlementCommand?.pending) this.resetSettlementForm();
        this.$swal.fire("儲存失敗", error.response?.data?.message || (this.settlementCommand?.pending
          ? "結果尚未確認，已保留原資料，請重試這筆還款。" : error.message || "請稍後再試"), "error");
        await this.fetchSplitState();
      } finally {
        this.submittingSettlement = false;
      }
    },
    settlementAccountOptions(currency, { allowSkip = false } = {}) {
      const options = {};
      if (allowSkip) {
        options.__none__ = "只更新分帳狀態，不異動帳戶";
      }
      Object.values(this.assets || {})
        .filter((asset) => (
          asset.currency === currency
          && asset.track_balance !== false
          && asset.is_active !== false
        ))
        .sort((left, right) => (left.bank_name || "").localeCompare(right.bank_name || "", "zh-TW"))
        .forEach((asset) => {
          options[asset.id] = `${asset.bank_name} · ${asset.currency} ${Number(asset.balance || 0).toLocaleString("zh-TW")}`;
        });
      const realOptionCount = Object.keys(options).length - (allowSkip ? 1 : 0);
      if (realOptionCount === 0) return null;
      return options;
    },
    async postSettlementAccountEntry(settlement) {
      const accountOptions = this.settlementAccountOptions(settlement.currency);
      if (!accountOptions) {
        this.$swal.fire(
          "沒有可用帳戶",
          `請先建立並啟用一個 ${settlement.currency} 餘額追蹤帳戶。`,
          "info"
        );
        return;
      }

      const direction = this.selectedTrip?.current_member_id === settlement.from_member_id
        ? "扣除付款"
        : "加入收款";
      const result = await this.$swal.fire({
        title: `${direction}帳戶`,
        text: `${settlement.from_display_name} → ${settlement.to_display_name} ${this.formatMoney(settlement.amount, settlement.currency)}`,
        input: "select",
        inputOptions: accountOptions,
        inputPlaceholder: "選擇你的帳戶",
        inputValidator: (value) => (!value ? "請選擇帳戶" : undefined),
        showCancelButton: true,
        confirmButtonText: "記入帳戶",
        cancelButtonText: "取消",
      });
      if (!result.isConfirmed) return;

      try {
        await apiClient.post(
          `/api/trips/${this.selectedTrip.id}/settlements/${settlement.id}/account-entry`,
          { account_id: result.value }
        );
        await Promise.all([this.fetchSplitState(), this.fetchAssets()]);
      } catch (error) {
        this.$swal.fire("入帳失敗", error.response?.data?.message || "請稍後再試", "error");
      }
    },
    async reverseSettlementAccountEntry(settlement) {
      const result = await this.$swal.fire({
        title: "取消私人帳戶入帳？",
        text: "只會反轉你自己的帳戶餘額，不會撤銷群組結算。",
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "取消入帳",
        cancelButtonText: "保留",
      });
      if (!result.isConfirmed) return;

      try {
        await apiClient.delete(
          `/api/trips/${this.selectedTrip.id}/settlements/${settlement.id}/account-entry`,
          { data: { reason: "使用者從旅行結算頁取消入帳" } }
        );
        await Promise.all([this.fetchSplitState(), this.fetchAssets()]);
      } catch (error) {
        this.$swal.fire("取消失敗", error.response?.data?.message || "請稍後再試", "error");
      }
    },
    async deleteSettlement(settlement) {
      const result = await this.$swal.fire({
        title: "撤銷結算？",
        text: `${settlement.from_display_name} 付給 ${settlement.to_display_name} ${this.formatMoney(settlement.amount, settlement.currency)}`,
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "撤銷",
        cancelButtonText: "取消",
      });
      if (!result.isConfirmed) return;

      try {
        await apiClient.delete(`/api/trips/${this.selectedTrip.id}/settlements/${settlement.id}`);
        await this.fetchSplitState();
      } catch (error) {
        this.$swal.fire("撤銷失敗", error.response?.data?.message || "請稍後再試", "error");
      }
    },
    buildSettlementSummaryText() {
      if (!this.selectedTrip) return "";
      return buildSettlementSummary({
        trip: this.selectedTrip,
        total: this.tripExpenseTotal,
        members: this.splitSummary,
        suggestions: this.settlementSuggestions,
        settlements: this.settlementRecords,
        rates: this.tripRates?.rates || [],
        formatMoney: this.formatMoney,
      });
    },
    async writeTextToClipboard(text) {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        return;
      }

      const textarea = document.createElement("textarea");
      textarea.value = text;
      textarea.setAttribute("readonly", "");
      textarea.style.position = "fixed";
      textarea.style.top = "-9999px";
      textarea.style.left = "-9999px";
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();

      const copied = document.execCommand("copy");
      document.body.removeChild(textarea);
      if (!copied) {
        throw new Error("copy command failed");
      }
    },
    async copySettlementSummary() {
      const text = this.buildSettlementSummaryText();
      if (!text) return;

      try {
        await this.writeTextToClipboard(text);
        this.$swal.fire("已複製", "結算摘要已複製到剪貼簿。", "success");
      } catch (error) {
        this.$swal.fire(copyDialogOptions(text));
      }
    },
    async archiveSelectedTrip() {
      if (!this.selectedTrip) return;
      const result = await this.$swal.fire({
        title: "封存旅行帳本？",
        text: `${this.selectedTrip.name} 會保留資料，但不再作為主要操作帳本。`,
        icon: "question",
        showCancelButton: true,
        confirmButtonText: "封存帳本",
        cancelButtonText: "取消",
      });
      if (!result.isConfirmed) return;

      try {
        await apiClient.post(`/api/trips/${this.selectedTrip.id}/archive`);
        await this.$router.push({ name: "Trips" });
        await this.fetchTrips();
        await this.fetchManagedTrips();
        this.showTripManagement = true;
        this.$swal.fire("已封存", "可在旅行管理的已封存帳本中解除封存。", "success");
      } catch (error) {
        this.$swal.fire("封存失敗", error.response?.data?.message || "請稍後再試", "error");
      }
    },
    async deleteSelectedTrip() {
      if (!this.selectedTrip) return;
      const result = await this.$swal.fire({
        title: "刪除旅行帳本？",
        // Render the shared trip name as text to prevent stored HTML injection.
        text: `會先保留 30 天。若要刪除，請輸入帳本名稱：${this.selectedTrip.name}`,
        input: "text",
        inputPlaceholder: this.selectedTrip.name,
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "刪除帳本",
        cancelButtonText: "取消",
        preConfirm: (value) => {
          if (value !== this.selectedTrip.name) {
            this.$swal.showValidationMessage("請輸入完整旅行名稱");
            return false;
          }
          return value;
        },
      });
      if (!result.isConfirmed) return;

      try {
        await apiClient.delete(`/api/trips/${this.selectedTrip.id}`);
        await this.$router.push({ name: "Trips" });
        await this.fetchTrips();
        await this.fetchManagedTrips();
        this.showTripManagement = true;
        this.$swal.fire("已移至暫存區", "30 天內可在旅行管理的已刪除帳本中復原。", "success");
      } catch (error) {
        this.$swal.fire("刪除失敗", error.response?.data?.message || "請稍後再試", "error");
      }
    },
    async unarchiveTrip(trip) {
      const result = await this.$swal.fire({
        title: "解除封存？",
        text: `${trip.name} 會回到主要旅行帳本列表。`,
        icon: "question",
        showCancelButton: true,
        confirmButtonText: "解除封存",
        cancelButtonText: "取消",
      });
      if (!result.isConfirmed) return;

      try {
        await apiClient.post(`/api/trips/${trip.id}/unarchive`);
        await this.fetchTrips();
        await this.fetchManagedTrips();
        this.showTripManagement = true;
        this.$swal.fire("已解除封存", `${trip.name} 已回到主要旅行帳本列表。`, "success");
      } catch (error) {
        this.$swal.fire("解除封存失敗", error.response?.data?.message || "請稍後再試", "error");
      }
    },
    async restoreTrip(trip) {
      const result = await this.$swal.fire({
        title: "復原旅行帳本？",
        text: `${trip.name} 會回到原本狀態。`,
        icon: "question",
        showCancelButton: true,
        confirmButtonText: "復原",
        cancelButtonText: "取消",
      });
      if (!result.isConfirmed) return;

      try {
        await apiClient.post(`/api/trips/${trip.id}/restore`);
        await this.fetchTrips();
        await this.fetchManagedTrips();
        this.showTripManagement = true;
        this.$swal.fire("已復原", `${trip.name} 已回到旅行帳本。`, "success");
      } catch (error) {
        this.$swal.fire("復原失敗", error.response?.data?.message || "請稍後再試", "error");
      }
    },
    formatRange(trip) {
      return `${trip.start_date} - ${trip.end_date}`;
    },
    tripCurrentMember(trip) {
      if (!trip?.current_member_id) return null;
      return (trip.members || []).find((member) => member.id === trip.current_member_id) || null;
    },
    tripReportPreference(trip) {
      return this.tripCurrentMember(trip)?.monthly_report_preference || null;
    },
    tripReportPreferenceClass(trip) {
      return {
        included: this.tripReportPreference(trip) === "include",
        pending: this.tripReportPreference(trip) === "pending",
      };
    },
    tripReportLabel(trip) {
      const preference = this.tripReportPreference(trip);
      if (preference === "include") return "計入我的月報";
      if (preference === "exclude") return "不計入我的月報";
      if (preference === "pending") return "尚未決定";
      return trip?.include_in_monthly_report ? "舊設定：計入月報" : "尚未設定";
    },
    formatDateChip(dateString) {
      if (!dateString) return "";
      const parts = String(dateString).split("-");
      if (parts.length !== 3) return dateString;
      const month = Number(parts[1]);
      const day = Number(parts[2]);
      if (!Number.isFinite(month) || !Number.isFinite(day)) return dateString;
      return `${month}/${day}`;
    },
    formatDateTime(value) {
      if (!value) return "";
      return new Date(value).toLocaleDateString("zh-TW", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
      });
    },
    tripDays(trip) {
      const start = new Date(trip.start_date);
      const end = new Date(trip.end_date);
      const diff = end.getTime() - start.getTime();
      return Math.max(Math.round(diff / 86400000) + 1, 1);
    },
    getMemberName(memberId) {
      if (!memberId || !this.selectedTrip) return "";
      const member = this.selectedTrip.members.find((item) => item.id === memberId);
      return member?.display_name || "";
    },
    escapeCsvValue(value) {
      const text = value === null || value === undefined ? "" : String(value);
      return `"${text.replace(/"/g, '""')}"`;
    },
    buildTripTransactionsCsvFrom(transactions) {
      const headers = [
        "日期",
        "品項",
        "店家",
        "類別",
        "付款人",
        "原幣金額",
        "原幣",
        "匯率",
        "換算金額",
        "本幣",
        "付款帳戶",
        "備註",
      ];
      const rows = transactions.map((transaction) => [
        transaction.date,
        transaction.category,
        transaction.merchant || "",
        transaction.budget_category || "",
        this.getMemberName(transaction.paid_by_member_id),
        transaction.amount,
        transaction.currency,
        transaction.exchange_rate,
        transaction.converted_amount,
        transaction.base_currency,
        transaction.account_name || "",
        transaction.description || "",
      ]);
      return [headers, ...rows]
        .map((row) => row.map((value) => this.escapeCsvValue(value)).join(","))
        .join("\n");
    },
    async fetchAllTripTransactionsForExport() {
      const transactions = [];
      const seenIds = new Set();
      const seenCursors = new Set();
      let cursor = null;
      let hasMore = true;

      while (hasMore) {
        const params = {
          trip_id: this.selectedTrip.id,
          limit: 50,
        };
        if (cursor) params.cursor = cursor;

        const response = await apiClient.get("/api/transactions", { params });
        const incoming = response.data.data || [];
        incoming.forEach((transaction) => {
          if (!seenIds.has(transaction.id)) {
            seenIds.add(transaction.id);
            transactions.push(transaction);
          }
        });

        const pagination = response.data.pagination || {};
        const nextCursor = pagination.next_cursor || null;
        hasMore = pagination.has_more === true && Boolean(nextCursor);
        if (hasMore && seenCursors.has(nextCursor)) {
          throw new Error("交易分頁游標重複，已停止匯出");
        }
        if (nextCursor) seenCursors.add(nextCursor);
        cursor = nextCursor;
      }

      return transactions;
    },
    downloadCsv(csv) {
      const blob = new Blob([`\uFEFF${csv}`], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      const safeName = this.selectedTrip.name.replace(/[\\/:*?"<>|]/g, "_");
      link.href = url;
      link.download = `${safeName}-transactions.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    },
    async exportTripTransactionsCsv() {
      if (!this.selectedTrip || this.tripTransactions.length === 0) return;

      this.$swal.fire({
        title: "正在整理完整交易資料",
        text: "交易較多時可能需要一些時間。",
        allowOutsideClick: false,
        didOpen: () => this.$swal.showLoading(),
      });

      let allTransactions;
      try {
        allTransactions = await this.fetchAllTripTransactionsForExport();
      } catch (error) {
        console.error("無法匯出完整旅行交易", error);
        this.$swal.fire("匯出失敗", "無法取得完整交易資料，請稍後再試。", "error");
        return;
      }

      const csv = this.buildTripTransactionsCsvFrom(allTransactions);
      this.downloadCsv(csv);

      const result = await this.$swal.fire({
        title: "CSV 已產生",
        text: "如果瀏覽器沒有跳出下載，可能是目前測試瀏覽器限制下載行為，可以改用複製 CSV 內容。",
        icon: "success",
        showCancelButton: true,
        confirmButtonText: "複製 CSV",
        cancelButtonText: "完成",
      });
      if (!result.isConfirmed) return;

      try {
        await this.writeTextToClipboard(csv);
        this.$swal.fire("已複製", "CSV 內容已複製到剪貼簿。", "success");
      } catch (error) {
        this.$swal.fire(copyDialogOptions(csv));
      }
    },
    formatMoney(amount, currency) {
      const minorUnit = ["TWD", "JPY", "KRW"].includes(currency) ? 0 : 2;
      return `${currency} ${Number(amount || 0).toLocaleString("zh-TW", {
        minimumFractionDigits: minorUnit,
        maximumFractionDigits: minorUnit,
      })}`;
    },
  },
  created() {
    this.fetchExpenseCategories();
    this.fetchAssets();
    this.fetchTrips();
  },
};
</script>

<style scoped>
.trips-page {
  max-width: 720px;
  margin: 0 auto;
  min-height: calc(100vh - 80px);
  /* Room for the floating add button above the bottom navigation. */
  padding: 24px 16px calc(var(--app-bottom-nav-height) + env(safe-area-inset-bottom) + 110px);
  color: var(--text-color);
}

.trips-header,
.trip-hero,
.metric-item {
  display: flex;
  align-items: center;
}

.trips-header {
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.header-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
}

.eyebrow {
  margin: 0 0 4px;
  color: var(--light-text-color);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
}

h1,
h2,
h3 {
  margin: 0;
  letter-spacing: 0;
}

h1 {
  font-size: 2rem;
}

.icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 42px;
  border-radius: 8px;
  box-shadow: none;
}

.primary-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 42px;
}

.secondary-action,
.quiet-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 42px;
  border-radius: 8px;
  box-shadow: none;
}

.icon-button {
  width: 44px;
  padding: 0;
  color: var(--primary-color);
  background: var(--primary-soft);
}


:deep(.swal-copy-textarea) {
  width: 100%;
  min-height: 180px;
  padding: 10px 12px;
  color: var(--text-color);
  background: var(--secondary-color);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  font: inherit;
  line-height: 1.5;
  resize: vertical;
}

.metric-item svg,
.primary-action svg,
.secondary-action svg,
.icon-button svg {
  width: 18px;
  height: 18px;
}

.primary-action {
  align-self: end;
}

.secondary-action {
  background: var(--primary-color);
  color: var(--on-primary);
}

.quiet-action {
  color: var(--text-color);
  background: var(--border-color);
}

.loading-state,
.empty-state {
  margin: 12px 0 0;
  color: var(--light-text-color);
}

.trips-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 16px;
}

.trip-route-state {
  display: grid;
  justify-items: start;
  gap: 8px;
  padding: 18px;
  color: var(--light-text-color);
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-left: 4px solid var(--warning-color);
  border-radius: 8px;
}

.trip-route-state strong {
  color: var(--text-color);
}

.trip-detail {
  display: grid;
  gap: 16px;
  min-width: 0;
}

.current-trip-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 86px;
  padding: 12px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.current-trip-card > div {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.current-trip-actions {
  display: flex;
  flex: 0 0 auto;
  flex-direction: column;
  gap: 8px;
}

.current-trip-card strong {
  color: var(--text-color);
  font-size: 1rem;
}

.current-trip-card span {
  color: var(--light-text-color);
  font-size: 0.86rem;
}

.trip-compact-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 5px;
}

.trip-compact-meta span {
  min-height: 24px;
  padding: 3px 8px;
  color: var(--text-color);
  background: var(--secondary-color);
  border: 1px solid var(--border-color);
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 800;
}

.trip-state-badge {
  justify-self: start;
  min-height: 26px;
  padding: 4px 8px;
  color: var(--light-text-color);
  background: var(--secondary-color);
  border: 1px solid var(--border-color);
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 800;
}

.trip-state-badge.included {
  color: var(--primary-color);
  background: var(--income-soft);
  border-color: var(--brand-border);
}

.trip-state-badge.pending {
  color: var(--warning-color);
  background: var(--warning-soft);
  border-color: var(--warning-color);
}

.monthly-preference-panel {
  display: grid;
  gap: 12px;
  padding: 14px;
  margin-top: 12px;
  background: var(--warning-soft);
  border: 1px solid var(--warning-color);
  border-radius: 8px;
}

.monthly-preference-panel strong {
  color: var(--warning-color);
  font-size: 0.98rem;
}

.monthly-preference-panel p {
  margin: 4px 0 0;
  color: var(--warning-color);
  font-size: 0.84rem;
  line-height: 1.45;
}

.monthly-preference-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.trip-hero {
  justify-content: space-between;
  gap: 12px;
  padding: 14px;
  color: #ffffff;
  background: #247e8f;
  border-radius: 16px;
}

.trip-hero .eyebrow {
  color: var(--primary-soft);
}

.trip-hero p {
  margin: 6px 0 0;
}

.currency-pill {
  flex: 0 0 auto;
  padding: 8px 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.18);
  font-weight: 800;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.metric-item {
  gap: 8px;
  min-height: 54px;
  padding: 10px;
  color: var(--text-color);
  background: var(--secondary-color);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  font-weight: 700;
}

.trip-tabs {
  position: sticky;
  top: 74px;
  z-index: 5;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(0, 1fr));
  gap: 6px;
  padding: 6px;
  background: var(--border-color);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.trip-tabs button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 42px;
  padding: 0 8px;
  color: var(--light-text-color);
  background: transparent;
  border-radius: 6px;
  box-shadow: none;
  font-size: 0.92rem;
}

.trip-tabs button.active {
  color: var(--primary-color);
  background: var(--card-bg);
}

.trip-tabs svg {
  width: 17px;
  height: 17px;
}

.app-panel {
  display: none;
}

.app-panel.active {
  display: block;
}

@media (max-width: 820px) {
  .trips-page {
    padding: 18px 12px calc(var(--app-bottom-nav-height) + 22px);
  }

  .trips-layout,
  .metric-grid {
    grid-template-columns: 1fr;
  }

  .trip-hero {
    align-items: flex-start;
    flex-direction: column;
  }

  .trips-header {
    align-items: flex-start;
  }

  .trips-header h1 {
    font-size: 1.6rem;
  }

  .header-actions {
    gap: 6px;
  }

  .current-trip-card {
    align-items: stretch;
    flex-direction: column;
    min-height: auto;
  }

  .current-trip-actions,
  .current-trip-card .quiet-action,
  .current-trip-card .secondary-action {
    width: 100%;
  }

  .trip-tabs {
    top: 0;
    margin: 0 -4px;
  }

  .trip-tabs button {
    flex-direction: column;
    gap: 2px;
    min-height: 50px;
    padding: 4px 2px;
    font-size: 0.78rem;
  }

}
.trip-head {
  margin-bottom: 16px;
}

.trip-cover {
  position: relative;
  display: grid;
  gap: 2px;
  margin-top: 6px;
  padding: 40px 16px 16px;
  border-radius: 14px;
  color: #ffffff;
}

.trip-cover h1 {
  margin: 0;
  font-size: 1.6rem;
  line-height: 1.25;
}

.trip-cover .trip-meta {
  color: #ffffff;
  opacity: 0.92;
}

.cover-tag {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 3px 10px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.22);
  font-size: 0.78rem;
  font-weight: 700;
}

.settings-row--stack {
  display: block;
  padding: 12px 2px;
}

.back-link,
.text-button {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  min-height: 40px;
  padding: 0;
  color: var(--light-text-color);
  background: transparent;
  border: 0;
  font-weight: 600;
}

.back-link svg {
  width: 16px;
  height: 16px;
}

.trip-meta {
  margin: 0;
  color: var(--light-text-color);
  font-size: 0.88rem;
}

.trip-alert {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-height: 44px;
  margin-bottom: 10px;
  padding: 0 14px;
  border: 1px solid var(--warning-color);
  border-radius: 10px;
  color: var(--warning-text);
  background: var(--warning-soft);
  font-weight: 600;
  text-align: left;
}

.trip-alert svg {
  width: 16px;
  height: 16px;
}

.expense-form-head {
  display: flex;
  justify-content: flex-end;
  margin-bottom: -40px;
}

.trip-settings {
  display: grid;
  margin-top: 12px;
  border-top: 1px solid var(--border-color);
}

.settings-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 60px;
  padding: 8px 2px;
  border-bottom: 1px solid var(--border-color);
}

.settings-row span {
  display: grid;
  gap: 2px;
}

.settings-row small {
  color: var(--light-text-color);
  font-size: 0.82rem;
}

.trip-fab {
  position: fixed;
  right: 16px;
  /* Clear the nav's raised centre button and the phone's home-indicator inset. */
  bottom: calc(var(--app-bottom-nav-height) + env(safe-area-inset-bottom) + 24px);
  z-index: 15;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 48px;
  padding: 0 18px;
  border: 0;
  border-radius: 999px;
  color: var(--on-primary);
  background: var(--primary-color);
  font-weight: 700;
}

.trip-fab svg {
  width: 18px;
  height: 18px;
}

@media (min-width: 1024px) {
  .trip-fab {
    bottom: 24px;
  }
}
</style>
