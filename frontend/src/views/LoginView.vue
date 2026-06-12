<template>
  <div class="login-container">
    <div class="login-box">
      <h1>歡迎來到個人財務管理系統</h1>
      <p>請登入以繼續</p>
      <button @click="lineLogin" class="login-button">
        <img src="/line-logo.png" alt="LINE logo" class="line-logo" />
        使用 LINE 登入
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'LoginView',
  methods: {
    safeRedirectPath(value) {
      return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//')
        ? value
        : '/';
    },
    lineLogin() {
      const backendBaseUrl = import.meta.env.VITE_APP_API_URL;
      const redirectPath = this.safeRedirectPath(this.$route.query.redirect || '/');
      const params = new URLSearchParams({ redirect: redirectPath });
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
