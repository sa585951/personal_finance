<template>
  <div class="login-container">
    <div class="login-layout">
      <div class="login-intro">
        <div class="brand"><img class="brand-mark" src="/nomica-mark.svg" alt="" /><span>Nomica</span></div>
        <p class="eyebrow">把日常與旅程，放進同一本帳</p>
        <h1>每一筆生活，<br><em>都更有方向。</em></h1>
        <p class="intro-copy">清楚記錄日常收支、帳戶與旅行分攤，從今天開始掌握自己的財務節奏。</p>
        <div class="feature-list" aria-label="產品功能">
          <span>日常收支</span><span>帳戶總覽</span><span>旅行分攤</span>
        </div>
      </div>
      <div class="login-box">
        <img class="login-icon" src="/nomica-mark.svg" alt="" />
        <h2>歡迎回來</h2>
        <p>登入後繼續查看你的 Nomica 帳本。</p>
        <button type="button" @click="lineLogin" class="login-button">
          使用 LINE 繼續
        </button>
        <small>登入即會前往 LINE 完成驗證。</small>
      </div>
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
  display: grid;
  min-height: 100dvh;
  place-items: center;
  padding: 32px 20px;
  background: radial-gradient(circle at 17% 20%, #dfefe3 0, transparent 38%), #f7f8f4;
}
.login-layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(300px, 390px); align-items: center; gap: clamp(32px, 8vw, 110px); width: min(100%, 1060px); }
.brand { display: inline-flex; align-items: center; gap: 10px; color: #19332f; font-size: 1.3rem; font-weight: 850; letter-spacing: -0.04em; }
.brand-mark { width: 39px; height: 39px; border-radius: 13px; }
.eyebrow { margin: 64px 0 14px; color: #116f67; font-size: 0.83rem; font-weight: 800; letter-spacing: 0.09em; }
h1 { margin: 0; color: #19332f; font-size: clamp(2.8rem, 6vw, 5rem); font-weight: 850; letter-spacing: -0.07em; line-height: 1.18; }
h1 em { color: #116f67; font-style: normal; }
.intro-copy { max-width: 460px; margin: 24px 0 28px; color: #647570; font-size: 1.05rem; line-height: 1.8; }
.feature-list { display: flex; flex-wrap: wrap; gap: 8px; }
.feature-list span { padding: 7px 12px; color: #2f695f; background: #e7f2e9; border-radius: 999px; font-size: 0.8rem; font-weight: 750; }
.login-box {
  padding: clamp(28px, 5vw, 42px);
  background: #fff;
  border: 1px solid #e5e9e3;
  border-radius: 28px;
  box-shadow: 0 20px 55px rgba(30, 69, 56, 0.09);
}
.login-icon { display: block; width: 48px; height: 48px; margin-bottom: 30px; border-radius: 16px; }
h2 { margin: 0 0 8px; color: #19332f; font-size: 1.65rem; letter-spacing: -0.04em; }
.login-box p { margin: 0 0 30px; color: #647570; }
.login-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  width: 100%;
  min-height: 54px;
  padding: 10px 20px;
  border-radius: 14px;
  color: #fff;
  background: #06a842;
  font-size: 1rem;
  font-weight: 800;
}
.login-button:hover { background: #078d3a; }
.login-box small { display: block; margin-top: 16px; color: #7a8983; font-size: 0.75rem; text-align: center; }
@media (max-width: 740px) {
  .login-container { align-items: start; padding: max(34px, env(safe-area-inset-top)) 20px 36px; }
  .login-layout { max-width: 470px; grid-template-columns: 1fr; gap: 32px; }
  .eyebrow { margin-top: 38px; }
  .intro-copy { margin: 16px 0 20px; font-size: 0.95rem; }
  .login-box { border-radius: 24px; }
  .login-icon { display: none; }
}
</style>
