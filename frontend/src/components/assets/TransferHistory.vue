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
      </article>
    </div>
  </section>
</template>

<script>
export default {
  name: "TransferHistory",
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
</style>
