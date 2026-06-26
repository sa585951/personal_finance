<template>
  <nav class="navbar" aria-label="主要導覽">
    <div class="logo">
      <router-link to="/">Nomica</router-link>
    </div>
    <ul class="nav-links">
      <li v-for="item in navItems" :key="item.to">
        <router-link :to="item.to" :aria-label="item.label">
          <component :is="item.icon" />
          <span>{{ item.label }}</span>
        </router-link>
      </li>
    </ul>
    <div class="auth-section">
      <template v-if="devAuthBypass">
        <label class="dev-user-switcher">
          <span>測試使用者</span>
          <select v-model="selectedDevUser" @change="switchDevUser">
            <option v-for="user in devUsers" :key="user.id" :value="user.id">
              {{ user.name }}
            </option>
          </select>
        </label>
      </template>
      <template v-if="isLoggedIn">
        <button class="account-button" type="button" @click="showAccountMenu = !showAccountMenu">
          {{ userName || "帳號" }}
        </button>
        <div v-if="showAccountMenu" class="account-menu">
          <span>{{ userName || "已登入" }}</span>
          <router-link class="account-menu-link" to="/account" @click="showAccountMenu = false">
            帳號設定
          </router-link>
          <button class="logout-button" type="button" @click="logout">登出</button>
        </div>
      </template>
    </div>
  </nav>
</template>

<script>
import apiClient from "@/api";
import { jwtDecode } from 'jwt-decode';
import { HomeFilled, Money, PieChart, Suitcase, Wallet } from '@element-plus/icons-vue';

export default {
  name: 'Navbar',
  components: {
    HomeFilled,
    Money,
    PieChart,
    Suitcase,
    Wallet,
  },
  data() {
    return {
      isLoggedIn: false,
      userName: '',
      showAccountMenu: false,
      devAuthBypass: import.meta.env.VITE_DEV_AUTH_BYPASS === "true",
      selectedDevUser: localStorage.getItem('devAuthUser') || 'local-dev-user',
      devUsers: [
        { id: 'local-dev-user', name: 'Dev User' },
        { id: 'amy-dev-user', name: 'Amy' },
        { id: 'ben-dev-user', name: 'Ben' },
        { id: 'cara-dev-user', name: 'Cara' },
      ],
      navItems: [
        { to: "/", label: "首頁", icon: "HomeFilled" },
        { to: "/transactions", label: "收支", icon: "Money" },
        { to: "/trips", label: "旅行", icon: "Suitcase" },
        { to: "/budgets", label: "預算", icon: "PieChart" },
        { to: "/assets", label: "帳戶", icon: "Wallet" },
      ],
    };
  },
  mounted() {
    this.checkLoginStatus();
  },
  methods: {
    async checkLoginStatus() {
      if (this.devAuthBypass) {
        this.isLoggedIn = false;
        this.userName = "Dev";
        return;
      }

      const token = localStorage.getItem('authToken');
      if (token) {
        try {
          const decoded = jwtDecode(token);
          // Phase 7.1 後 token 必須綁定後端 session，舊 token 需重新登入。
          if (decoded.session_id && decoded.exp * 1000 > Date.now()) {
            this.isLoggedIn = true;
            this.userName = decoded.name; // 從 JWT payload 中讀取 name
            return;
          } else {
            localStorage.removeItem('authToken');
          }
        } catch (error) {
          console.error("JWT 解碼失敗:", error);
          localStorage.removeItem('authToken');
        }
      }

      try {
        const response = await apiClient.get('/api/auth/me');
        if (response.data?.success) {
          this.isLoggedIn = true;
          this.userName = response.data.data?.name || "帳號";
          return;
        }
      } catch (error) {
        this.isLoggedIn = false;
        this.userName = '';
      }

      this.isLoggedIn = false;
      this.userName = '';
    },
    async logout() {
      try {
        await apiClient.post('/api/auth/logout');
      } catch (error) {
        console.warn("後端登出失敗，仍會清除本機登入狀態。", error);
      }
      localStorage.removeItem('authToken');
      this.isLoggedIn = false;
      this.userName = '';
      this.showAccountMenu = false;
      // 登出後一律導向到登入頁
      if (this.$route.path !== '/login') {
        this.$router.push('/login');
      }
    },
    switchDevUser() {
      localStorage.setItem('devAuthUser', this.selectedDevUser);
      window.location.reload();
    },
  },
};
</script>

<style scoped>
.navbar {
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(14px);
  min-height: var(--app-bottom-nav-height);
  padding: 6px 8px calc(6px + env(safe-area-inset-bottom));
  border-top: 1px solid #e2e8f0;
  box-shadow: 0 -8px 24px rgba(15, 23, 42, 0.08);
  display: flex;
  justify-content: center;
  align-items: center;
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 20;
}

.logo,
.auth-section {
  display: none;
}

.dev-user-switcher {
  display: none;
}

.nav-links {
  list-style: none;
  display: flex;
  justify-content: space-between;
  gap: 0;
  width: min(520px, 100%);
  margin: 0;
  padding: 0;
}

.nav-links li {
  flex: 1;
}

.nav-links a {
  color: #64748b;
  text-decoration: none;
  font-weight: 500;
  transition: color 0.3s ease;
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  width: 100%;
  min-height: 58px;
  padding: 0 2px;
  border-radius: 12px;
  font-size: 0.78rem;
}

.nav-links svg {
  width: 20px;
  height: 20px;
}

.nav-links a:hover,
.nav-links a.router-link-active,
.nav-links a.router-link-exact-active {
  color: #0f766e;
  background: #f0fdfa;
  border-bottom: 0;
  transform: none;
}

.nav-links a.router-link-active svg,
.nav-links a.router-link-exact-active svg {
  color: #0f766e;
}

.nav-links a span {
  line-height: 1;
}

@media (min-width: 1px) {
  .auth-section {
    display: block;
    position: fixed;
    top: 8px;
    right: 8px;
    z-index: 30;
  }

  .dev-user-switcher {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 8px;
    color: #334155;
    background: rgba(255, 255, 255, 0.94);
    border: 1px solid #dbe4ee;
    border-radius: 8px;
    box-shadow: 0 8px 20px rgba(15, 23, 42, 0.12);
    font-size: 0.75rem;
    font-weight: 700;
  }

  .dev-user-switcher select {
    min-height: 28px;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    background: #ffffff;
    font-size: 0.78rem;
  }

  .account-button {
    min-height: 34px;
    max-width: 128px;
    padding: 6px 10px;
    color: #334155;
    background: rgba(255, 255, 255, 0.94);
    border: 1px solid #dbe4ee;
    border-radius: 8px;
    box-shadow: 0 8px 20px rgba(15, 23, 42, 0.12);
    font-size: 0.78rem;
    font-weight: 800;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .account-menu {
    position: absolute;
    top: calc(100% + 8px);
    right: 0;
    min-width: 150px;
    padding: 10px;
    display: grid;
    gap: 8px;
    color: #334155;
    background: #ffffff;
    border: 1px solid #dbe4ee;
    border-radius: 10px;
    box-shadow: 0 14px 28px rgba(15, 23, 42, 0.18);
  }

  .account-menu span {
    font-size: 0.78rem;
    font-weight: 800;
  }

  .account-menu-link,
  .logout-button {
    min-height: 34px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    text-decoration: none;
    border-radius: 8px;
    font-weight: 800;
  }

  .account-menu-link {
    color: #0f766e;
    background: #ccfbf1;
    border: 1px solid #99f6e4;
  }

  .logout-button {
    color: #b91c1c;
    background: #fee2e2;
    border: 1px solid #fecaca;
  }
}
</style>
