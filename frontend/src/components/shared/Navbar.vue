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
      <ThemeToggle />
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
        <button class="account-button" type="button" :aria-label="`帳號選單：${userName || '帳號'}`" :aria-expanded="showAccountMenu" @click="showAccountMenu = !showAccountMenu">
          <span class="account-initial" aria-hidden="true">{{ (userName || "帳")[0] }}</span>
          <span class="account-name">{{ userName || "帳號" }}</span>
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
  border-top: 1px solid var(--border-color);
  box-shadow: 0 -8px 24px rgba(15, 23, 42, 0.08);
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 4px;
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
  flex: 1 1 auto;
  min-width: 0;
  max-width: 520px;
  margin: 0;
  padding: 0;
}

.nav-links li {
  flex: 1;
}

.nav-links a {
  color: var(--light-text-color);
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
  color: var(--primary-color);
  background: var(--primary-soft);
  border-bottom: 0;
  transform: none;
}

.nav-links a.router-link-active svg,
.nav-links a.router-link-exact-active svg {
  color: var(--primary-color);
}

.nav-links a span {
  line-height: 1;
}

@media (min-width: 1px) {
  .auth-section {
    display: flex;
    align-items: center;
    gap: 4px;
    position: relative;
    flex: 0 0 auto;
    z-index: 1;
  }

  .dev-user-switcher {
    display: inline-flex;
    align-items: center;
    padding: 4px;
    color: var(--text-color);
    background: var(--secondary-color);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    font-size: 0.75rem;
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
    width: 74px;
    min-height: 28px;
    border: 1px solid var(--border-color);
    border-radius: 6px;
    background: var(--card-bg);
    font-size: 0.78rem;
  }

  .account-button {
    min-height: 34px;
    max-width: 78px;
    padding: 6px 8px;
    color: var(--text-color);
    background: rgba(255, 255, 255, 0.94);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    font-size: 0.78rem;
    font-weight: 800;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .account-menu {
    position: absolute;
    bottom: calc(100% + 8px);
    right: 0;
    min-width: 150px;
    padding: 10px;
    display: grid;
    gap: 8px;
    color: var(--text-color);
    background: var(--card-bg);
    border: 1px solid var(--border-color);
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
    color: var(--primary-color);
    background: var(--primary-soft);
    border: 1px solid var(--brand-border);
  }

.logout-button {
  color: var(--expense-color);
  background: var(--expense-soft);
  border: 1px solid var(--expense-color);
}
}

/* Product navigation */
.navbar {
  left: 10px;
  right: 10px;
  bottom: max(8px, env(safe-area-inset-bottom));
  min-height: 68px;
  padding: 6px;
  border: 1px solid var(--border-color);
  border-radius: 18px;
  background: var(--card-bg);
  box-shadow: 0 4px 16px rgba(23, 26, 31, 0.08);
}
.nav-links { max-width: 540px; gap: 2px; }
.nav-links a {
  min-height: 54px;
  border-radius: 15px;
  color: var(--light-text-color);
  font-size: 0.72rem;
  font-weight: 700;
  transition: background-color 180ms ease, color 180ms ease, transform 180ms ease;
}
.nav-links svg { width: 21px; height: 21px; }
.nav-links a:hover,
.nav-links a.router-link-active,
.nav-links a.router-link-exact-active {
  color: var(--primary-color);
  background: var(--primary-soft);
}
.nav-links a.router-link-active svg,
.nav-links a.router-link-exact-active svg { color: var(--primary-color); }
.nav-links a[href="/trips"].router-link-active,
.nav-links a[href="/trips"].router-link-exact-active { color: var(--travel-color); background: var(--travel-soft); }
.nav-links a[href="/trips"].router-link-active svg,
.nav-links a[href="/trips"].router-link-exact-active svg { color: var(--travel-color); }
.account-button {
  display: grid;
  place-items: center;
  width: 38px;
  min-width: 38px;
  height: 38px;
  padding: 0;
  border: 1px solid var(--brand-border);
  border-radius: 50%;
  color: var(--primary-color);
  background: var(--primary-soft);
}
.account-initial { font-size: 0.9rem; font-weight: 800; }
.account-name { display: none; }
.account-menu { border-radius: 16px; border-color: var(--border-color); background: var(--card-bg); }
.account-menu-link { color: var(--primary-color); background: var(--primary-soft); border-color: var(--brand-border); }
.dev-user-switcher { border-radius: 12px; border-color: var(--border-color); background: var(--secondary-color); }
.dev-user-switcher select { width: 58px; border: 0; background: transparent; color: var(--text-color); }
.auth-section :deep(.theme-toggle) { width: 42px; min-width: 42px; min-height: 42px; padding: 0; border-radius: 13px; }
@media (max-width: 380px) {
  .navbar { left: 6px; right: 6px; }
  .nav-links a { font-size: 0.68rem; }
  .nav-links svg { width: 19px; height: 19px; }
}
@media (min-width: 1024px) {
  .navbar {
    top: 0;
    bottom: auto;
    left: 0;
    right: 0;
    min-height: 72px;
    padding: 8px max(24px, calc((100vw - 1120px) / 2));
    justify-content: space-between;
    gap: 36px;
    border: 0;
    border-bottom: 1px solid var(--border-color);
    border-radius: 0;
    box-shadow: 0 2px 10px rgba(23, 26, 31, 0.04);
  }
  .logo { display: block; flex: 0 0 auto; }
  .logo a {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    color: var(--text-color);
    font-size: 1.2rem;
    font-weight: 850;
    letter-spacing: -0.04em;
    text-decoration: none;
  }
  .logo-mark { width: 34px; height: 34px; border-radius: 11px; }
  .nav-links { flex: 0 1 540px; }
  .nav-links a { flex-direction: row; gap: 7px; min-height: 42px; font-size: 0.84rem; }
  .nav-links svg { width: 18px; height: 18px; }
  .account-button { display: inline-flex; width: auto; max-width: 150px; padding: 0 12px 0 4px; gap: 8px; border-radius: 999px; }
  .account-initial { display: grid; place-items: center; width: 29px; height: 29px; border-radius: 50%; background: var(--primary-soft); }
  .account-name { display: block; overflow: hidden; text-overflow: ellipsis; }
  .account-menu { top: calc(100% + 10px); bottom: auto; }
}
</style>
