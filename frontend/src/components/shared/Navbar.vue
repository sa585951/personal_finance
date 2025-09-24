<template>
  <nav class="navbar">
    <div class="logo">
      <router-link to="/">財務管理</router-link>
    </div>
    <ul class="nav-links">
      <li>
        <router-link to="/">首頁</router-link>
      </li>
      <li>
        <router-link to="/assets">資產</router-link>
      </li>
      <li>
        <router-link to="/transactions">收支</router-link>
      </li>
      <li>
        <router-link to="/budgets">預算</router-link>
      </li>
      <li>
        <router-link to="/goals">目標</router-link>
      </li>
    </ul>
    <div class="auth-section">
      <template v-if="isLoggedIn">
        <span>歡迎, {{ userName }}</span>
        <button @click="logout" style="margin-left: 20px; background-color: red;">登出</button>
      </template>
      <template v-else>
        <button @click="lineLogin" style="background-color:green">Line 登入</button>
      </template>
    </div>
  </nav>
</template>

<script>
import { jwtDecode } from 'jwt-decode';

export default {
  name: 'Navbar',
  data() {
    return {
      isLoggedIn: false,
      userName: '',
    };
  },
  mounted() {
    this.checkLoginStatus();
  },
  methods: {
    checkLoginStatus() {
      const token = localStorage.getItem('authToken');
      if (token) {
        try {
          const decoded = jwtDecode(token);
          // 檢查 token 是否過期
          if (decoded.exp * 1000 > Date.now()) {
            this.isLoggedIn = true;
            this.userName = decoded.name; // 從 JWT payload 中讀取 name
          } else {
            // Token 過期，執行登出
            this.logout();
          }
        } catch (error) {
          console.error("JWT 解碼失敗:", error);
          this.logout();
        }
      } else {
        this.isLoggedIn = false;
        this.userName = '';
      }
    },
    lineLogin() {
      const LINE_CHANNEL_ID = import.meta.env.VITE_LINE_LOGIN_CHANNEL_ID;
      const backendBaseUrl = import.meta.env.BACKEND_BASE_URL;
      const redirectUri = `${backendBaseUrl}/line-login-callback`;
      const state = Math.random().toString(36).substring(2, 15);

      sessionStorage.setItem('line_login_state', state);

      const authUrl = `https://access.line.me/oauth2/v2.1/authorize?` +
                      `response_type=code&` +
                      `client_id=${LINE_CHANNEL_ID}&` +
                      `redirect_uri=${encodeURIComponent(redirectUri)}&` +
                      `state=${state}&` +
                      `scope=profile%20openid`;
      
      window.location.href = authUrl;
    },
    logout() {
      localStorage.removeItem('authToken'); // 確保移除的是 authToken
      this.isLoggedIn = false;
      this.userName = '';
      if (this.$route.path !== '/') {
        this.$router.push('/');
      } else {
        window.location.reload();
      }
    },
  },
};
</script>

<style scoped>
.navbar {
  background-color: var(--card-bg);
  padding: 1rem 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo a {
  font-weight: bold;
  font-size: 1.5rem;
  color: var(--primary-color);
  text-decoration: none;
}

.nav-links {
  list-style: none;
  display: flex;
  gap: 2rem;
}

.nav-links a {
  color: var(--text-color);
  text-decoration: none;
  font-weight: 500;
  transition: color 0.3s ease;
}

.nav-links a:hover,
.nav-links a.router-link-active {
  color: var(--primary-color);
  border-bottom: 2px solid var(--primary-color);
}
</style>