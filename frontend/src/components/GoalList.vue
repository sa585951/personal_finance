<template>
  <div class="goals-list-container">
    <h3>我的目標</h3>
    <div v-if="Object.keys(goals).length === 0" class="no-data-message">
      目前沒有設定任何財務目標。
    </div>
    <table v-else>
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
          <template v-if="editingGoalId === goalId">
            <td><input v-model="goal.title" /></td>
            <td><input v-model="goal.type" /></td>
            <td><input type="number" v-model.number="goal.target_amount" /></td>
            <td>
              <input type="number" v-model.number="goal.current_amount" />
            </td>
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
            <td class="action-buttons">
              <button
                class="base-btn btn-primary"
                @click="$emit('save-goal', goalId, goal)"
              >
                儲存
              </button>
              <button class="base-btn btn-danger" @click="cancelEdit()">
                取消
              </button>
            </td>
          </template>

          <template v-else>
            <td>{{ goal.title }}</td>
            <td>{{ goal.type }}</td>
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
            <td class="action-buttons">
              <input
                type="number"
                v-model.number="goal.new_current_amount"
                :placeholder="`更新金額`"
                class="update-input"
              />
              <button
                class="base-btn btn-update"
                @click="
                  $emit('update-progress', goalId, goal.new_current_amount)
                "
              >
                更新
              </button>
              <button class="base-btn btn-primary" @click="editGoal(goalId)">
                編輯
              </button>
              <button
                class="base-btn btn-danger"
                @click="$emit('delete-goal', goalId)"
              >
                刪除
              </button>
            </td>
          </template>
        </tr>
      </tbody>
    </table>
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
  emits: ["update-progress", "delete-goal", "save-goal", "edit-canceled"],
  data() {
    return {
      editingGoalId: null,
    };
  },
  methods: {
    calculateProgress(goal) {
      if (!goal.target_amount || goal.target_amount === 0) {
        return 0;
      }
      let progress = (goal.current_amount / goal.target_amount) * 100;
      return Math.min(progress, 100);
    },
    editGoal(goalId) {
      this.editingGoalId = goalId;
    },
    cancelEdit() {
      this.editingGoalId = null;
      this.$emit("edit-canceled"); // 通知父元件還原資料
    },
  },
};
</script>

<style scoped>
.goals-list-container {
  margin-top: 2rem;
  padding: 1.5rem;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  background-color: var(--secondary-color);
}

.goals-list-container h3 {
  margin-top: 0;
  color: var(--light-text-color);
}

.no-data-message {
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

.action-buttons {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 5px;
}

.update-input {
  width: 60px;
  text-align: center;
}
</style>
