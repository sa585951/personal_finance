<template>
  <nav class="navbar" aria-label="主要導覽">
    <div class="logo">
      <router-link to="/"><img src="/nomica-mark.svg" alt="" class="logo-mark" />Nomica</router-link>
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
      <template v-if="isLoggedIn || devAuthBypass">
        <button class="account-button" type="button" :aria-label="`帳號選單：${userName || '帳號'}`" :aria-expanded="showAccountMenu" @click="showAccountMenu = !showAccountMenu">
          <span class="account-initial" aria-hidden="true">{{ (userName || "帳")[0] }}</span>
          <span class="account-name">{{ userName || "帳號" }}</span>
        </button>
        <div v-if="showAccountMenu" class="account-menu">
          <span>{{ userName || "已登入" }}</span>
          <ThemeToggle show-label />
          <label v-if="devAuthBypass" class="dev-user-switcher">
            <span>測試使用者</span>
            <select v-model="selectedDevUser" aria-label="測試使用者" @change="switchDevUser">
              <option v-for="user in devUsers" :key="user.id" :value="user.id">{{ user.name }}</option>
            </select>
          </label>
          <router-link class="account-menu-link app-button app-button--soft" to="/account" @click="showAccountMenu = false">
            帳號設定
          </router-link>
          <button v-if="isLoggedIn" class="logout-button" type="button" @click="logout">登出</button>
        </div>
      </template>
    </div>
  </nav>
</template>

<script>
import apiClient from "@/api";
import ThemeToggle from "@/components/shared/ThemeToggle.vue";
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
    ThemeToggle,
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
        { to: "/transactions", label: "紀錄", icon: "Money" },
        { to: "/trips", label: "旅行", icon: "Suitcase" },
        { to: "/analysis", label: "分析", icon: "PieChart" },
        { to: "/assets", label: "帳戶", icon: "Wallet" },
      ],
    };
  },
  mounted() {
    this.checkLoginStatus();
    document.addEventListener('pointerdown', this.closeOutside);
    document.addEventListener('keydown', this.closeOnEscape);
  },
  beforeUnmount() {
    document.removeEventListener('pointerdown', this.closeOutside);
    document.removeEventListener('keydown', this.closeOnEscape);
  },
  watch: { '$route.fullPath'() { this.showAccountMenu = false; } },
  methods: {
    closeOutside(event) {
      if (!this.$el.querySelector('.auth-section')?.contains(event.target)) this.showAccountMenu = false;
    },
    closeOnEscape(event) {
      if (event.key === 'Escape' && this.showAccountMenu) {
        this.showAccountMenu = false;
        this.$el.querySelector('.account-button')?.focus();
      }
    },
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
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
  min-height: 64px;
  padding: calc(8px + env(safe-area-inset-top)) 16px 8px;
  border-bottom: 1px solid var(--border-color);
  background: var(--card-bg);
  box-shadow: var(--surface-shadow);
}
.logo { display: block; }
.logo a {
  display: flex;
  align-items: center;
  gap: 9px;
  color: var(--text-color);
  text-decoration: none;
  font-size: 1.1rem;
  font-weight: 850;
  letter-spacing: -.04em;
}
.logo-mark { width: 32px; height: 32px; border-radius: 10px; }
.nav-links {
  position: fixed;
  left: 10px;
  right: 10px;
  bottom: max(8px, env(safe-area-inset-bottom));
  display: flex;
  justify-content: space-between;
  flex: 1 1 auto;
  gap: 2px;
  min-width: 0;
  min-height: 68px;
  margin: 0;
  padding: 6px;
  list-style: none;
  border: 1px solid var(--border-color);
  border-radius: 18px;
  background: var(--card-bg);
  box-shadow: 0 4px 16px rgba(23, 26, 31, .08);
}
.nav-links li { flex: 1; }
.nav-links a {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  width: 100%;
  min-height: 54px;
  padding: 0 2px;
  border-radius: 15px;
  color: var(--light-text-color);
  text-decoration: none;
  font-size: .72rem;
  font-weight: 700;
  transition: background-color var(--motion-fast) ease, color var(--motion-fast) ease, transform var(--motion-fast) ease;
}
.nav-links svg { width: 21px; height: 21px; }
.nav-links a span { line-height: 1; }
.nav-links a:hover,
.nav-links a.router-link-active,
.nav-links a.router-link-exact-active {
  color: var(--primary-color);
  background: var(--primary-soft);
  border-bottom: 0;
  transform: none;
}
.nav-links a.router-link-active svg,
.nav-links a.router-link-exact-active svg { color: var(--primary-color); }
.nav-links a[href="/trips"].router-link-active,
.nav-links a[href="/trips"].router-link-exact-active { color: var(--travel-color); background: var(--travel-soft); }
.nav-links a[href="/trips"].router-link-active svg,
.nav-links a[href="/trips"].router-link-exact-active svg { color: var(--travel-color); }
.auth-section { position: relative; z-index: 1; display: flex; align-items: center; gap: 4px; flex: 0 0 auto; }
.account-button {
  display: grid;
  place-items: center;
  width: 44px;
  min-width: 38px;
  max-width: 78px;
  height: 44px;
  min-height: 44px;
  padding: 0;
  overflow: hidden;
  border: 1px solid var(--brand-border);
  border-radius: 50%;
  color: var(--primary-color);
  background: var(--primary-soft);
  font-size: .78rem;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.account-initial { font-size: .9rem; font-weight: 800; }
.account-name { display: none; }
.account-menu {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  display: grid;
  gap: 10px;
  width: 220px;
  min-width: 150px;
  max-width: calc(100vw - 32px);
  padding: 14px;
  border: 1px solid var(--border-color);
  border-radius: 16px;
  color: var(--text-color);
  background: var(--card-bg);
  box-shadow: 0 14px 28px rgba(15, 23, 42, .18);
}
.account-menu span { font-size: .78rem; font-weight: 800; }
.account-menu :deep(.theme-toggle) {
  width: 100%;
  min-width: 42px;
  min-height: 44px;
  padding: 10px 12px;
  border-radius: 10px;
  justify-content: flex-start;
}
.account-menu-link {
  --app-button-padding: 0;
  --app-button-radius: 8px;
  --app-button-weight: 800;
  --app-button-gap: normal;
  transition: all 0s;
}
.logout-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  border: 1px solid var(--expense-color);
  border-radius: 8px;
  color: var(--expense-color);
  background: var(--expense-soft);
  text-decoration: none;
  font-weight: 800;
}
.dev-user-switcher {
  display: flex;
  align-items: center;
  min-height: 44px;
  padding: 4px;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  color: var(--text-color);
  background: var(--secondary-color);
  font-size: .75rem;
  font-weight: 700;
}
.dev-user-switcher span {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
.dev-user-switcher select {
  width: 100%;
  min-height: 36px;
  border: 0;
  border-radius: 6px;
  color: var(--text-color);
  background: transparent;
  font-size: .78rem;
}
@media (max-width: 380px) {
  .nav-links a { font-size: .68rem; }
  .nav-links svg { width: 19px; height: 19px; }
}
@media (min-width: 1024px) {
  .navbar { min-height: 72px; padding: 8px max(24px, calc((100vw - 1120px) / 2)); gap: 36px; }
  .logo { flex: 0 0 auto; }
  .nav-links { position: static; flex: 0 1 540px; max-width: 540px; min-height: auto; padding: 0; border: 0; background: transparent; box-shadow: none; }
  .nav-links a { flex-direction: row; gap: 7px; min-height: 42px; font-size: .84rem; }
  .nav-links svg { width: 18px; height: 18px; }
  .account-button { display: inline-flex; max-width: 150px; padding: 0 12px 0 4px; gap: 8px; border-radius: 999px; }
  .account-initial { display: grid; place-items: center; width: 29px; height: 29px; border-radius: 50%; background: var(--primary-soft); }
  .account-name { display: block; overflow: hidden; text-overflow: ellipsis; }
}
</style>
