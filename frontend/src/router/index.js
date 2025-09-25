import { createRouter, createWebHistory } from "vue-router";
import { jwtDecode } from 'jwt-decode';

// View Components
import HomeView from "../views/HomeView.vue";
import LoginView from "../views/LoginView.vue";
import AssetsOverview from "../views/AssetsOverview.vue";
import TransactionRecord from "../views/TransactionRecord.vue";
import BudgetPlanner from "@/views/BudgetPlanner.vue";
import Goals from "../views/FinancialGoals.vue";
import AuthCallback from "../views/AuthCallback.vue";

const routes = [
  {
    path: "/login",
    name: "Login",
    component: LoginView,
  },
  {
    path: "/",
    name: "Home",
    component: HomeView,
    meta: { requiresAuth: true },
  },
  {
    path: "/assets",
    name: "AssetsOverview",
    component: AssetsOverview,
    meta: { requiresAuth: true },
  },
  {
    path: "/transactions",
    name: "TransactionRecord",
    component: TransactionRecord,
    meta: { requiresAuth: true },
  },
  {
    path: "/budgets",
    name: "BudgetPlanner",
    component: BudgetPlanner,
    meta: { requiresAuth: true },
  },
  {
    path: "/goals",
    name: "Goals",
    component: Goals,
    meta: { requiresAuth: true },
  },
  {
    path: '/auth-callback',
    name: 'AuthCallback',
    component: AuthCallback,
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// Navigation Guard
router.beforeEach((to, from, next) => {
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth);
  const token = localStorage.getItem('authToken');
  let isAuthenticated = false;

  if (token) {
    try {
      const decoded = jwtDecode(token);
      if (decoded.exp * 1000 > Date.now()) {
        isAuthenticated = true;
      }
    } catch (e) {
      isAuthenticated = false;
    }
  }

  if (requiresAuth && !isAuthenticated) {
    // If route requires auth and user is not authenticated, redirect to login
    next({ name: 'Login' });
  } else if (to.name === 'Login' && isAuthenticated) {
    // If user is authenticated and tries to go to login page, redirect to home
    next({ name: 'Home' });
  } else {
    // Otherwise, proceed
    next();
  }
});

export default router;
