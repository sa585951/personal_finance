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
      <section class="monthly-budget-card">
        <div>
          <span>本月預算狀態</span>
          <strong>{{ budgetUsageRate }}%</strong>
        </div>
        <div class="summary-progress">
          <div
            class="summary-progress-fill"
            :class="{ overbudget: totalRemaining < 0 }"
            :style="{ width: summaryProgressWidth + '%' }"
          ></div>
        </div>
        <div class="budget-metrics">
          <div>
            <span>總預算</span>
            <strong>{{ formatMoney(totalBudget) }}</strong>
          </div>
          <div>
            <span>已花費</span>
            <strong>{{ formatMoney(totalSpentWithBudget) }}</strong>
          </div>
          <div>
            <span>剩餘</span>
            <strong :class="{ negative: totalRemaining < 0 }">{{ formatMoney(totalRemaining) }}</strong>
          </div>
          <div>
            <span>已設定分類</span>
            <strong>{{ budgetedItems.length }}</strong>
          </div>
        </div>
        <p v-if="unbudgetedSpentItems.length > 0">
          另有 {{ unbudgetedSpentItems.length }} 個分類尚未設定預算，已花費 {{ formatMoney(totalUnbudgetedSpent) }}。
        </p>
        <p v-else-if="budgetedItems.length === 0">
          先設定 1 到 3 個常用分類，就能開始追蹤本月支出上限。
        </p>
      </section>

      <section class="budget-alerts">
        <article v-if="overspentItems.length > 0" class="alert-card danger">
          <div>
            <span>超支提醒</span>
            <strong>{{ formatMoney(totalOverspent) }}</strong>
          </div>
          <p>{{ overspentItems.length }} 個分類已超出預算。</p>
          <div class="alert-list">
            <span v-for="item in topOverspentItems" :key="`overspend-${item.category}`">
              {{ item.category }} · 已超出 {{ formatMoney(Math.abs(item.remaining)) }}
            </span>
          </div>
        </article>

        <article v-if="nearLimitItems.length > 0" class="alert-card warning">
          <div>
            <span>快用完</span>
            <strong>{{ nearLimitItems.length }} 類</strong>
          </div>
          <p>以下分類已使用超過 90%，可優先留意。</p>
          <div class="alert-list">
            <span v-for="item in topNearLimitItems" :key="`near-limit-${item.category}`">
              {{ item.category }} · {{ usageRate(item) }}%
            </span>
          </div>
        </article>

        <article v-if="unbudgetedSpentItems.length > 0" class="alert-card neutral">
          <div>
            <span>可設定上限</span>
            <strong>{{ formatMoney(totalUnbudgetedSpent) }}</strong>
          </div>
          <p>這些分類已有支出，但尚未設定預算。</p>
          <div class="alert-list">
            <span v-for="item in topUnbudgetedSpentItems" :key="`unbudgeted-${item.category}`">
              {{ item.category }} · {{ formatMoney(item.spent) }}
            </span>
          </div>
        </article>

        <article
          v-if="overspentItems.length === 0 && nearLimitItems.length === 0 && unbudgetedSpentItems.length === 0"
          class="alert-card clear"
        >
          <div>
            <span>目前狀態</span>
            <strong>控制良好</strong>
          </div>
          <p>{{ selectedMonth }} 的預算目前都在範圍內。</p>
        </article>
      </section>

      <article v-for="item in budgetSummary" :key="item.category" class="budget-card">
        <div class="card-top">
          <div>
            <h3>{{ item.category }}</h3>
            <span :class="statusClass(item)">
              {{ statusLabel(item) }}
            </span>
          </div>
          <strong>{{ item.budget ? formatMoney(item.remaining) : "可設定上限" }}</strong>
        </div>

        <div class="budget-values">
          <div>
            <span>已花費</span>
            <strong>{{ formatMoney(item.spent) }}</strong>
          </div>
          <div>
            <span>預算</span>
            <strong>{{ hasBudget(item) ? formatMoney(item.budget) : "未設定" }}</strong>
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
            {{ hasBudget(item) ? "編輯" : "設定上限" }}
          </button>
          <button
            v-if="hasBudget(item)"
            class="delete-btn"
            type="button"
            @click="promptDeleteBudget(item.category)"
          >
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
    budgetedItems() {
      return this.budgetSummary.filter((item) => this.hasBudget(item));
    },
    totalBudget() {
      return this.budgetedItems.reduce((sum, item) => sum + Number(item.budget || 0), 0);
    },
    totalSpentWithBudget() {
      return this.budgetedItems.reduce((sum, item) => sum + Number(item.spent || 0), 0);
    },
    totalRemaining() {
      return this.totalBudget - this.totalSpentWithBudget;
    },
    budgetUsageRate() {
      if (this.totalBudget <= 0) return 0;
      return Math.round((this.totalSpentWithBudget / this.totalBudget) * 100);
    },
    summaryProgressWidth() {
      return Math.min(this.budgetUsageRate, 100);
    },
    overspentItems() {
      return this.budgetedItems.filter((item) => Number(item.remaining || 0) < 0);
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
    nearLimitItems() {
      return this.budgetedItems
        .filter((item) => Number(item.remaining || 0) >= 0 && this.usageRate(item) >= 90)
        .sort((a, b) => this.usageRate(b) - this.usageRate(a));
    },
    topNearLimitItems() {
      return this.nearLimitItems.slice(0, 3);
    },
    unbudgetedSpentItems() {
      return this.budgetSummary
        .filter((item) => !this.hasBudget(item) && Number(item.spent || 0) > 0)
        .sort((a, b) => Number(b.spent || 0) - Number(a.spent || 0));
    },
    topUnbudgetedSpentItems() {
      return this.unbudgetedSpentItems.slice(0, 3);
    },
    totalUnbudgetedSpent() {
      return this.unbudgetedSpentItems.reduce((sum, item) => sum + Number(item.spent || 0), 0);
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
      if (!this.hasBudget(item)) {
        return 0;
      }
      const progress = (item.spent / item.budget) * 100;
      return Math.min(progress, 100);
    },
    hasBudget(item) {
      return item.budget !== null && item.budget !== undefined && Number(item.budget) > 0;
    },
    usageRate(item) {
      if (!this.hasBudget(item)) return 0;
      return Math.round((Number(item.spent || 0) / Number(item.budget || 1)) * 100);
    },
    statusLabel(item) {
      if (!this.hasBudget(item)) return "未設定預算";
      if (Number(item.remaining || 0) < 0) return "超支";
      if (this.usageRate(item) >= 90) return "快用完";
      return "控制良好";
    },
    statusClass(item) {
      return {
        overspend: this.hasBudget(item) && Number(item.remaining || 0) < 0,
        warning: this.hasBudget(item) && Number(item.remaining || 0) >= 0 && this.usageRate(item) >= 90,
        unset: !this.hasBudget(item),
      };
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
          `<input id="swal-input1" class="swal2-input" type="number" min="1" value="${item.budget || ''}">` +
          `<label for="swal-input2">備註:</label>` +
          `<input id="swal-input2" class="swal2-input" value="${item.notes || ''}">`,
        focusConfirm: false,
        showCancelButton: true,
        confirmButtonText: "儲存",
        cancelButtonText: "取消",
        preConfirm: () => {
          const amount = parseFloat(this.$swal.getPopup().querySelector('#swal-input1').value);
          const notes = this.$swal.getPopup().querySelector('#swal-input2').value;

          if (isNaN(amount) || amount <= 0) {
            this.$swal.showValidationMessage(`請輸入大於 0 的預算金額`);
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

.monthly-budget-card {
  display: grid;
  gap: 12px;
  padding: 16px;
  color: #134e4a;
  background: #ecfdf5;
  border: 1px solid #99f6e4;
  border-radius: 10px;
}

.monthly-budget-card > div:first-child,
.alert-card > div:first-child {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.monthly-budget-card span,
.monthly-budget-card strong,
.alert-card span,
.alert-card strong {
  font-weight: 900;
}

.monthly-budget-card > div:first-child span,
.alert-card > div:first-child span {
  font-size: 0.86rem;
}

.monthly-budget-card > div:first-child strong {
  font-size: 1.55rem;
}

.summary-progress {
  width: 100%;
  height: 12px;
  overflow: hidden;
  background: rgba(15, 118, 110, 0.14);
  border-radius: 999px;
}

.summary-progress-fill {
  height: 100%;
  background: #0f766e;
  transition: width 0.3s ease-in-out;
}

.summary-progress-fill.overbudget {
  background: #dc2626;
}

.budget-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.budget-metrics div {
  display: grid;
  gap: 3px;
  min-height: 58px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(20, 184, 166, 0.24);
  border-radius: 8px;
}

.budget-metrics span {
  color: #0f766e;
  font-size: 0.8rem;
}

.budget-metrics strong {
  color: #134e4a;
  font-size: 1rem;
}

.budget-metrics .negative {
  color: #dc2626;
}

.monthly-budget-card p {
  margin: 0;
  color: #0f766e;
  font-size: 0.86rem;
  line-height: 1.45;
}

.budget-alerts {
  display: grid;
  gap: 8px;
}

.alert-card {
  display: grid;
  gap: 8px;
  padding: 14px;
  border-radius: 10px;
}

.alert-card.danger {
  color: #991b1b;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-left: 4px solid #dc2626;
}

.alert-card.warning {
  color: #92400e;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-left: 4px solid #f59e0b;
}

.alert-card.neutral {
  color: #1e3a8a;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-left: 4px solid #2563eb;
}

.alert-card.clear {
  color: #166534;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-left: 4px solid #16a34a;
}

.alert-card p {
  margin: 0;
  color: inherit;
  font-size: 0.86rem;
  line-height: 1.45;
}

.alert-list {
  display: grid;
  gap: 6px;
}

.alert-list span {
  display: flex;
  align-items: center;
  min-height: 32px;
  padding: 7px 9px;
  color: inherit;
  background: rgba(255, 255, 255, 0.64);
  border: 1px solid rgba(255, 255, 255, 0.56);
  border-radius: 8px;
  min-width: 0;
  font-size: 0.84rem;
  overflow: hidden;
  text-overflow: ellipsis;
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

.card-top .warning {
  color: #d97706;
}

.card-top .unset {
  color: #2563eb;
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
