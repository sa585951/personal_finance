<template>
  <div class="page-container">
    <h1>財務目標規劃</h1>

    <GoalSummaryCard />

    <GoalForm @goal-added="fetchGoals" />

    <GoalList
      :goals="goals"
      @update-goal="updateGoal"
      @delete-goal="deleteGoal"
      @update-progress="updateGoalProgress"
    />
  </div>
</template>

<script>
import axios from "axios";
const API_URL = import.meta.env.VITE_APP_API_URL;
import GoalForm from "../components/goals/GoalForm.vue";
import GoalList from "../components/goals/GoalList.vue";
import GoalSummaryCard from "../components/reports/GoalSummaryCard.vue";

export default {
  name: "FinancialGoals",
  components: {
    GoalForm,
    GoalList,
    GoalSummaryCard,
  },
  data() {
    return {
      goals: {},
    };
  },
  methods: {
    async fetchGoals() {
      try {
        const response = await axios.get(`${API_URL}/api/goals`);
        this.goals = response.data.data;
      } catch (error) {
        this.$swal.fire({
          icon: "error",
          title: "錯誤",
          text: "無法載入目標資料，請稍後再試。",
        });
      }
    },
    async updateGoal(goalId, updatedData) {
      try {
        const response = await axios.put(`${API_URL}/api/goals/${goalId}`, updatedData);
        this.$swal.fire({
          icon: "success",
          title: "成功",
          text: response.data.message,
        });
        this.fetchGoals();
      } catch (error) {
        this.$swal.fire({
          icon: "error",
          title: "更新失敗",
          text: "無法更新目標，請稍後再試。",
        });
      }
    },
    async deleteGoal(goalId) {
      try {
        const response = await axios.delete(`${API_URL}/api/goals/${goalId}`);
        this.$swal.fire({
          icon: "success",
          title: "成功",
          text: response.data.message,
        });
        this.fetchGoals();
      } catch (error) {
        this.$swal.fire({
          icon: "error",
          title: "刪除失敗",
          text: "無法刪除目標，請稍後再試。",
        });
      }
    },
    async updateGoalProgress(goalId, newCurrentAmount) {
      try {
        const response = await axios.put(`${API_URL}/api/goals/${goalId}`, {
          current_amount: newCurrentAmount,
        });
        this.$swal.fire({
          icon: "success",
          title: "成功",
          text: response.data.message,
        });
        this.fetchGoals();
      } catch (error) {
        this.$swal.fire({
          icon: "error",
          title: "更新失敗",
          text: "無法更新進度，請稍後再試。",
        });
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
