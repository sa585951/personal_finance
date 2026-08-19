<template>
  <section class="trip-management">
    <button class="management-toggle" type="button" @click="$emit('toggle')">
      {{ expanded ? "收合旅行管理" : "旅行管理" }}
    </button>
    <div v-if="expanded" class="management-panel">
      <div>
        <strong>帳本狀態</strong>
        <span>封存會保留資料；刪除會先保留 30 天。</span>
      </div>
      <div class="danger-row">
        <button class="quiet-action" type="button" @click="$emit('archive')">封存帳本</button>
        <button class="danger-action" type="button" @click="$emit('delete')">刪除帳本</button>
      </div>

      <div class="managed-trip-group">
        <div class="managed-trip-heading">
          <strong>已封存帳本</strong>
          <span>{{ archivedTrips.length }} 本</span>
        </div>
        <div v-if="archivedTrips.length === 0" class="managed-empty">尚無封存帳本</div>
        <div v-else class="managed-trip-list">
          <div v-for="trip in archivedTrips" :key="trip.id" class="managed-trip-row">
            <div>
              <strong>{{ trip.name }}</strong>
              <span>{{ trip.destination || "未設定地點" }} · {{ formatRange(trip) }}</span>
            </div>
            <button class="quiet-mini-button" type="button" @click="$emit('unarchive', trip)">
              解除封存
            </button>
          </div>
        </div>
      </div>

      <div class="managed-trip-group">
        <div class="managed-trip-heading">
          <strong>已刪除帳本</strong>
          <span>{{ deletedTrips.length }} 本</span>
        </div>
        <div v-if="deletedTrips.length === 0" class="managed-empty">尚無可復原帳本</div>
        <div v-else class="managed-trip-list">
          <div v-for="trip in deletedTrips" :key="trip.id" class="managed-trip-row deleted">
            <div>
              <strong>{{ trip.name }}</strong>
              <span>可復原至 {{ formatDateTime(trip.purge_after) || "30 天內" }}</span>
            </div>
            <button class="quiet-mini-button" type="button" @click="$emit('restore', trip)">復原</button>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script>
export default {
  name: "TripManagementPanel",
  props: {
    expanded: { type: Boolean, default: false },
    archivedTrips: { type: Array, default: () => [] },
    deletedTrips: { type: Array, default: () => [] },
  },
  emits: ["archive", "delete", "restore", "toggle", "unarchive"],
  methods: {
    formatRange(trip) {
      return `${trip.start_date || "未設定"} - ${trip.end_date || "未設定"}`;
    },
    formatDateTime(value) {
      if (!value) return "";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return value;
      return date.toLocaleString("zh-TW", { hour12: false });
    },
  },
};
</script>

<style scoped>
.trip-management {
  display: grid;
  gap: 10px;
  padding-top: 4px;
}

.management-toggle {
  min-height: 42px;
  color: #334155;
  background: #f8fafc;
  border: 1px solid #dbe4ee;
  border-radius: 8px;
  box-shadow: none;
  font-weight: 800;
}

.management-panel {
  display: grid;
  gap: 12px;
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #dbe4ee;
  border-radius: 8px;
}

.management-panel > div:first-child {
  display: grid;
  gap: 3px;
}

.management-panel span {
  color: #64748b;
  font-size: 0.88rem;
  font-weight: 700;
}

.danger-row,
.managed-trip-heading,
.managed-trip-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.danger-row {
  justify-content: flex-end;
  gap: 10px;
}

.quiet-action,
.danger-action,
.quiet-mini-button {
  min-height: 38px;
  padding: 0 12px;
  border: 0;
  border-radius: 8px;
  box-shadow: none;
  font-weight: 800;
}

.quiet-action {
  color: #334155;
  background: #e2e8f0;
}

.danger-action {
  color: #ffffff;
  background: #dc2626;
}

.quiet-mini-button {
  min-height: 32px;
  padding: 0 10px;
  color: #475569;
  background: #e2e8f0;
  font-size: 0.86rem;
}

.managed-trip-group {
  display: grid;
  gap: 8px;
  padding-top: 10px;
  border-top: 1px solid #e2e8f0;
}

.managed-trip-heading span,
.managed-trip-row > div span {
  color: #64748b;
  font-size: 0.82rem;
}

.managed-empty {
  padding: 10px 12px;
  color: #64748b;
  background: #ffffff;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  font-weight: 700;
}

.managed-trip-list {
  display: grid;
  gap: 8px;
}

.managed-trip-row {
  min-height: 58px;
  padding: 10px 12px;
  background: #ffffff;
  border: 1px solid #dbe4ee;
  border-radius: 8px;
}

.managed-trip-row.deleted {
  background: #fff7ed;
  border-color: #fed7aa;
}

.managed-trip-row > div {
  display: grid;
  gap: 2px;
  min-width: 0;
}

@media (max-width: 820px) {
  .danger-row {
    justify-content: stretch;
  }

  .danger-row button {
    flex: 1;
  }

  .managed-trip-row {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
