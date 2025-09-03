import { createRouter, createWebHistory } from "vue-router"; // 從 vue-router 庫中導入 createRouter 和 createWebHistory
import AssetsOverview from "../views/AssetsOverview.vue";
import TransactionRecord from "../views/TransactionRecord.vue";
import BudgetPlanner from "@/views/BudgetPlanner.vue";
import Goals from "../views/FinancialGoals.vue";

const routes = [
  {
    path: "/",
    name: "AssetsOverview",
    component: AssetsOverview,
  },
  {
    path: "/transactions",
    name: "TransactionRecord",
    component: TransactionRecord,
  },
  {
    path: "/budgets",
    name: "BudgetPlanner",
    component: BudgetPlanner,
  },
  {
    path: "/goals",
    name: "Goals",
    component: Goals,
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
