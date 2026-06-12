<template>
  <div class="login-container">
    <div class="login-box">
      <h1>歡迎來到個人財務管理系統</h1>
      <p>請登入以繼續</p>
      <p v-if="loginMessage" class="login-message">{{ loginMessage }}</p>
      <button @click="lineLogin" class="login-button">
        <img src="/line-logo.png" alt="LINE logo" class="line-logo" />
        使用 LINE 登入
      </button>
    </div>
  </div>
</template>

<script>
import apiClient from "@/api";

export default {
  name: 'LoginView',
  data() {
    return {
      loginMessage: '',
    };
  },
  mounted() {
    this.completePendingPwaLogin();
  },
  methods: {
    isStandalonePwa() {
      return window.navigator.standalone === true ||
        window.matchMedia('(display-mode: standalone)').matches;
    },
    createLoginNonce() {
      const bytes = new Uint8Array(32);
      window.crypto.getRandomValues(bytes);
      return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
    },
    async completePendingPwaLogin() {
      const nonce = localStorage.getItem('pendingPwaLoginNonce');
      if (!nonce) return;

      try {
        const response = await apiClient.get(`/api/auth/pwa-login-tokens/${encodeURIComponent(nonce)}`);
        if (response.data?.success && response.data.data?.token) {
          localStorage.setItem('authToken', response.data.data.token);
          localStorage.removeItem('pendingPwaLoginNonce');
          const redirectPath = this.safeRedirectPath(this.$route.query.redirect || '/');
          this.$router.replace(redirectPath);
        }
      } catch (error) {
        localStorage.removeItem('pendingPwaLoginNonce');
        this.loginMessage = '登入狀態已逾時，請重新使用 LINE 登入。';
      }
    },
    safeRedirectPath(value) {
      return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//')
        ? value
        : '/';
    },
    lineLogin() {
      const backendBaseUrl = import.meta.env.VITE_APP_API_URL;
      const redirectPath = this.safeRedirectPath(this.$route.query.redirect || '/');
      const params = new URLSearchParams({ redirect: redirectPath });
      if (this.isStandalonePwa()) {
        const nonce = this.createLoginNonce();
        localStorage.setItem('pendingPwaLoginNonce', nonce);
        params.set('pwa_nonce', nonce);
      }
      window.location.href = `${backendBaseUrl}/line-login-start?${params.toString()}`;
    },
  },
};
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f0f2f5;
}
.login-box {
  text-align: center;
  background: white;
  padding: 40px 50px;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}
h1 {
  font-size: 2rem;
  color: #333;
}
p {
  color: #666;
  margin-bottom: 30px;
}
.login-message {
  margin: 0 0 18px;
  color: #0f2742;
  font-size: 0.95rem;
  font-weight: 700;
}
.login-button {
  background-color: #00C300;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 1.2rem;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  transition: background-color 0.3s;
}
.login-button:hover {
  background-color: #00B300;
}
.line-logo {
  width: 32px;
  height: 32px;
}
</style>
