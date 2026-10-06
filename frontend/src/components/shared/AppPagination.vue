<template>
  <nav class="app-pagination" :aria-label="ariaLabel">
    <p v-if="error" class="pagination-error" role="alert">
      {{ error }}
      <button type="button" :disabled="loading" @click="$emit('retry')">重試</button>
    </p>
    <p class="pagination-status" aria-live="polite">
      <template v-if="hasTotalCount">
        第 {{ currentPage }} / {{ totalPages }} 頁 · 共 {{ totalCount }} 筆
      </template>
      <template v-else>第 {{ currentPage }} 頁</template>
    </p>
    <div class="pagination-actions">
      <button
        type="button"
        :disabled="loading || !hasPrevious"
        aria-label="前往上一頁"
        @click="$emit('previous')"
      >
        上一頁
      </button>
      <button
        type="button"
        :disabled="loading || !hasNext"
        aria-label="前往下一頁"
        @click="$emit('next')"
      >
        {{ loading ? "載入中…" : "下一頁" }}
      </button>
    </div>
  </nav>
</template>

<script>
export default {
  name: "AppPagination",
  props: {
    currentPage: { type: Number, default: 1 },
    pageSize: { type: Number, default: 20 },
    totalCount: { type: Number, default: null },
    hasNext: { type: Boolean, default: false },
    hasPrevious: { type: Boolean, default: false },
    loading: { type: Boolean, default: false },
    error: { type: String, default: "" },
    ariaLabel: { type: String, default: "分頁導覽" },
  },
  emits: ["next", "previous", "retry"],
  computed: {
    hasTotalCount() {
      return Number.isFinite(this.totalCount) && this.totalCount >= 0;
    },
    totalPages() {
      if (!this.hasTotalCount) return null;
      const pageSize = Math.max(Number(this.pageSize) || 20, 1);
      return Math.max(Math.ceil(this.totalCount / pageSize), 1);
    },
  },
};
</script>

<style scoped>
.app-pagination {
  display: grid;
  justify-items: center;
  gap: 8px;
  margin-top: 14px;
  color: #64748b;
  font-size: 0.82rem;
}

.pagination-status,
.pagination-error {
  margin: 0;
}

.pagination-error {
  color: #b91c1c;
  text-align: center;
}

.pagination-error button {
  min-height: 44px;
  margin-left: 6px;
  padding: 0 10px;
}

.pagination-actions {
  display: flex;
  gap: 8px;
}

.pagination-actions button {
  min-width: 88px;
  min-height: 44px;
  padding: 0 16px;
  color: #0f766e;
  background: #ccfbf1;
  border: 0;
  border-radius: 8px;
  box-shadow: none;
  font-weight: 800;
}

.pagination-actions button:disabled,
.pagination-error button:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}
</style>
