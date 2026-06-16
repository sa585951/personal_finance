<template>
  <section class="transfer-history">
    <div class="section-heading">
      <strong>最近資金分配</strong>
      <span>{{ transfers.length }} 筆</span>
    </div>

    <p v-if="!transfers.length" class="empty-hint">
      尚無轉帳紀錄。
    </p>

    <div v-else class="transfer-list">
      <article
        v-for="transfer in transfers"
        :key="transfer.id"
        class="transfer-item"
      >
        <div class="transfer-main">
          <div>
            <strong>{{ transfer.source_name }}</strong>
            <span>轉入 {{ transfer.target_name }}</span>
          </div>
          <strong>{{ formatMoney(transfer.target_amount, transfer.target_currency) }}</strong>
        </div>
        <div class="transfer-meta">
          <span>{{ formatDate(transfer.transfer_date) }}</span>
          <span>{{ translateAccountType(transfer.target_type) }}</span>
          <span v-if="transfer.note">{{ transfer.note }}</span>
        </div>
        <div class="transfer-actions">
          <button type="button" @click="$emit('edit-transfer', transfer)">編輯</button>
          <button type="button" class="danger" @click="$emit('delete-transfer', transfer)">刪除</button>
        </div>
      </article>
    </div>
  </section>
</template>

<script>
export default {
  name: "TransferHistory",
  emits: ["edit-transfer", "delete-transfer"],
  props: {
    transfers: {
      type: Array,
      default: () => [],
    },
  },
  methods: {
    formatMoney(amount, currency) {
      return `${currency || "TWD"} ${Number(amount || 0).toLocaleString()}`;
    },
    formatDate(dateValue) {
      if (!dateValue) return "";
      return String(dateValue).slice(0, 10);
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
.transfer-history {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #1f2937;
}

.section-heading span {
  color: #64748b;
  font-size: 0.86rem;
}

.empty-hint {
  margin: 0;
  color: #64748b;
}

.transfer-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.transfer-item {
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
}

.transfer-main,
.transfer-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.transfer-main div {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.transfer-main span,
.transfer-meta {
  color: #64748b;
  font-size: 0.86rem;
}

.transfer-meta {
  justify-content: flex-start;
  flex-wrap: wrap;
  margin-top: 8px;
}

.transfer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 10px;
}

.transfer-actions button {
  min-height: 34px;
  padding: 0 12px;
  color: #334155;
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  box-shadow: none;
  font-size: 0.88rem;
}

.transfer-actions .danger {
  color: #b91c1c;
  border-color: #fecaca;
  background: #fef2f2;
}
</style>
