import { createRouter, createWebHistory } from "vue-router";
import { jwtDecode } from 'jwt-decode';
import apiClient from "@/api";

const HomeView = () => import("../views/HomeView.vue");
const LoginView = () => import("../views/LoginView.vue");
const AssetsOverview = () => import("../views/AssetsOverview.vue");
const TransactionRecord = () => import("../views/TransactionRecord.vue");
const BudgetPlanner = () => import("@/views/BudgetPlanner.vue");
const Goals = () => import("../views/FinancialGoals.vue");
const TripsView = () => import("../views/TripsView.vue");
const TripInviteAccept = () => import("../views/TripInviteAccept.vue");
const AuthCallback = () => import("../views/AuthCallback.vue");
const AccountSettings = () => import("../views/AccountSettings.vue");
const AllocationOverview = () => import("../views/AllocationOverview.vue");
const AllocationDetail = () => import("../views/AllocationDetail.vue");

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
    path: "/allocation",
    name: "AllocationOverview",
    component: AllocationOverview,
    meta: { requiresAuth: true },
  },
  {
    path: "/allocation/:portfolioId",
    name: "AllocationDetail",
    component: AllocationDetail,
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
    path: "/trips/:tripId",
    name: "TripDetail",
    component: TripsView,
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
    path: "/account",
    name: "AccountSettings",
    component: AccountSettings,
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
    const hasSession = Boolean(decoded.session_id);
    const isFresh = decoded.exp * 1000 > Date.now();
    if (!hasSession || !isFresh) {
      localStorage.removeItem('authToken');
      return false;
    }
    return true;
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
