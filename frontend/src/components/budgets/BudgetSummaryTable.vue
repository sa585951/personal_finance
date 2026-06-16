<template>
  <section class="budget-summary">
    <div class="summary-header">
      <div>
        <h2>日常預算總覽</h2>
        <span>{{ selectedMonth }}</span>
      </div>
      <select :value="selectedMonth" @change="handleMonthChange">
        <option disabled value="">請選擇月份</option>
        <option v-for="month in availableMonths" :key="month" :value="month">
          {{ month }}
        </option>
      </select>
    </div>

    <div v-if="budgetSummary.length > 0" class="budget-list">
      <section class="overspend-alert" :class="{ clear: overspentItems.length === 0 }">
        <div>
          <span>{{ overspentItems.length > 0 ? "超支提醒" : "目前無超支" }}</span>
          <strong>
            {{ overspentItems.length > 0 ? formatMoney(totalOverspent) : "控制良好" }}
          </strong>
        </div>
        <p v-if="overspentItems.length > 0">
          {{ overspentItems.length }} 個分類已超出預算，最高超支是 {{ topOverspentItem.category }}。
        </p>
        <p v-else>
          {{ selectedMonth }} 的預算目前都在範圍內。
        </p>
        <div v-if="overspentItems.length > 0" class="overspend-list">
          <article
            v-for="item in topOverspentItems"
            :key="`overspend-${item.category}`"
            class="overspend-item"
          >
            <span>{{ item.category }}</span>
            <strong>超支 {{ formatMoney(Math.abs(item.remaining)) }}</strong>
          </article>
        </div>
      </section>

      <article v-for="item in budgetSummary" :key="item.category" class="budget-card">
        <div class="card-top">
          <div>
            <h3>{{ item.category }}</h3>
            <span :class="{ overspend: item.remaining < 0 }">
              {{ item.remaining < 0 ? "超支" : "良好" }}
            </span>
          </div>
          <strong>{{ formatMoney(item.remaining) }}</strong>
        </div>

        <div class="budget-values">
          <div>
            <span>已花費</span>
            <strong>{{ formatMoney(item.spent) }}</strong>
          </div>
          <div>
            <span>預算</span>
            <strong>{{ item.budget ? formatMoney(item.budget) : "未設定" }}</strong>
          </div>
        </div>

        <div class="progress-bar-container">
          <div
            class="progress-bar"
            :style="{ width: calculateProgress(item) + '%' }"
            :class="{ overbudget: item.remaining < 0 }"
          ></div>
        </div>

        <p v-if="item.notes" class="notes">{{ item.notes }}</p>

        <div class="card-actions">
          <button class="update-btn" type="button" @click="promptEditBudget(item)">
            編輯
          </button>
          <button class="delete-btn" type="button" @click="promptDeleteBudget(item.category)">
            刪除
          </button>
        </div>
      </article>
    </div>
    <p v-else class="no-data">該月無預算或支出資料。</p>
  </section>
</template>

<script>
import apiClient from '@/api';

export default {
  name: "BudgetSummaryTable",
  props: {
    selectedMonth: {
      type: String,
      required: true,
    },
  },
  emits: ["update-month", "update-budget"],
  data() {
    return {
      availableMonths: [],
      budgetSummary: [],
    };
  },
  computed: {
    overspentItems() {
      return this.budgetSummary.filter((item) => Number(item.remaining || 0) < 0);
    },
    totalOverspent() {
      return this.overspentItems.reduce(
        (sum, item) => sum + Math.abs(Number(item.remaining || 0)),
        0
      );
    },
    sortedOverspentItems() {
      return [...this.overspentItems].sort(
        (a, b) => Math.abs(Number(b.remaining || 0)) - Math.abs(Number(a.remaining || 0))
      );
    },
    topOverspentItems() {
      return this.sortedOverspentItems.slice(0, 3);
    },
    topOverspentItem() {
      return this.topOverspentItems[0] || { category: "" };
    },
  },
  methods: {
    handleMonthChange(event) {
      this.$emit("update-month", event.target.value);
    },
    async fetchBudgetSummary() {
      if (!this.selectedMonth) return;
      try {
        const response = await apiClient.get(
          `/api/budgets/summary/${this.selectedMonth}`
        );
        this.budgetSummary = response.data.data;
      } catch (error) {
        console.error("無法載入預算總覽", error);
        this.budgetSummary = [];
      }
    },
    async fetchAvailableMonths() {
      try {
        const response = await apiClient.get(`/api/months`);
        this.availableMonths = response.data.data;
      } catch (error) {
        console.error("無法載入可用月份", error);
      }
    },
    calculateProgress(item) {
      if (!item.budget || item.budget === 0) {
        return 0;
      }
      const progress = (item.spent / item.budget) * 100;
      return Math.min(progress, 100);
    },
    formatMoney(amount) {
      if (amount === null || amount === undefined) return "N/A";
      const sign = Number(amount) < 0 ? "-" : "";
      return `${sign}TWD ${Math.abs(Number(amount || 0)).toLocaleString("zh-TW", {
        maximumFractionDigits: 0,
      })}`;
    },
    async promptEditBudget(item) {
      const { value: formValues } = await this.$swal.fire({
        title: `編輯 ${item.category} 預算`,
        html:
          `<label for="swal-input1">預算金額:</label>` +
          `<input id="swal-input1" class="swal2-input" type="number" value="${item.budget}">` +
          `<label for="swal-input2">備註:</label>` +
          `<input id="swal-input2" class="swal2-input" value="${item.notes || ''}">`,
        focusConfirm: false,
        showCancelButton: true,
        confirmButtonText: "儲存",
        cancelButtonText: "取消",
        preConfirm: () => {
          const amount = parseFloat(this.$swal.getPopup().querySelector('#swal-input1').value);
          const notes = this.$swal.getPopup().querySelector('#swal-input2').value;

          if (isNaN(amount) || amount < 0) {
            this.$swal.showValidationMessage(`請輸入有效的非負數金額`);
            return false;
          }
          return { amount, notes };
        }
      });

      if (formValues) {
        this.$emit("update-budget", this.selectedMonth, item.category, formValues.amount, formValues.notes);
      }
    },
    async promptDeleteBudget(category) {
      const result = await this.$swal.fire({
        title: "確定刪除？",
        text: `確定要刪除「${this.selectedMonth}」月份的「${category}」預算嗎？`,
        icon: "warning",
        showCancelButton: true,
        confirmButtonColor: "#d33",
        cancelButtonColor: "#3085d6",
        confirmButtonText: "確定刪除",
        cancelButtonText: "取消",
      });

      if (result.isConfirmed) {
        try {
          const response = await apiClient.delete(
            `/api/budgets/${this.selectedMonth}/${category}`
          );
          this.$swal.fire("刪除成功！", response.data.message, "success");
          this.fetchBudgetSummary();
        } catch (error) {
          console.error("刪除預算失敗:", error);
          this.$swal.fire("刪除失敗！", "刪除失敗，請稍後再試。", "error");
        }
      }
    },
  },
  watch: {
    selectedMonth(newMonth, oldMonth) {
      if (newMonth !== oldMonth) {
        this.fetchBudgetSummary();
      }
    },
  },
  created() {
    this.fetchAvailableMonths();
  },
};
</script>

<style scoped>
.budget-summary {
  display: grid;
  gap: 12px;
}

.summary-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px;
  background: #ffffff;
  border: 1px solid #dbe4ee;
  border-radius: 10px;
}

.summary-header div {
  display: grid;
  gap: 2px;
}

.summary-header h2,
.budget-card h3 {
  margin: 0;
  letter-spacing: 0;
}

.summary-header h2 {
  color: #1f2933;
  font-size: 1.08rem;
}

.summary-header span {
  color: #64748b;
  font-size: 0.86rem;
  font-weight: 700;
}

select {
  min-height: 40px;
  max-width: 150px;
  padding: 0.5rem 0.7rem;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background-color: #fff;
}

.budget-list {
  display: grid;
  gap: 10px;
}

.overspend-alert {
  display: grid;
  gap: 8px;
  padding: 14px;
  border: 1px solid #fecaca;
  border-left: 4px solid #dc2626;
  border-radius: 10px;
  background: #fef2f2;
  color: #991b1b;
}

.overspend-alert.clear {
  border-color: #bbf7d0;
  border-left-color: #16a34a;
  background: #f0fdf4;
  color: #166534;
}

.overspend-alert div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.overspend-alert span,
.overspend-alert strong {
  font-weight: 900;
}

.overspend-alert p {
  margin: 0;
  color: inherit;
  font-size: 0.86rem;
  line-height: 1.45;
}

.overspend-list {
  display: grid;
  gap: 6px;
}

.overspend-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 10px;
  color: #991b1b;
  background: rgba(255, 255, 255, 0.64);
  border: 1px solid #fecaca;
  border-radius: 8px;
}

.overspend-item span,
.overspend-item strong {
  min-width: 0;
  font-size: 0.84rem;
}

.overspend-item span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.overspend-item strong {
  flex-shrink: 0;
  white-space: nowrap;
}

.budget-card {
  display: grid;
  gap: 12px;
  padding: 14px;
  background: #ffffff;
  border: 1px solid #dbe4ee;
  border-radius: 10px;
}

.card-top,
.card-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.card-top div {
  display: grid;
  gap: 2px;
}

.card-top h3 {
  color: #1f2933;
  font-size: 1rem;
}

.card-top span {
  color: #0f766e;
  font-size: 0.86rem;
  font-weight: 700;
}

.card-top .overspend {
  color: #dc2626;
}

.card-top > strong {
  color: #1f2933;
  text-align: right;
}

.budget-values {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.budget-values div {
  display: grid;
  gap: 3px;
  min-height: 58px;
  padding: 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.budget-values span {
  color: #64748b;
  font-size: 0.82rem;
  font-weight: 700;
}

.progress-bar-container {
  width: 100%;
  height: 10px;
  background-color: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background-color: #0f766e;
  transition: width 0.3s ease-in-out;
}

.progress-bar.overbudget {
  background-color: #dc2626;
}

.notes {
  margin: 0;
  color: #64748b;
  font-size: 0.9rem;
}

.card-actions {
  justify-content: flex-end;
}

.delete-btn,
.update-btn {
  min-height: 36px;
  padding: 0 12px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  box-shadow: none;
}

.delete-btn {
  color: #dc2626;
  background-color: #fee2e2;
}

.update-btn {
  color: #ffffff;
  background-color: #2563eb;
}

.no-data {
  text-align: center;
  padding: 2rem;
  color: #64748b;
  background-color: #ffffff;
  border: 1px solid #dbe4ee;
  border-radius: 8px;
}
</style>
