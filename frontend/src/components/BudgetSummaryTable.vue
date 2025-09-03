<template>
  <div>
    <select :value="selectedMonth" @change="handleMonthChange">
      <option disabled value="">請選擇月份</option>
      <option v-for="month in availableMonths" :key="month" :value="month">
        {{ month }}
      </option>
    </select>

    <table v-if="budgetSummary.length > 0">
      <thead>
        <tr>
          <th>類別</th>
          <th>已花費</th>
          <th>預算</th>
          <th>剩餘</th>
          <th>進度</th>
          <th>狀態</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in budgetSummary" :key="item.category">
          <td>{{ item.category }}</td>
          <td>${{ item.spent.toLocaleString() }}</td>
          <td>${{ item.budget ? item.budget.toLocaleString() : "未設定" }}</td>
          <td>
            ${{ item.remaining ? item.remaining.toLocaleString() : "N/A" }}
          </td>
          <td>
            <div class="progress-bar-container">
              <div
                class="progress-bar"
                :style="{ width: calculateProgress(item) + '%' }"
                :class="{ overbudget: item.remaining < 0 }"
              ></div>
            </div>
          </td>
          <td>
            <span :class="{ overspend: item.remaining < 0 }">{{
              item.remaining < 0 ? "超支" : "良好"
            }}</span>
          </td>
          <td>
            <button class="delete-btn" @click="deleteBudget(item.category)">
              刪除
            </button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else class="no-data">該月無預算或支出資料。</p>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "BudgetSummaryTable",
  props: {
    selectedMonth: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      availableMonths: [],
      budgetSummary: [],
    };
  },
  methods: {
    // 處理下拉選單變更事件
    handleMonthChange(event) {
      // 發出事件，將新值傳給父元件
      this.$emit("update-month", event.target.value);
    },
    async fetchBudgetSummary() {
      if (!this.selectedMonth) return;
      try {
        const response = await axios.get(
          `/api/budgets/summary/${this.selectedMonth}`
        );
        this.budgetSummary = response.data.data;
      } catch (error) {
        console.error("無法載入預算總覽", error);
        this.budgetSummary = []; // 清空資料
      }
    },
    // 獲取所有有紀錄的月份
    async fetchAvailableMonths() {
      try {
        const response = await axios.get("/api/months");
        this.availableMonths = response.data.data;
      } catch (error) {
        console.error("無法載入可用月份", error);
      }
    },
    calculateProgress(item) {
      if (!item.budget || item.budget === 0) {
        return 0;
      }
      let progress = (item.spent / item.budget) * 100;
      return Math.min(progress, 100); // 確保進度條不超過 100%
    },
    async deleteBudget(category) {
      const confirmDelete = window.confirm(
        `確定要刪除「${this.selectedMonth}」月份的「${category}」預算嗎？`
      );
      if (confirmDelete) {
        try {
          const response = await axios.delete(
            `/api/budgets/${this.selectedMonth}/${category}`
          );
          alert(response.data.message);
          this.fetchBudgetSummary(); // 刪除成功後重新載入列表
        } catch (error) {
          console.error("刪除預算失敗:", error);
          alert("刪除失敗，請稍後再試。");
        }
      }
    },
  },
  // 使用 watch 監聽 selectedMonth 的變化
  watch: {
    selectedMonth(newMonth, oldMonth) {
      // 確保只有當月份真的改變時才重新載入
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
table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0 10px;
}

thead th {
  background-color: var(--primary-color);
  color: var(--card-bg);
  padding: 12px;
  text-align: center;
  font-size: 1rem;
  white-space: nowrap;
}

thead th:first-child {
  border-top-left-radius: 8px;
}

thead th:last-child {
  border-top-right-radius: 8px;
}

tbody td {
  padding: 12px;
  text-align: center;
  vertical-align: middle;
}

tbody tr {
  background-color: var(--card-bg);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  box-shadow: 0 1px 5px rgba(0, 0, 0, 0.05);
}

tbody tr:hover {
  transform: translateY(-3px);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

select {
  padding: 0.8rem 1rem;
  border: 1px solid #ccc;
  border-radius: 6px;
  margin-bottom: 1rem;
  background-color: #fff;
  transition: all 0.3s ease;
}

select:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2);
}

.progress-bar-container {
  width: 100px;
  height: 10px;
  background-color: #e0e0e0;
  border-radius: 5px;
  overflow: hidden;
  margin: 0 auto;
}

.progress-bar {
  height: 100%;
  background-color: var(--primary-color);
  transition: width 0.3s ease-in-out;
}

.progress-bar.overbudget {
  background-color: var(--danger-color);
}

.delete-btn {
  background-color: var(--danger-color);
  color: white;
  border: none;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.delete-btn:hover {
  background-color: #d32f2f;
}

.overspend {
  color: var(--danger-color);
  font-weight: bold;
}

.no-data {
  text-align: center;
  padding: 2rem;
  color: #666;
  background-color: var(--card-bg);
  margin-top: 1rem;
  border-radius: 8px;
}
</style>
