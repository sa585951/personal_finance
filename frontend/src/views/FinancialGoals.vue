<template>
  <div class="page-container">
    <h1>財務目標規劃</h1>

    <GoalForm @goal-added="fetchGoals" />

    <GoalList
      :goals="goals"
      @update-progress="updateGoalProgress"
      @delete-goal="deleteGoal"
      @save-goal="saveGoal"
      @edit-canceled="fetchGoals"
    />
  </div>
</template>

<script>
import axios from "axios";
import GoalForm from "../components/GoalForm.vue";
import GoalList from "../components/GoalList.vue";

export default {
  name: "FinancialGoals",
  components: {
    GoalForm,
    GoalList,
  },
  data() {
    return {
      goals: {},
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
    async saveGoal(goalId, updatedGoal) {
      try {
        if (updatedGoal.target_amount < 0 || updatedGoal.current_amount < 0) {
          alert("目標金額和目前金額不能為負數！");
          return;
        }

        const response = await axios.put(`/api/goals/${goalId}`, {
          title: updatedGoal.title,
          goal_type: updatedGoal.type,
          target_amount: updatedGoal.target_amount,
          current_amount: updatedGoal.current_amount,
        });

        alert(response.data.message);
        this.fetchGoals();
      } catch (error) {
        alert("儲存目標失敗。");
        console.error("儲存目標失敗:", error);
      }
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
</style>
