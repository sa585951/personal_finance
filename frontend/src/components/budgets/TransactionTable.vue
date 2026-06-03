<template>
  <div>
    <div v-if="transactions.length > 0" class="transaction-list">
      <article
        v-for="transaction in transactions"
        :key="transaction.id"
        class="transaction-card"
      >
        <div class="transaction-main">
          <span :class="['type-chip', transaction.type === 'income' ? 'income' : 'expense']">
            {{ translateType(transaction.type) }}
          </span>
          <div>
            <strong>{{ transaction.category }}</strong>
            <span>{{ formatDate(transaction.date) }} · {{ transaction.budget_category }}</span>
            <span v-if="transaction.account_name" class="account-line">
              帳戶 {{ transaction.account_name }}
            </span>
          </div>
        </div>
        <div class="transaction-side">
          <strong :class="transaction.type === 'income' ? 'income-amount' : 'expense-amount'">
            {{ formatMoney(transaction.amount, transaction.currency) }}
          </strong>
          <span v-if="transaction.description">{{ transaction.description }}</span>
        </div>
        <button
          class="delete-btn"
          type="button"
          @click="promptDeleteTransaction(transaction.id)"
        >
          刪除
        </button>
      </article>
    </div>
    <div v-else class="no-data">目前沒有交易記錄</div>
  </div>
</template>

<script>
import apiClient from '@/api';

export default {
  name: "TransactionTable",
  props: {
    transactions: {
      type: Array,
      required: true,
    },
  },
  methods: {
    formatDate(dateString) {
      if (!dateString) return "";
      const date = new Date(dateString);
      const month = date.getMonth() + 1;
      const day = date.getDate();
      return `${month}月${day}日`;
    },
    translateType(type) {
      return type === "income" ? "收入" : "支出";
    },
    formatMoney(amount, currency = "TWD") {
      const minorUnit = ["TWD", "JPY", "KRW"].includes(currency) ? 0 : 2;
      return `${currency} ${Number(amount || 0).toLocaleString("zh-TW", {
        minimumFractionDigits: minorUnit,
        maximumFractionDigits: minorUnit,
      })}`;
    },
    async promptDeleteTransaction(id) {
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
        try {
          await apiClient.delete(`/api/transactions/${id}`);
          this.$swal.fire("刪除成功！", "交易已成功刪除。", "success");
          this.$emit("transaction-deleted");
        } catch (error) {
          console.error("刪除失敗:", error);
          this.$swal.fire(
            "刪除失敗！",
            error.response?.data?.message || "刪除交易失敗，請稍後再試。",
            "error"
          );
        }
      }
    },
  },
};
</script>

<style scoped>
.transaction-list {
  display: grid;
  gap: 10px;
}

.transaction-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 10px;
  min-height: 74px;
  padding: 12px;
  background-color: #ffffff;
  border: 1px solid #dbe4ee;
  border-radius: 8px;
}

.transaction-main {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.transaction-main div,
.transaction-side {
  display: grid;
  gap: 2px;
}

.transaction-main strong,
.transaction-main span,
.transaction-side span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.transaction-main span,
.transaction-side span {
  color: #64748b;
  font-size: 0.86rem;
}

.account-line {
  color: #0f766e;
  font-weight: 700;
}

.transaction-side {
  text-align: right;
}

.type-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 42px;
  min-height: 28px;
  border-radius: 6px;
  font-size: 0.82rem;
  font-weight: 800;
}

.delete-btn {
  min-height: 36px;
  padding: 0 10px;
  background-color: #fee2e2;
  color: #dc2626;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  box-shadow: none;
  transition: background-color 0.3s ease;
}

.delete-btn:hover {
  background-color: #fecaca;
}

.income-amount {
  color: #0f766e;
  font-weight: bold;
}

.expense-amount {
  color: #dc2626;
  font-weight: bold;
}

.type-chip.income {
  color: #0f766e;
  background: #ccfbf1;
}

.type-chip.expense {
  color: #dc2626;
  background: #fee2e2;
}

.no-data {
  text-align: center;
  padding: 2rem;
  color: #666;
  background-color: #ffffff;
  border: 1px solid #dbe4ee;
  margin-top: 1rem;
  border-radius: 8px;
}

@media (max-width: 560px) {
  .transaction-card {
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .delete-btn {
    grid-column: 1 / -1;
    justify-self: end;
  }
}
</style>
