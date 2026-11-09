<template>
  <div class="account-page">
    <section class="account-hero">
      <h1>帳號設定</h1>
      <p>登入方式、資料匯出與帳號安全。</p>
    </section>

    <section class="account-card" aria-labelledby="login-methods">
      <div class="section-heading">
        <h2 id="login-methods">登入方式</h2>
        <span v-if="loading">讀取中</span>
      </div>

      <div v-if="errorMessage" class="state-message error">
        {{ errorMessage }}
      </div>
      <p v-else-if="!loading && !connectedProviders.length" class="muted">目前沒有綁定的登入方式。</p>
      <div v-else class="provider-list">
        <article v-for="provider in connectedProviders" :key="provider.provider" class="provider-item connected">
          <div>
            <h3>{{ providerLabel(provider.provider) }}</h3>
            <p>{{ providerDescription(provider) }}</p>
          </div>
          <span class="status-pill">已綁定</span>
        </article>
      </div>
    </section>

    <section class="account-card" aria-labelledby="data-export">
      <h2 id="data-export">匯出我的資料</h2>
      <p class="muted">下載 ZIP，內含帳戶、收支、轉帳、預算、旅行成員資格與 AI 解析紀錄的 CSV。</p>
      <button type="button" class="secondary-action" :disabled="busy === 'export'" @click="exportData">
        {{ busy === "export" ? "準備中" : "下載資料" }}
      </button>
    </section>

    <section class="account-card" aria-labelledby="sessions">
      <h2 id="sessions">登出所有裝置</h2>
      <p class="muted">手機遺失或在別人的電腦登入過時使用。所有裝置（包含這一台）都需要重新登入。</p>
      <button type="button" class="secondary-action" :disabled="busy === 'logout'" @click="logoutAll">
        {{ busy === "logout" ? "處理中" : "登出所有裝置" }}
      </button>
    </section>

    <section class="account-card danger" aria-labelledby="delete-account">
      <h2 id="delete-account">刪除帳號</h2>
      <ul class="muted">
        <li>你的帳戶、收支、預算與資產配置會立即從 Nomica 移除，30 天後永久清除。</li>
        <li>共享旅行中的紀錄會留給其他成員，你的名字會改為「已刪除的使用者」。</li>
        <li>若你是仍有其他成員的旅行擁有者，需先刪除那些旅行。</li>
        <li>之後再用 LINE 登入，會建立一個全新的空帳號。</li>
      </ul>
      <label for="deleteConfirmation" class="confirm-label">
        輸入「{{ confirmationPhrase }}」以確認
      </label>
      <input
        id="deleteConfirmation"
        v-model.trim="deleteConfirmation"
        type="text"
        autocomplete="off"
        :placeholder="confirmationPhrase"
      />
      <p v-if="deleteError" class="state-message error" role="alert">{{ deleteError }}</p>
      <button
        type="button"
        class="danger-action"
        :disabled="deleteConfirmation !== confirmationPhrase || busy === 'delete'"
        @click="deleteAccount"
      >
        {{ busy === "delete" ? "刪除中" : "永久刪除帳號" }}
      </button>
    </section>
  </div>
</template>

<script>
import apiClient from "@/api";

const CONFIRMATION_PHRASE = "刪除我的帳號";

export default {
  name: "AccountSettings",
  data() {
    return {
      loading: false,
      errorMessage: "",
      providers: [],
      busy: "",
      deleteConfirmation: "",
      deleteError: "",
      confirmationPhrase: CONFIRMATION_PHRASE,
    };
  },
  computed: {
    connectedProviders() {
      return this.providers.filter((provider) => provider.status === "connected");
    },
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
      return { line: "LINE", apple: "Apple", google: "Google" }[provider] || provider;
    },
    providerDescription(provider) {
      if (provider.provider === "line") return "用於登入，也可以在 LINE 直接記帳。";
      return provider.email || "已綁定。";
    },
    async exportData() {
      this.busy = "export";
      try {
        const response = await apiClient.get("/api/account/export", { responseType: "blob" });
        const url = URL.createObjectURL(response.data);
        const link = document.createElement("a");
        const match = /filename="([^"]+)"/.exec(response.headers?.["content-disposition"] || "");
        link.href = url;
        link.download = match?.[1] || "nomica-export.zip";
        document.body.append(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
      } catch (error) {
        this.$swal.fire("匯出失敗", "目前無法產生匯出檔，請稍後再試。", "error");
      } finally {
        this.busy = "";
      }
    },
    async logoutAll() {
      const result = await this.$swal.fire({
        title: "登出所有裝置？",
        text: "包含這一台裝置，之後都需要重新登入。",
        showCancelButton: true,
        confirmButtonText: "登出所有裝置",
        cancelButtonText: "取消",
      });
      if (!result.isConfirmed) return;
      this.busy = "logout";
      try {
        await apiClient.post("/api/auth/logout-all");
        this.$router.replace({ name: "Login" });
      } catch (error) {
        this.$swal.fire("操作失敗", "目前無法登出所有裝置，請稍後再試。", "error");
      } finally {
        this.busy = "";
      }
    },
    async deleteAccount() {
      this.busy = "delete";
      this.deleteError = "";
      try {
        await apiClient.post("/api/account/delete", { confirmation: this.deleteConfirmation });
        this.$router.replace({ name: "Login", query: { deleted: "1" } });
      } catch (error) {
        this.deleteError = error.response?.data?.message || "目前無法刪除帳號，請稍後再試。";
      } finally {
        this.busy = "";
      }
    },
  },
};
</script>

<style scoped>
.account-page {
  min-height: 100vh;
  padding: 72px 16px 104px;
  background: var(--secondary-color);
  color: var(--text-color);
}

.account-hero,
.account-card {
  display: grid;
  gap: 10px;
  width: min(880px, 100%);
  margin: 0 auto 16px;
  padding: 18px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

h1,
h2,
h3,
p,
ul {
  margin: 0;
}

.account-hero h1 {
  font-size: 1.7rem;
}

.account-hero p,
.muted,
.provider-item p {
  color: var(--light-text-color);
  line-height: 1.55;
}

ul.muted {
  padding-left: 1.2em;
}

.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.account-card h2 {
  font-size: 1.05rem;
}

.section-heading span {
  color: var(--light-text-color);
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
  border: 1px solid var(--brand-border);
  border-radius: 8px;
  background: var(--primary-soft);
}

.provider-item h3 {
  margin-bottom: 4px;
  font-size: 1rem;
}

.status-pill {
  align-self: flex-start;
  white-space: nowrap;
  padding: 5px 8px;
  color: var(--primary-color);
  background: var(--card-bg);
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 800;
}

.secondary-action,
.danger-action {
  justify-self: start;
  min-height: 44px;
  padding: 0 16px;
  border-radius: 8px;
  font-weight: 800;
  cursor: pointer;
}

.secondary-action {
  color: var(--text-color);
  background: var(--secondary-color);
  border: 1px solid var(--border-color);
}

.account-card.danger {
  border-color: var(--expense-color);
}

.account-card.danger h2 {
  color: var(--expense-color);
}

.confirm-label {
  font-weight: 700;
}

#deleteConfirmation {
  min-height: 44px;
  padding: 0 12px;
  color: var(--text-color);
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.danger-action {
  color: var(--on-primary);
  background: var(--expense-color);
  border: none;
}

.secondary-action:disabled,
.danger-action:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.state-message {
  padding: 12px;
  border-radius: 8px;
  font-weight: 700;
}

.state-message.error {
  color: var(--expense-color);
  background: var(--expense-soft);
}

@media (max-width: 520px) {
  .provider-item {
    flex-direction: column;
  }
}
</style>
