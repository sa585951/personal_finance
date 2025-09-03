<template>
  <div class="page-container">
    <h1>財務目標規劃</h1>

    <div class="form-container">
      <h3>新增目標</h3>
      <form @submit.prevent="addGoal">
        <div>
          <label for="title">目標名稱:</label>
          <input
            type="text"
            id="title"
            v-model="newGoal.title"
            placeholder="例如：買房頭期款"
            required
          />
        </div>

        <div>
          <label for="goalType">目標類型:</label>
          <input
            type="text"
            id="goalType"
            v-model="newGoal.goal_type"
            placeholder="例如：投資、儲蓄"
            required
          />
        </div>

        <div>
          <label for="targetAmount">目標金額:</label>
          <input
            type="number"
            id="targetAmount"
            v-model.number="newGoal.target_amount"
            required
          />
        </div>

        <div>
          <label for="targetDate">預計達成日期:</label>
          <input
            type="date"
            id="targetDate"
            v-model="newGoal.target_date"
            required
          />
        </div>

        <div>
          <label for="description">描述 (可選):</label>
          <input
            type="text"
            id="description"
            v-model="newGoal.description"
            placeholder="詳細說明"
          />
        </div>

        <button type="submit" class="base-btn btn-primary">新增目標</button>
      </form>
    </div>

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
              <td>
                <input type="number" v-model.number="goal.target_amount" />
              </td>
              <td>
                <input type="number" v-model.number="goal.current_amount" />
              </td>
              <td>
                <div class="progress-bar-container">
                  <div
                    class="progress-bar"
                    :style="{
                      width:
                        (goal.current_amount / goal.target_amount) * 100 + '%',
                    }"
                    :class="{ completed: goal.status === 'completed' }"
                  ></div>
                </div>
                <span
                  >{{
                    ((goal.current_amount / goal.target_amount) * 100).toFixed(
                      1
                    )
                  }}%</span
                >
              </td>
              <td>
                <span :class="{ completed: goal.status === 'completed' }">
                  {{ goal.status === "completed" ? "已達成" : "進行中" }}
                </span>
              </td>
              <td class="action-buttons">
                <button class="base-btn btn-primary" @click="saveGoal(goalId)">
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
                    :style="{
                      width:
                        (goal.current_amount / goal.target_amount) * 100 + '%',
                    }"
                    :class="{ completed: goal.status === 'completed' }"
                  ></div>
                </div>
                <span
                  >{{
                    ((goal.current_amount / goal.target_amount) * 100).toFixed(
                      1
                    )
                  }}%</span
                >
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
                  @click="updateGoalProgress(goalId, goal.new_current_amount)"
                >
                  更新
                </button>
                <button class="base-btn btn-primary" @click="editGoal(goalId)">
                  編輯
                </button>
                <button class="base-btn btn-danger" @click="deleteGoal(goalId)">
                  刪除
                </button>
              </td>
            </template>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "FinancialGoals",
  data() {
    return {
      goals: {},
      newGoal: {
        title: "",
        goal_type: "",
        target_amount: null,
        target_date: null,
        description: "",
      },
      editingGoalId: null,
    };
  },
  methods: {
    async fetchGoals() {
      try {
        const response = await axios.get("/api/goals");
        this.goals = response.data.data;
      } catch (error) {
        console.error("無法載入目標資料", error);
      }
    },
    async addGoal() {
      if (
        !this.newGoal.title ||
        !this.newGoal.target_amount ||
        !this.newGoal.target_date
      ) {
        alert("請填寫所有必填欄位！");
        return;
      }
      try {
        const response = await axios.post("/api/goals", this.newGoal);
        alert(response.data.message);
        this.resetForm();
        this.fetchGoals();
      } catch (error) {
        alert("新增目標失敗。");
        console.error("新增目標失敗:", error);
      }
    },
    async updateGoalProgress(goalId, newCurrentAmount) {
      if (
        newCurrentAmount === undefined ||
        newCurrentAmount === null ||
        newCurrentAmount < 0
      ) {
        alert("請輸入有效的更新金額（大於或等於 0）！");
        return;
      }
      try {
        const response = await axios.put(`/api/goals/${goalId}`, {
          new_current_amount: newCurrentAmount,
        });
        alert(response.data.message);
        this.fetchGoals();
      } catch (error) {
        alert("更新進度失敗。");
        console.error("更新進度失敗:", error);
      }
    },
    async deleteGoal(goalId) {
      if (confirm("確定要刪除這個目標嗎？")) {
        try {
          const response = await axios.delete(`/api/goals/${goalId}`);
          alert(response.data.message);
          this.fetchGoals();
        } catch (error) {
          alert("刪除目標失敗。");
          console.error("刪除目標失敗:", error);
        }
      }
    },
    editGoal(goalId) {
      this.editingGoalId = goalId;
    },
    async saveGoal(goalId) {
      try {
        const goalToUpdate = this.goals[goalId];
        // 確保目標金額不為負數
        if (goalToUpdate.target_amount < 0 || goalToUpdate.current_amount < 0) {
          alert("目標金額和目前金額不能為負數！");
          return;
        }

        const response = await axios.put(`/api/goals/${goalId}`, {
          title: goalToUpdate.title,
          goal_type: goalToUpdate.type,
          target_amount: goalToUpdate.target_amount,
          current_amount: goalToUpdate.current_amount,
        });

        alert(response.data.message);
        this.editingGoalId = null;
        this.fetchGoals();
      } catch (error) {
        alert("儲存目標失敗。");
        console.error("儲存目標失敗:", error);
      }
    },
    cancelEdit() {
      this.editingGoalId = null;
      this.fetchGoals();
    },
    resetForm() {
      this.newGoal = {
        title: "",
        goal_type: "",
        target_amount: null,
        target_date: null,
        description: "",
      };
    },
  },
  created() {
    this.fetchGoals();
  },
};
</script>

<style scoped>
.page-container {
  max-width: 900px;
  margin: 40px auto;
  padding: 20px;
  background-color: var(--card-bg);
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

.form-container,
.goals-list-container {
  margin-top: 2rem;
  padding: 1.5rem;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  background-color: var(--secondary-color);
}

.form-container h3,
.goals-list-container h3 {
  margin-top: 0;
  color: var(--light-text-color);
}

.form-container form {
  display: grid;
  grid-template-columns: repeat(5, 1fr) auto;
  gap: 1.5rem;
  align-items: end;
}

.form-container label {
  font-weight: bold;
  color: var(--light-text-color);
  margin-bottom: 0.5rem;
}

.form-container input {
  padding: 0.8rem 1rem;
  border: 1px solid #ccc;
  border-radius: 6px;
  transition: all 0.3s ease;
  width: 100%;
}

.form-container input:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2);
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
