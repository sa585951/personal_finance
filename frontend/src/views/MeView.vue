<template>
  <div class="me-page">
    <h1>我的</h1>

    <nav class="me-group" aria-label="帳本">
      <router-link v-for="item in ledgerLinks" :key="item.to" :to="item.to" class="me-row">
        <span>
          <strong>{{ item.label }}</strong>
          <small>{{ item.hint }}</small>
        </span>
        <ArrowRight aria-hidden="true" />
      </router-link>
    </nav>

    <nav class="me-group" aria-label="設定">
      <router-link to="/account" class="me-row">
        <span>
          <strong>帳號與隱私</strong>
          <small>登入方式、匯出資料、刪除帳號</small>
        </span>
        <ArrowRight aria-hidden="true" />
      </router-link>
      <router-link to="/privacy" class="me-row">
        <span><strong>隱私權政策</strong></span>
        <ArrowRight aria-hidden="true" />
      </router-link>
      <router-link to="/terms" class="me-row">
        <span><strong>服務條款</strong></span>
        <ArrowRight aria-hidden="true" />
      </router-link>
      <div class="me-row me-row--static">
        <span><strong>外觀</strong></span>
        <ThemeToggle show-label />
      </div>
    </nav>
  </div>
</template>

<script>
import { ArrowRight } from "@element-plus/icons-vue";
import ThemeToggle from "@/components/shared/ThemeToggle.vue";

export default {
  name: "MeView",
  components: { ArrowRight, ThemeToggle },
  data() {
    return {
      ledgerLinks: [
        { to: "/assets", label: "帳戶", hint: "餘額、轉帳、信用卡帳期" },
        { to: "/budgets", label: "預算", hint: "每月各類別上限" },
        { to: "/analysis", label: "分析", hint: "趨勢與類別分佈" },
        { to: "/allocation", label: "資產配置", hint: "投資標的與成本" },
      ],
    };
  },
};
</script>

<style scoped>
.me-page {
  max-width: var(--compact-page-max-width);
  margin: 0 auto;
  padding: 20px 16px calc(var(--app-bottom-nav-height) + 24px);
  color: var(--text-color);
}

h1 {
  margin: 0 0 20px;
  font-size: 1.5rem;
}

.me-group {
  margin-bottom: 20px;
  border-top: 1px solid var(--border-color);
}

.me-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 60px;
  padding: 10px 2px;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-color);
  text-decoration: none;
}

.me-row span {
  display: grid;
  gap: 2px;
}

.me-row small {
  color: var(--light-text-color);
  font-size: 0.82rem;
}

.me-row svg {
  width: 16px;
  height: 16px;
  color: var(--light-text-color);
}
</style>
