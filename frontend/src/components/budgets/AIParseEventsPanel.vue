<template>
  <section class="parse-events-panel">
    <button class="panel-toggle" type="button" @click="isOpen = !isOpen">
      <span>AI 解析紀錄</span>
      <small>{{ isOpen ? "收合" : "展開" }}</small>
    </button>

    <div v-if="isOpen" class="panel-body">
      <div class="panel-actions">
        <p>開發用，確認解析是否被採用。</p>
        <button type="button" :disabled="isLoading" @click="fetchEvents">
          {{ isLoading ? "更新中" : "更新" }}
        </button>
      </div>

      <p v-if="errorMessage" class="panel-message error">{{ errorMessage }}</p>
      <p v-else-if="!events.length" class="panel-message">目前沒有解析紀錄。</p>

      <ul v-else class="event-list">
        <li v-for="event in events" :key="event.id">
          <div class="event-main">
            <span :class="['status-dot', event.status]">{{ statusLabel(event.status) }}</span>
            <strong>{{ event.raw_input }}</strong>
          </div>
          <div class="event-meta">
            <span>{{ sourceLabel(event.source) }}</span>
            <span>{{ event.result_type || "未分類" }}</span>
            <span>{{ formatTime(event.created_at) }}</span>
          </div>
        </li>
      </ul>
    </div>
  </section>
</template>

<script>
import apiClient from "@/api";

export default {
  name: "AIParseEventsPanel",
  data() {
    return {
      isOpen: false,
      isLoading: false,
      events: [],
      errorMessage: "",
    };
  },
  methods: {
    async fetchEvents() {
      this.isLoading = true;
      this.errorMessage = "";
      try {
        const response = await apiClient.get("/api/ai/parse-events?limit=5");
        this.events = response.data.data || [];
      } catch (error) {
        console.error("無法載入 AI 解析紀錄", error);
        this.errorMessage = error.response?.data?.message || "解析紀錄載入失敗。";
      } finally {
        this.isLoading = false;
      }
    },
    statusLabel(status) {
      const labelMap = {
        success: "未採用",
        confirmed: "已採用",
        failed: "失敗",
        cancelled: "取消",
      };
      return labelMap[status] || status || "未知";
    },
    sourceLabel(source) {
      const labelMap = {
        web: "Web",
        line_bot: "LINE",
        pwa: "PWA",
        ios: "iOS",
      };
      return labelMap[source] || source || "未知來源";
    },
    formatTime(value) {
      if (!value) return "";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return value;
      return date.toLocaleString("zh-TW", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      });
    },
  },
};
</script>

<style scoped>
.parse-events-panel {
  margin: 0 0 1rem;
  border: 1px dashed #cbd5e1;
  border-radius: 10px;
  background: #ffffff;
}

.panel-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  min-height: 42px;
  padding: 0 12px;
  color: #475569;
  background: transparent;
  border: 0;
  box-shadow: none;
  font-weight: 900;
}

.panel-toggle small {
  color: #64748b;
  font-weight: 800;
}

.panel-body {
  padding: 0 12px 12px;
}

.panel-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding-top: 4px;
}

.panel-actions p {
  margin: 0;
  color: #64748b;
  font-size: 0.82rem;
  font-weight: 700;
}

.panel-actions button {
  min-height: 32px;
  padding: 0 10px;
  color: #0f172a;
  background: #e2e8f0;
  border: 0;
  border-radius: 8px;
  box-shadow: none;
  font-weight: 800;
}

.panel-message {
  margin: 10px 0 0;
  color: #64748b;
  font-size: 0.86rem;
  font-weight: 700;
}

.panel-message.error {
  color: #b91c1c;
}

.event-list {
  display: grid;
  gap: 8px;
  padding: 0;
  margin: 10px 0 0;
  list-style: none;
}

.event-list li {
  padding: 10px;
  background: #f8fafc;
  border-radius: 8px;
}

.event-main {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.event-main strong {
  color: #0f172a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-dot {
  flex: 0 0 auto;
  min-width: 54px;
  padding: 3px 7px;
  color: #475569;
  background: #e2e8f0;
  border-radius: 999px;
  font-size: 0.74rem;
  font-weight: 900;
  text-align: center;
}

.status-dot.confirmed {
  color: #166534;
  background: #dcfce7;
}

.status-dot.success {
  color: #1d4ed8;
  background: #dbeafe;
}

.status-dot.failed {
  color: #b91c1c;
  background: #fee2e2;
}

.event-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 6px;
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 700;
}
</style>
