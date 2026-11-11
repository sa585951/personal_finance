<template>
  <div class="usage-page">
    <router-link to="/me" class="back-link">← 我的</router-link>
    <h1>使用概況</h1>
    <p class="note">只有你看得到。這裡只統計人數和筆數，不含任何金額、品項或備註。</p>

    <p v-if="loading" class="state">載入中</p>
    <div v-else-if="errorMessage" class="state" role="alert">
      <p>{{ errorMessage }}</p>
      <button type="button" class="retry" @click="load">重新載入</button>
    </div>
    <template v-else-if="overview">
      <div class="totals">
        <div><strong>{{ overview.total_users }}</strong><small>總使用者</small></div>
        <div><strong>{{ overview.active_users }}</strong><small>近 {{ overview.recent_days }} 天有記帳</small></div>
      </div>

      <ul class="user-list">
        <li v-for="(user, index) in overview.users" :key="index" class="user-row">
          <div class="user-main">
            <strong>{{ user.name }}</strong>
            <small>{{ lastRecordText(user) }}</small>
          </div>
          <div class="user-counts">
            <span>共 {{ user.total_records }} 筆</span>
            <small>近 {{ overview.recent_days }} 天 {{ user.recent_records }} 筆</small>
          </div>
        </li>
      </ul>
      <p v-if="overview.total_users > overview.users.length" class="note">
        只列出最近活動的 {{ overview.users.length }} 位。
      </p>
    </template>
  </div>
</template>

<script>
import apiClient from "@/api";

const DAY_MS = 24 * 60 * 60 * 1000;

export default {
  name: "AdminUsageView",
  data() {
    return { overview: null, loading: false, errorMessage: "" };
  },
  mounted() {
    this.load();
  },
  methods: {
    async load() {
      this.loading = true;
      this.errorMessage = "";
      try {
        const data = (await apiClient.get("/api/admin/usage")).data?.data;
        if (!data || !Array.isArray(data.users)) throw new Error("bad shape");
        this.overview = data;
      } catch (error) {
        this.overview = null;
        this.errorMessage = error.response?.status === 404 ? "沒有權限查看這個頁面。" : "請確認網路連線後重試。";
      } finally {
        this.loading = false;
      }
    },
    lastRecordText(user) {
      const joined = this.dayText(user.joined_at);
      if (!user.last_record_at) return `${joined} 加入 · 還沒記過帳`;
      return `${joined} 加入 · 最後記帳 ${this.agoText(user.last_record_at)}`;
    },
    dayText(value) {
      const date = new Date(value);
      return Number.isNaN(date.getTime()) ? "" : `${date.getMonth() + 1}/${date.getDate()}`;
    },
    agoText(value) {
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return "";
      const days = Math.floor((Date.now() - date.getTime()) / DAY_MS);
      if (days <= 0) return "今天";
      return days === 1 ? "昨天" : `${days} 天前`;
    },
  },
};
</script>

<style scoped>
.usage-page {
  max-width: var(--compact-page-max-width);
  margin: 0 auto;
  padding: 20px 16px calc(var(--app-bottom-nav-height) + 24px);
  color: var(--text-color);
}

.back-link {
  color: var(--primary-color);
  text-decoration: none;
  font-weight: 700;
}

h1 {
  margin: 12px 0 6px;
  font-size: 1.5rem;
}

.note,
.state,
small {
  color: var(--light-text-color);
  font-size: 0.84rem;
  line-height: 1.5;
}

.note {
  margin: 0 0 16px;
}

.totals {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 16px;
}

.totals div {
  display: grid;
  gap: 2px;
  padding: 14px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.totals strong {
  font-size: 1.6rem;
}

.user-list {
  margin: 0;
  padding: 0;
  list-style: none;
  border-top: 1px solid var(--border-color);
}

.user-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 2px;
  border-bottom: 1px solid var(--border-color);
}

.user-main,
.user-counts {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.user-main strong {
  overflow-wrap: anywhere;
}

.user-counts {
  text-align: right;
  white-space: nowrap;
}

.retry {
  min-height: 40px;
  padding: 0 16px;
}
</style>
