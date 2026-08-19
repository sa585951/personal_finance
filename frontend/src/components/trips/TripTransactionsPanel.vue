<template>
  <div class="trip-transactions-panels">
    <section class="transactions-section">
      <div class="section-title split-title-row">
        <div>
          <List />
          <h3>旅行交易</h3>
        </div>
        <button
          v-if="transactions.length > 0"
          class="copy-summary-button"
          type="button"
          @click="$emit('export')"
        >
          匯出 CSV
        </button>
      </div>

      <div
        v-if="dateFilters.length > 1"
        class="transaction-date-tabs"
        aria-label="旅行交易日期篩選"
      >
        <button
          v-for="filter in dateFilters"
          :key="filter.key"
          type="button"
          :class="{ active: selectedDate === filter.key }"
          @click="$emit('select-date', filter.key)"
        >
          <span>{{ filter.label }}</span>
          <small>{{ filter.count }} 筆</small>
        </button>
      </div>

      <div v-if="missingSplitCount > 0" class="split-warning">
        <strong>{{ missingSplitCount }} 筆支出缺少分帳設定</strong>
        <p>需完成分攤設定後，這些支出才會依個人分攤金額納入月報。</p>
      </div>

      <div v-if="transactions.length === 0" class="empty-state">尚未新增旅行支出</div>
      <div v-else-if="filteredTransactions.length === 0" class="empty-state">這一天尚無旅行支出</div>
      <div v-else class="transaction-list">
        <div
          v-for="transaction in filteredTransactions"
          :key="transaction.id"
          class="transaction-row"
          :class="{ selected: selectedTransaction && selectedTransaction.id === transaction.id }"
          @click="$emit('select-transaction', transaction.id)"
        >
          <div class="transaction-description">
            <strong>{{ transaction.category }}</strong>
            <span>{{ transaction.date }} · {{ transaction.merchant || transaction.budget_category }}</span>
          </div>
          <div class="transaction-amount">
            <span>{{ formatMoney(transaction.amount, transaction.currency) }}</span>
            <small>{{ formatMoney(transaction.converted_amount, transaction.base_currency) }}</small>
          </div>
          <button
            v-if="transaction.can_delete !== false"
            class="transaction-delete"
            type="button"
            title="刪除交易"
            @click.stop="$emit('delete-transaction', transaction)"
          >
            <Delete />
          </button>
          <button
            v-if="transaction.can_edit !== false"
            class="transaction-edit"
            type="button"
            title="編輯交易"
            @click.stop="$emit('edit-transaction', transaction.id)"
          >
            <Edit />
          </button>
        </div>
      </div>
    </section>

    <section v-if="selectedTransaction" class="transaction-detail-section">
      <div class="section-title">
        <Document />
        <h3>交易明細</h3>
      </div>
      <div class="detail-grid">
        <div>
          <span>品項</span>
          <strong>{{ selectedTransaction.category }}</strong>
        </div>
        <div>
          <span>付款人</span>
          <strong>{{ selectedTransaction.paid_by_member?.display_name || "未設定" }}</strong>
        </div>
        <div>
          <span>記錄者</span>
          <strong>{{ selectedTransaction.created_by_display_name || "未設定" }}</strong>
        </div>
        <div>
          <span>確認狀態</span>
          <strong>{{ translateReviewStatus(selectedTransaction.review_status) }}</strong>
        </div>
        <div>
          <span>原幣金額</span>
          <strong>{{ formatMoney(selectedTransaction.amount, selectedTransaction.currency) }}</strong>
        </div>
        <div>
          <span>換算金額</span>
          <strong>{{ formatMoney(selectedTransaction.converted_amount, selectedTransaction.base_currency) }}</strong>
        </div>
        <div>
          <span>此筆成本</span>
          <strong>{{ formatMyShare(selectedTransaction) }}</strong>
        </div>
        <div>
          <span>匯率</span>
          <strong>{{ selectedTransaction.exchange_rate }}</strong>
        </div>
        <div>
          <span>類別</span>
          <strong>{{ selectedTransaction.budget_category }}</strong>
        </div>
        <div class="full-row">
          <span>備註</span>
          <strong>{{ selectedTransaction.description || "無" }}</strong>
        </div>
      </div>

      <div class="split-detail-list">
        <div
          v-for="split in selectedTransaction.splits"
          :key="split.id"
          class="split-detail-row"
        >
          <span>{{ split.display_name }}</span>
          <strong>
            {{ formatMoney(split.share_amount, split.share_currency) }}
            <small>{{ formatMoney(split.converted_share_amount, split.base_currency) }}</small>
          </strong>
        </div>
      </div>
    </section>
  </div>
</template>

<script>
import { Delete, Document, Edit, List } from "@element-plus/icons-vue";

export default {
  name: "TripTransactionsPanel",
  components: { Delete, Document, Edit, List },
  props: {
    transactions: { type: Array, default: () => [] },
    filteredTransactions: { type: Array, default: () => [] },
    dateFilters: { type: Array, default: () => [] },
    selectedDate: { type: String, default: "all" },
    missingSplitCount: { type: Number, default: 0 },
    selectedTransaction: { type: Object, default: null },
    currentMemberId: { type: String, default: "" },
  },
  emits: [
    "delete-transaction",
    "edit-transaction",
    "export",
    "select-date",
    "select-transaction",
  ],
  methods: {
    formatMoney(amount, currency) {
      const minorUnit = ["TWD", "JPY", "KRW"].includes(currency) ? 0 : 2;
      return `${currency} ${Number(amount || 0).toLocaleString("zh-TW", {
        minimumFractionDigits: minorUnit,
        maximumFractionDigits: minorUnit,
      })}`;
    },
    formatMyShare(transaction) {
      if (!this.currentMemberId) return "尚未對應";
      const split = transaction.splits.find(
        (item) => item.trip_member_id === this.currentMemberId
      );
      if (!split) return "未分攤";
      return this.formatMoney(split.converted_share_amount, split.base_currency);
    },
    translateReviewStatus(status) {
      const statusMap = {
        confirmed: "已確認",
        pending: "待確認",
      };
      return statusMap[status] || status || "未設定";
    },
  },
};
</script>

<style scoped>
.trip-transactions-panels {
  display: grid;
  gap: 16px;
}

.section-title,
.split-title-row > div {
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-title {
  margin-bottom: 14px;
  color: #334155;
}

.section-title h3 {
  margin: 0;
  letter-spacing: 0;
}

.section-title svg {
  width: 18px;
  height: 18px;
}

.split-title-row {
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 12px;
}

.split-title-row > div {
  min-width: 0;
}

.copy-summary-button {
  flex: 0 0 auto;
  min-height: 34px;
  padding: 0 10px;
  color: #0f766e;
  background: #ccfbf1;
  border: 0;
  border-radius: 8px;
  box-shadow: none;
  font-size: 0.84rem;
  font-weight: 800;
}

.transaction-date-tabs {
  position: relative;
  z-index: 1;
  display: flex;
  gap: 8px;
  clear: both;
  margin: 4px 0 14px;
  padding: 2px 0 4px;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}

.transaction-date-tabs::-webkit-scrollbar {
  display: none;
}

.transaction-date-tabs button {
  display: grid;
  gap: 2px;
  flex: 0 0 auto;
  min-width: 68px;
  min-height: 48px;
  padding: 6px 10px;
  color: #475569;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  box-shadow: none;
}

.transaction-date-tabs button.active {
  color: #ffffff;
  background: #0f766e;
  border-color: #0f766e;
}

.transaction-date-tabs span {
  font-size: 0.86rem;
  font-weight: 900;
}

.transaction-date-tabs small {
  font-size: 0.72rem;
  font-weight: 800;
  opacity: 0.82;
}

.split-warning {
  display: grid;
  gap: 4px;
  padding: 12px;
  margin-bottom: 12px;
  color: #92400e;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
}

.split-warning strong {
  font-size: 0.92rem;
}

.split-warning p {
  margin: 0;
  font-size: 0.82rem;
  line-height: 1.45;
}

.empty-state {
  margin: 12px 0 0;
  color: #475569;
}

.transaction-list {
  display: grid;
  gap: 8px;
}

.transaction-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  min-height: 62px;
  padding: 10px 12px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  cursor: pointer;
}

.transaction-row.selected {
  background: #f0fdfa;
  border-color: #0f766e;
}

.transaction-description,
.transaction-amount {
  display: grid;
  gap: 2px;
}

.transaction-description {
  min-width: 0;
}

.transaction-description span,
.transaction-amount small {
  color: #64748b;
}

.transaction-amount {
  flex: 0 0 auto;
  text-align: right;
}

.transaction-amount span {
  color: #111827;
  font-weight: 800;
}

.transaction-delete,
.transaction-edit {
  flex: 0 0 38px;
  width: 38px;
  min-height: 38px;
  padding: 0;
  border: 0;
  border-radius: 8px;
  box-shadow: none;
}

.transaction-delete {
  color: #dc2626;
  background: #fee2e2;
}

.transaction-edit {
  color: #0f766e;
  background: #ccfbf1;
}

.transaction-delete svg,
.transaction-edit svg {
  width: 18px;
  height: 18px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}

.detail-grid > div {
  display: grid;
  gap: 2px;
  min-height: 54px;
  padding: 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.detail-grid span,
.split-detail-row span,
.split-detail-row small {
  color: #64748b;
}

.full-row {
  grid-column: 1 / -1;
}

.split-detail-list {
  display: grid;
  gap: 8px;
}

.split-detail-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  min-height: 48px;
  padding: 10px 12px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.split-detail-row strong {
  display: grid;
  gap: 2px;
  text-align: right;
}

@media (max-width: 820px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }

  .transaction-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto 38px 38px;
    align-items: center;
    gap: 8px;
  }

  .transaction-description span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}
</style>
