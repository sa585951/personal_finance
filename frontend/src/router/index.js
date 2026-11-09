import { createRouter, createWebHistory } from "vue-router";
import apiClient from "@/api";

const HomeView = () => import("../views/HomeView.vue");
const LoginView = () => import("../views/LoginView.vue");
const AssetsOverview = () => import("../views/AssetsOverview.vue");
const TransactionRecord = () => import("../views/TransactionRecord.vue");
const BudgetPlanner = () => import("@/views/BudgetPlanner.vue");
const TripListView = () => import("../views/TripListView.vue");
const TripsView = () => import("../views/TripsView.vue");
const TripInviteAccept = () => import("../views/TripInviteAccept.vue");
const AuthCallback = () => import("../views/AuthCallback.vue");
const AccountSettings = () => import("../views/AccountSettings.vue");
const AllocationOverview = () => import("../views/AllocationOverview.vue");
const AllocationDetail = () => import("../views/AllocationDetail.vue");
const UniversalAddView = () => import("../views/UniversalAddView.vue");
const AnalysisView = () => import("../views/AnalysisView.vue");
const MeView = () => import("../views/MeView.vue");

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
    meta: { requiresAuth: true, tab: "today" },
  },
  {
    path: "/assets",
    name: "AssetsOverview",
    component: AssetsOverview,
    meta: { requiresAuth: true, tab: "me" },
  },
  {
    path: "/allocation",
    name: "AllocationOverview",
    component: AllocationOverview,
    meta: { requiresAuth: true, tab: "me" },
  },
  {
    path: "/allocation/:portfolioId",
    name: "AllocationDetail",
    component: AllocationDetail,
    meta: { requiresAuth: true, tab: "me" },
  },
  {
    path: "/transactions",
    name: "TransactionRecord",
    component: TransactionRecord,
    meta: { requiresAuth: true, tab: "ledger" },
  },
  {
    path: "/add",
    name: "UniversalAdd",
    component: UniversalAddView,
    meta: { requiresAuth: true },
  },
  {
    path: "/analysis",
    name: "Analysis",
    component: AnalysisView,
    meta: { requiresAuth: true, tab: "me" },
  },
  {
    path: "/trips",
    name: "Trips",
    component: TripListView,
    meta: { requiresAuth: true, tab: "trips" },
  },
  {
    path: "/trips/invite/:token",
    name: "TripInviteAccept",
    component: TripInviteAccept,
    meta: { requiresAuth: true, tab: "trips" },
  },
  {
    path: "/trips/:tripId",
    name: "TripDetail",
    component: TripsView,
    meta: { requiresAuth: true, tab: "trips" },
  },
  {
    path: "/budgets",
    name: "BudgetPlanner",
    component: BudgetPlanner,
    meta: { requiresAuth: true, tab: "me" },
  },
  {
    path: "/goals",
    redirect: "/analysis",
  },
  {
    path: "/me",
    name: "Me",
    component: MeView,
    meta: { requiresAuth: true, tab: "me" },
  },
  {
    path: "/account",
    name: "AccountSettings",
    component: AccountSettings,
    meta: { requiresAuth: true, tab: "me" },
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
  if (import.meta.env.DEV && import.meta.env.VITE_DEV_AUTH_BYPASS === "true") {
    if (to.name === "Login") {
      next({ name: "Home" });
      return;
    }
    next();
    return;
  }

  if (!requiresAuth && to.name !== 'Login') {
    next();
    return;
  }
  const isAuthenticated = await hasValidCookieSession();

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
