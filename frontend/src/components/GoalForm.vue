<template>
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
</template>

<script>
import axios from "axios";

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
        alert("請填寫所有必填欄位！");
        return;
      }
      try {
        const response = await axios.post("/api/goals", this.newGoal);
        alert(response.data.message);
        this.resetForm();
        this.$emit("goal-added"); // 新增成功後發出事件
      } catch (error) {
        alert("新增目標失敗。");
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
.form-container {
  margin-top: 2rem;
  padding: 1.5rem;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  background-color: var(--secondary-color);
}

.form-container h3 {
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
</style>
