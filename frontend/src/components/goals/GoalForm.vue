<template>
  <div class="card">
    <div class="card-header">
      <h3 class="card-title">新增目標</h3>
    </div>
    <div class="card-body">
      <form @submit.prevent="addGoal">
        <div class="form-group">
          <label for="title">目標名稱:</label>
          <input
            type="text"
            id="title"
            v-model="newGoal.title"
            placeholder="例如：買房頭期款"
            required
          />
        </div>

        <div class="form-group">
          <label for="goalType">目標類型:</label>
          <input
            type="text"
            id="goalType"
            v-model="newGoal.goal_type"
            placeholder="例如：投資、儲蓄"
            required
          />
        </div>

        <div class="form-group">
          <label for="targetAmount">目標金額:</label>
          <input
            type="number"
            id="targetAmount"
            v-model.number="newGoal.target_amount"
            required
          />
        </div>

        <div class="form-group">
          <label for="targetDate">預計達成日期:</label>
          <input
            type="date"
            id="targetDate"
            v-model="newGoal.target_date"
            required
          />
        </div>

        <div class="form-group">
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
  </div>
</template>

<script>
import axios from "axios";
const API_URL = import.meta.env.VITE_APP_API_URL;

export default {
  name: "GoalForm",
  emits: ["goal-added"], // 宣告一個事件，用於通知父元件
  data() {
    return {
      newGoal: {
        title: "",
        goal_type: "",
        target_amount: null,
        target_date: null,
        description: "",
      },
    };
  },
  methods: {
    async addGoal() {
      if (
        !this.newGoal.title ||
        !this.newGoal.target_amount ||
        !this.newGoal.target_date
      ) {
        this.$swal.fire({
          icon: "warning",
          title: "警告",
          text: "請填寫所有必填欄位！",
        });
        return;
      }
      try {
        const response = await axios.post(`${API_URL}/api/goals`, this.newGoal);
        this.$swal.fire({
          icon: "success",
          title: "成功",
          text: response.data.message,
        });
        this.resetForm();
        this.$emit("goal-added"); // 新增成功後發出事件
      } catch (error) {
        this.$swal.fire({
          icon: "error",
          title: "新增失敗",
          text: "新增目標失敗，請稍後再試。",
        });
        console.error("新增目標失敗:", error);
      }
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

form {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  align-items: flex-end;
}

.form-group {
  display: flex;
  flex-direction: column;
}

label {
  font-weight: bold;
  color: var(--light-text-color);
  margin-bottom: 0.5rem;
}

input[type="text"],
input[type="number"],
input[type="date"] {
  padding: 0.8rem 1rem;
  border: 1px solid #ccc;
  border-radius: 6px;
  transition: all 0.3s ease;
  width: 100%;
  box-sizing: border-box; /* Ensure padding doesn't increase width */
}

input:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2);
}

button[type="submit"] {
  grid-column: span 2; /* Make button span across two columns */
  padding: 0.8rem 1.5rem;
  font-size: 1rem;
  cursor: pointer;
  border-radius: 6px;
  transition: background-color 0.3s ease;
  margin-top: 1rem; /* Add some space above the button */
}

.btn-primary {
  background-color: var(--primary-color);
  color: white;
  border: none;
}

.btn-primary:hover {
  background-color: var(--primary-dark-color);
}
</style>
