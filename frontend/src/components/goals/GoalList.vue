<template>
  <div class="card">
    <div class="card-header">
      <h3 class="card-title">我的目標</h3>
    </div>
    <div class="card-body" v-if="goals && Object.keys(goals).length > 0">
      <table class="goals-table">
        <thead>
          <tr>
            <th>目標名稱</th>
            <th>類型</th>
            <th>目標金額</th>
            <th>已達成金額</th>
            <th>達成率</th>
            <th>狀態</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(goal, goalId) in goals" :key="goalId">
            <td>{{ goal.title }}</td>
            <td>{{ goal.goal_type }}</td>
            <td>${{ goal.target_amount.toLocaleString() }}</td>
            <td>${{ goal.current_amount.toLocaleString() }}</td>
            <td>
              <div class="progress-bar-container">
                <div
                  class="progress-bar"
                  :style="{ width: calculateProgress(goal) + '%' }"
                  :class="{ completed: goal.status === 'completed' }"
                ></div>
              </div>
              <span>{{ calculateProgress(goal).toFixed(1) }}%</span>
            </td>
            <td>
              <span :class="{ completed: goal.status === 'completed' }">
                {{ goal.status === "completed" ? "已達成" : "進行中" }}
              </span>
            </td>
            <td class="table-buttons">
              <button class="update-btn" @click="promptUpdate(goalId, goal)">
                更新
              </button>
              <button class="delete-btn" @click="promptDelete(goalId)">
                刪除
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else class="no-data">
      <p>目前沒有設定任何財務目標。</p>
    </div>
  </div>
</template>

<script>
export default {
  name: "GoalList",
  props: {
    goals: {
      type: Object,
      required: true,
    },
  },
  emits: ["update-goal", "delete-goal", "update-progress"], // Keep update-progress for now, will remove if not needed
  methods: {
    calculateProgress(goal) {
      if (!goal.target_amount || goal.target_amount === 0) {
        return 0;
      }
      let progress = (goal.current_amount / goal.target_amount) * 100;
      return Math.min(progress, 100);
    },
    async promptUpdate(goalId, goal) {
      const { value: formValues } = await this.$swal.fire({
        title: "更新目標",
        html:
          `<label for="swal-input1">目標名稱:</label>` +
          `<input id="swal-input1" class="swal2-input" value="${goal.title}">` +
          `<label for="swal-input2">目標類型:</label>` +
          `<input id="swal-input2" class="swal2-input" value="${goal.goal_type}">` +
          `<label for="swal-input3">目標金額:</label>` +
          `<input id="swal-input3" type="number" class="swal2-input" value="${goal.target_amount}">` +
          `<label for="swal-input4">已達成金額:</label>` +
          `<input id="swal-input4" type="number" class="swal2-input" value="${goal.current_amount}">`,
        focusConfirm: false,
        showCancelButton: true,
        confirmButtonText: "儲存",
        cancelButtonText: "取消",
        preConfirm: () => {
          const title = this.$swal.getPopup().querySelector('#swal-input1').value;
          const goal_type = this.$swal.getPopup().querySelector('#swal-input2').value;
          const target_amount = parseFloat(this.$swal.getPopup().querySelector('#swal-input3').value);
          const current_amount = parseFloat(this.$swal.getPopup().querySelector('#swal-input4').value);

          if (!title || !goal_type || isNaN(target_amount) || isNaN(current_amount)) {
            this.$swal.showValidationMessage(`請填寫所有欄位並確保金額為數字`);
            return false;
          }
          if (target_amount < 0 || current_amount < 0) {
            this.$swal.showValidationMessage(`金額不能為負數`);
            return false;
          }
          return { title: title, goal_type: goal_type, target_amount: target_amount, current_amount: current_amount };
        }
      });

      if (formValues) {
        this.$emit("update-goal", goalId, formValues);
      }
    },
    async promptDelete(goalId) {
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
        this.$emit("delete-goal", goalId);
      }
    },
  },
};
</script>

<style scoped>
.card {
  margin-top: 2rem;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  background-color: var(--secondary-color);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.card-header {
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--border-color);
}

.card-title {
  margin: 0;
  color: var(--light-text-color);
  font-size: 1.5rem;
}

.card-body {
  padding: 1.5rem;
}

.no-data {
  text-align: center;
  color: #888;
  font-style: italic;
  padding: 2rem;
}

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

thead tr th:first-child {
  border-top-left-radius: 8px;
}

thead tr th:last-child {
  border-top-right-radius: 8px;
}

tbody td {
  padding: 12px;
  text-align: center;
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

.progress-bar.completed {
  background-color: var(--primary-color);
}

.table-buttons {
  display: flex;
  justify-content: center;
  gap: 8px;
}

.update-btn {
  background-color: var(--update-color);
}

.delete-btn {
  background-color: var(--danger-color);
}
</style>
