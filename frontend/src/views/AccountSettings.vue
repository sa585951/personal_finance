<template>
  <div class="account-page">
    <section class="account-hero">
      <p class="eyebrow">Nomica Account</p>
      <h1>帳號設定</h1>
      <p>管理你的登入方式。Nomica 主帳號會串接 Web、LINE 與未來 iOS App。</p>
    </section>

    <section class="account-card">
      <div class="section-heading">
        <h2>已綁定登入方式</h2>
        <span v-if="loading">讀取中</span>
      </div>

      <div v-if="errorMessage" class="state-message error">
        {{ errorMessage }}
      </div>

      <div v-else class="provider-list">
        <article
          v-for="provider in providers"
          :key="provider.provider"
          class="provider-item"
          :class="{ connected: provider.status === 'connected' }"
        >
          <div>
            <h3>{{ providerLabel(provider.provider) }}</h3>
            <p>{{ providerDescription(provider) }}</p>
          </div>
          <span class="status-pill">
            {{ provider.status === 'connected' ? '已啟用' : '尚未啟用' }}
          </span>
        </article>
      </div>
    </section>

    <section class="account-note">
      <h2>Phase 7.1 範圍</h2>
      <p>Apple 與 Google 登入會在後續階段接入；本輪先建立可撤銷 session 與多 provider 帳號地基。</p>
    </section>
  </div>
</template>

<script>
import apiClient from "@/api";

export default {
  name: "AccountSettings",
  data() {
    return {
      loading: false,
      errorMessage: "",
      providers: [],
    };
  },
  mounted() {
    this.fetchAccount();
  },
  methods: {
    async fetchAccount() {
      this.loading = true;
      this.errorMessage = "";
      try {
        const response = await apiClient.get("/api/auth/account");
        this.providers = response.data?.data?.providers || [];
      } catch (error) {
        this.errorMessage = "目前無法讀取帳號設定，請稍後再試。";
      } finally {
        this.loading = false;
      }
    },
    providerLabel(provider) {
      const labels = {
        line: "LINE",
        apple: "Apple",
        google: "Google",
      };
      return labels[provider] || provider;
    },
    providerDescription(provider) {
      if (provider.provider === "line" && provider.status === "connected") {
        return "可用於登入，也會作為 LINE 快速記帳與查詢入口。";
      }
      if (provider.provider === "apple") {
        return "預留給未來 iOS App 與 Sign in with Apple。";
      }
      if (provider.provider === "google") {
        return "預留給未來 Web 與跨平台登入。";
      }
      return provider.role || "尚未啟用。";
    },
  },
};
</script>

<style scoped>
.account-page {
  min-height: 100vh;
  padding: 72px 16px 104px;
  background: #f8fafc;
  color: #1f2937;
}

.account-hero,
.account-card,
.account-note {
  width: min(880px, 100%);
  margin: 0 auto 16px;
  padding: 18px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
}

.eyebrow {
  margin: 0 0 6px;
  color: #0f766e;
  font-size: 0.78rem;
  font-weight: 800;
  text-transform: uppercase;
}

h1,
h2,
h3,
p {
  margin: 0;
}

.account-hero h1 {
  margin-bottom: 8px;
  font-size: 1.7rem;
}

.account-hero p,
.account-note p,
.provider-item p {
  color: #64748b;
  line-height: 1.55;
}

.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.section-heading h2,
.account-note h2 {
  font-size: 1.05rem;
}

.section-heading span {
  color: #64748b;
  font-size: 0.82rem;
  font-weight: 700;
}

.provider-list {
  display: grid;
  gap: 10px;
}

.provider-item {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding: 14px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
}

.provider-item.connected {
  border-color: #99f6e4;
  background: #f0fdfa;
}

.provider-item h3 {
  margin-bottom: 4px;
  font-size: 1rem;
}

.status-pill {
  align-self: flex-start;
  white-space: nowrap;
  padding: 5px 8px;
  color: #334155;
  background: #e2e8f0;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 800;
}

.provider-item.connected .status-pill {
  color: #0f766e;
  background: #ccfbf1;
}

.state-message {
  padding: 12px;
  border-radius: 8px;
  font-weight: 700;
}

.state-message.error {
  color: #991b1b;
  background: #fee2e2;
}

@media (max-width: 520px) {
  .provider-item {
    flex-direction: column;
  }
}
</style>
