<template>
  <div class="goals-screen">
    <header class="goals-header">
      <p class="eyebrow">Deferred</p>
      <h1>財務目標</h1>
    </header>

    <section class="placeholder-card">
      <div class="status-pill">MVP 後開放</div>
      <h2>這個功能尚未開啟</h2>
      <p>
        財務目標會先暫緩，等日常記帳、旅行帳本、多幣別與分帳流程穩定後再重新設計。
      </p>
      <router-link class="primary-link" to="/">回首頁</router-link>
    </section>
  </div>
</template>

<script>
export default {
  name: "FinancialGoals",
};
</script>

<style scoped>
.goals-screen {
  max-width: 520px;
  min-height: calc(100vh - 80px);
  margin: 0 auto;
  padding: 24px 14px calc(var(--app-bottom-nav-height) + 22px);
  color: #1f2933;
}

.goals-header {
  margin-bottom: 1rem;
}

.eyebrow {
  margin: 0 0 4px;
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
}

h1,
h2 {
  margin: 0;
  letter-spacing: 0;
}

h1 {
  color: var(--text-color);
  font-size: 1.85rem;
}

.placeholder-card {
  padding: 20px;
  border: 1px solid #dbe4ee;
  border-radius: 10px;
  background: #ffffff;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 4px 10px;
  border-radius: 999px;
  background: #e0f2fe;
  color: #075985;
  font-size: 0.82rem;
  font-weight: 700;
}

.placeholder-card h2 {
  margin-top: 14px;
  color: #1f2933;
  font-size: 1.35rem;
}

.placeholder-card p {
  margin: 10px 0 18px;
  color: #64748b;
  line-height: 1.7;
}

.primary-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  width: 100%;
  border-radius: 8px;
  background: #0f766e;
  color: #ffffff;
  font-weight: 700;
  text-decoration: none;
}
</style>
