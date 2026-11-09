<template>
  <div class="login-container">
    <header class="login-top">
      <div class="brand"><img class="brand-mark" src="/nomica-mark.svg" alt="" /><span>Nomica</span></div>
      <ThemeToggle show-label />
    </header>

    <main class="login-main">
      <section class="hero" aria-label="Nomica 是什麼">
        <h1>在 LINE 說一句話記帳<br>旅行分帳，自動回到帳本</h1>
      </section>

      <ol class="steps">
        <li v-for="step in steps" :key="step.title">
          <component :is="step.icon" aria-hidden="true" />
          <span>
            <strong>{{ step.title }}</strong>
            <small>{{ step.detail }}</small>
          </span>
        </li>
      </ol>

      <p v-if="$route.query.deleted === '1'" class="login-notice" role="status">帳號已刪除。資料會在 30 天後永久清除。</p>
      <button type="button" class="login-button" @click="lineLogin">使用 LINE 開始</button>
      <small class="legal">
        登入即表示你同意<router-link to="/terms">服務條款</router-link>與<router-link to="/privacy">隱私權政策</router-link>。
      </small>
    </main>
  </div>
</template>

<script>
import { ChatLineRound, Notebook, User } from "@element-plus/icons-vue";
import ThemeToggle from "@/components/shared/ThemeToggle.vue";
import { safeRedirectPath } from "@/utils/authNavigation";

export default {
  name: "LoginView",
  components: { ChatLineRound, Notebook, ThemeToggle, User },
  data() {
    return {
      steps: [
        { icon: "ChatLineRound", title: "「午餐 120 刷玉山卡」", detail: "說完就是一筆草稿，確認才入帳" },
        { icon: "User", title: "和旅伴共用一本旅行帳", detail: "誰付、誰欠，自動算好" },
        { icon: "Notebook", title: "回國後，你的那份進月報", detail: "不用再手動對帳" },
      ],
    };
  },
  methods: {
    safeRedirectPath(value) {
      return safeRedirectPath(value);
    },
    lineLogin() {
      const backendBaseUrl = import.meta.env.PROD ? "" : (import.meta.env.VITE_APP_API_URL || "");
      const redirectPath = this.safeRedirectPath(this.$route.query.redirect || "/");
      const params = new URLSearchParams({ redirect: redirectPath });
      window.location.href = `${backendBaseUrl}/line-login-start?${params.toString()}`;
    },
  },
};
</script>

<style scoped>
.login-container {
  min-height: 100dvh;
  padding: max(16px, env(safe-area-inset-top)) 16px 32px;
  color: var(--text-color);
  background: var(--page-bg);
}

.login-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 440px;
  margin: 0 auto;
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-size: 1.2rem;
  font-weight: 800;
}

.brand-mark {
  width: 34px;
  height: 34px;
  border-radius: 10px;
}

.login-main {
  display: grid;
  gap: 18px;
  max-width: 440px;
  margin: 24px auto 0;
}

.hero {
  display: flex;
  align-items: flex-end;
  min-height: 190px;
  padding: 20px;
  border-radius: 18px;
  color: #ffffff;
  background: #1f5a73;
}

.hero h1 {
  margin: 0;
  font-size: 1.5rem;
  line-height: 1.4;
  text-wrap: balance;
}

.steps {
  display: grid;
  gap: 14px;
  margin: 4px 0 6px;
  padding: 0;
  list-style: none;
}

.steps li {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.steps svg {
  flex: none;
  width: 22px;
  height: 22px;
  margin-top: 2px;
  color: var(--light-text-color);
}

.steps span {
  display: grid;
  gap: 2px;
}

.steps small,
.legal {
  color: var(--light-text-color);
  font-size: 0.85rem;
}

.login-notice {
  margin: 0;
  padding: 12px 14px;
  border-radius: 10px;
  background: var(--secondary-color);
}

.login-button {
  width: 100%;
  min-height: 54px;
  border-radius: 14px;
  color: var(--on-primary);
  background: var(--primary-color);
  font-size: 1rem;
  font-weight: 800;
}

.legal {
  text-align: center;
}

.legal a {
  color: var(--text-color);
}

@media (min-width: 900px) {
  .hero {
    min-height: 240px;
  }

  .hero h1 {
    font-size: 1.9rem;
  }
}
</style>
