import { createRouter, createWebHistory } from "vue-router";
import { jwtDecode } from 'jwt-decode';
import apiClient from "@/api";

// View Components
import HomeView from "../views/HomeView.vue";
import LoginView from "../views/LoginView.vue";
import AssetsOverview from "../views/AssetsOverview.vue";
import TransactionRecord from "../views/TransactionRecord.vue";
import BudgetPlanner from "@/views/BudgetPlanner.vue";
import Goals from "../views/FinancialGoals.vue";
import TripsView from "../views/TripsView.vue";
import TripInviteAccept from "../views/TripInviteAccept.vue";
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
    path: "/trips",
    name: "Trips",
    component: TripsView,
    meta: { requiresAuth: true },
  },
  {
    path: "/trips/invite/:token",
    name: "TripInviteAccept",
    component: TripInviteAccept,
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

function hasValidLocalToken() {
  const token = localStorage.getItem('authToken');
  if (!token) return false;
  try {
    const decoded = jwtDecode(token);
    return decoded.exp * 1000 > Date.now();
  } catch (e) {
    localStorage.removeItem('authToken');
    return false;
  }
}

async function hasValidCookieSession() {
  try {
    const response = await apiClient.get("/api/auth/me");
    return response.data?.success === true;
  } catch (error) {
    return false;
  }
}

// Navigation Guard
router.beforeEach(async (to, from, next) => {
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth);
  if (import.meta.env.VITE_DEV_AUTH_BYPASS === "true") {
    if (to.name === "Login") {
      next({ name: "Home" });
      return;
    }
    next();
    return;
  }

  const isAuthenticated = hasValidLocalToken() || await hasValidCookieSession();

  if (requiresAuth && !isAuthenticated) {
    // If route requires auth and user is not authenticated, redirect to login
    next({ name: 'Login', query: { redirect: to.fullPath } });
  } else if (to.name === 'Login' && isAuthenticated) {
    // If user is authenticated and tries to go to login page, redirect to home
    next({ name: 'Home' });
  } else {
    // Otherwise, proceed
    next();
  }
});

export default router;
