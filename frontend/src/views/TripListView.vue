<template>
  <div class="trip-list-view">
    <header class="page-header">
      <div>
        <p class="eyebrow">Nomica Travel</p>
        <h1>旅行帳本</h1>
      </div>
      <div class="header-actions">
        <button class="icon-button" type="button" title="重新整理" @click="fetchTrips">
          <Refresh />
        </button>
        <button class="primary-action" type="button" @click="showCreateTrip = !showCreateTrip">
          <Plus />
          {{ showCreateTrip ? "收合" : "新增" }}
        </button>
      </div>
    </header>

    <section v-if="showCreateTrip || (!loading && trips.length === 0)" class="create-panel">
      <div class="section-heading">
        <div>
          <span>NEW TRIP</span>
          <h2>新增旅行</h2>
        </div>
        <p>建立後再到旅行詳情記錄支出、分帳與邀請旅伴。</p>
      </div>
      <form class="trip-form" @submit.prevent="createTrip">
        <label>
          名稱
          <input v-model.trim="newTrip.name" type="text" required placeholder="日本 2027" />
        </label>
        <label>
          地點
          <input v-model.trim="newTrip.destination" type="text" placeholder="Tokyo" />
        </label>
        <label>
          開始
          <input v-model="newTrip.start_date" type="date" required />
        </label>
        <label>
          結束
          <input v-model="newTrip.end_date" type="date" required />
        </label>
        <label>
          本幣
          <select v-model="newTrip.base_currency">
            <option v-for="currency in currencies" :key="currency" :value="currency">
              {{ currency }}
            </option>
          </select>
        </label>
        <label>
          當地幣別
          <select v-model="newTrip.default_currency">
            <option v-for="currency in currencies" :key="currency" :value="currency">
              {{ currency }}
            </option>
          </select>
        </label>
        <label class="toggle-row full-row">
          <input v-model="newTrip.include_in_monthly_report" type="checkbox" />
          納入我的月報
        </label>
        <p class="field-hint full-row">
          只會將你的旅行分攤金額納入個人統計，其他成員可自行決定。
        </p>
        <button class="primary-action full-row" type="submit" :disabled="submittingTrip">
          <Plus />
          {{ submittingTrip ? "建立中" : "建立旅行" }}
        </button>
      </form>
      <p v-if="tripMessage" class="status-message">{{ tripMessage }}</p>
    </section>

    <div v-if="loading" class="page-state">載入中...</div>
    <div v-else-if="loadError" class="page-state error">
      <strong>無法載入旅行帳本</strong>
      <span>{{ loadError }}</span>
      <button class="secondary-action" type="button" @click="fetchTrips">重新整理</button>
    </div>
    <section v-else class="list-section" aria-label="旅行帳本列表">
      <div class="list-heading">
        <div>
          <span>全部旅行</span>
          <strong>{{ trips.length }} 本帳本</strong>
        </div>
        <button class="quiet-action" type="button" @click="toggleTripManagement">
          {{ showTripManagement ? "收合管理" : "管理帳本" }}
        </button>
      </div>

      <div v-if="trips.length === 0" class="empty-state">
        <strong>尚未建立旅行帳本</strong>
        <span>建立第一趟旅行後，就能集中記錄外幣支出與旅伴分帳。</span>
      </div>
      <div v-else class="trip-groups">
        <section v-for="group in visibleTripGroups" :key="group.key" class="trip-group">
          <div class="trip-group-heading">
            <div>
              <span>{{ group.eyebrow }}</span>
              <strong>{{ group.label }}</strong>
            </div>
            <span>{{ group.trips.length }} 趟</span>
          </div>
          <div class="trip-grid">
            <button
              v-for="trip in group.trips"
              :key="trip.id"
              class="trip-card"
              type="button"
              @click="openTrip(trip.id)"
            >
              <div class="card-topline">
                <span class="report-badge" :class="tripReportPreferenceClass(trip)">
                  {{ tripReportLabel(trip) }}
                </span>
                <span>{{ tripDays(trip) }} 天</span>
              </div>
              <strong>{{ trip.name }}</strong>
              <span>{{ trip.destination || "未設定地點" }}</span>
              <small>{{ formatRange(trip) }}</small>
              <div class="card-meta">
                <span>{{ trip.members?.length || 0 }} 人</span>
                <span>{{ trip.default_currency }} / {{ trip.base_currency }}</span>
              </div>
            </button>
          </div>
        </section>
      </div>
    </section>

    <section v-if="showTripManagement" class="management-panel">
      <div class="section-heading">
        <div>
          <span>ARCHIVE</span>
          <h2>旅行管理</h2>
        </div>
        <p>封存資料會保留；軟刪除帳本可在 30 天內復原。</p>
      </div>
      <div class="managed-group">
        <div class="managed-heading">
          <strong>已封存帳本</strong>
          <span>{{ archivedManagedTrips.length }} 本</span>
        </div>
        <p v-if="archivedManagedTrips.length === 0" class="managed-empty">尚無封存帳本</p>
        <div v-else class="managed-list">
          <div v-for="trip in archivedManagedTrips" :key="trip.id" class="managed-row">
            <div>
              <strong>{{ trip.name }}</strong>
              <span>{{ trip.destination || "未設定地點" }} · {{ formatRange(trip) }}</span>
            </div>
            <button class="quiet-action" type="button" @click="unarchiveTrip(trip)">解除封存</button>
          </div>
        </div>
      </div>
      <div class="managed-group">
        <div class="managed-heading">
          <strong>已刪除帳本</strong>
          <span>{{ deletedManagedTrips.length }} 本</span>
        </div>
        <p v-if="deletedManagedTrips.length === 0" class="managed-empty">尚無可復原帳本</p>
        <div v-else class="managed-list">
          <div v-for="trip in deletedManagedTrips" :key="trip.id" class="managed-row deleted">
            <div>
              <strong>{{ trip.name }}</strong>
              <span>可復原至 {{ formatDateTime(trip.purge_after) || "30 天內" }}</span>
            </div>
            <button class="quiet-action" type="button" @click="restoreTrip(trip)">復原</button>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script>
import { Plus, Refresh } from "@element-plus/icons-vue";
import apiClient from "@/api";

export default {
  name: "TripListView",
  components: { Plus, Refresh },
  data() {
    const today = new Date().toISOString().slice(0, 10);
    return {
      currencies: ["TWD", "JPY", "KRW", "USD", "EUR"],
      trips: [],
      managedTrips: [],
      loading: true,
      loadError: "",
      showCreateTrip: false,
      showTripManagement: false,
      submittingTrip: false,
      tripMessage: "",
      newTrip: {
        name: "",
        destination: "",
        start_date: today,
        end_date: today,
        timezone: "Asia/Taipei",
        base_currency: "TWD",
        default_currency: "JPY",
        include_in_monthly_report: false,
      },
    };
  },
  computed: {
    visibleTripGroups() {
      const today = new Date().toISOString().slice(0, 10);
      const ongoing = this.trips
        .filter((trip) => trip.start_date <= today && trip.end_date >= today)
        .sort((left, right) => right.start_date.localeCompare(left.start_date));
      const upcoming = this.trips
        .filter((trip) => trip.start_date > today)
        .sort((left, right) => left.start_date.localeCompare(right.start_date));
      const past = this.trips
        .filter((trip) => trip.end_date < today)
        .sort((left, right) => right.end_date.localeCompare(left.end_date));

      return [
        { key: "ongoing", eyebrow: "ONGOING", label: "進行中", trips: ongoing },
        { key: "upcoming", eyebrow: "UPCOMING", label: "即將出發", trips: upcoming },
        { key: "past", eyebrow: "PAST", label: "過往旅行", trips: past },
      ].filter((group) => group.trips.length > 0);
    },
    archivedManagedTrips() {
      return this.managedTrips.filter((trip) => !trip.deleted_at && trip.status === "archived");
    },
    deletedManagedTrips() {
      return this.managedTrips.filter((trip) => trip.deleted_at);
    },
  },
  methods: {
    async fetchTrips() {
      this.loading = true;
      this.loadError = "";
      try {
        const response = await apiClient.get("/api/trips");
        this.trips = response.data.data || [];
      } catch (error) {
        this.trips = [];
        this.loadError = error.response?.data?.message || "旅行資料載入失敗，請稍後再試。";
      } finally {
        this.loading = false;
      }
    },
    async fetchManagedTrips() {
      try {
        const response = await apiClient.get("/api/trips?include_archived=true&include_deleted=true");
        this.managedTrips = response.data.data || [];
      } catch (error) {
        this.$swal.fire("載入失敗", error.response?.data?.message || "旅行管理資料載入失敗", "error");
      }
    },
    async toggleTripManagement() {
      this.showTripManagement = !this.showTripManagement;
      if (this.showTripManagement) await this.fetchManagedTrips();
    },
    openTrip(tripId) {
      this.$router.push({ name: "TripDetail", params: { tripId } });
    },
    async createTrip() {
      if (this.submittingTrip) return;
      this.submittingTrip = true;
      this.tripMessage = "";
      try {
        const response = await apiClient.post("/api/trips", this.newTrip);
        const createdTrip = response.data.data;
        await this.$router.push({ name: "TripDetail", params: { tripId: createdTrip.id } });
      } catch (error) {
        this.tripMessage = error.response?.data?.message || "旅行建立失敗";
      } finally {
        this.submittingTrip = false;
      }
    },
    async unarchiveTrip(trip) {
      const result = await this.$swal.fire({
        title: "解除封存？",
        text: `${trip.name} 會回到旅行帳本列表。`,
        icon: "question",
        showCancelButton: true,
        confirmButtonText: "解除封存",
        cancelButtonText: "取消",
      });
      if (!result.isConfirmed) return;
      try {
        await apiClient.post(`/api/trips/${trip.id}/unarchive`);
        await Promise.all([this.fetchTrips(), this.fetchManagedTrips()]);
      } catch (error) {
        this.$swal.fire("解除封存失敗", error.response?.data?.message || "請稍後再試", "error");
      }
    },
    async restoreTrip(trip) {
      const result = await this.$swal.fire({
        title: "復原旅行帳本？",
        text: `${trip.name} 會回到原本狀態。`,
        icon: "question",
        showCancelButton: true,
        confirmButtonText: "復原",
        cancelButtonText: "取消",
      });
      if (!result.isConfirmed) return;
      try {
        await apiClient.post(`/api/trips/${trip.id}/restore`);
        await Promise.all([this.fetchTrips(), this.fetchManagedTrips()]);
      } catch (error) {
        this.$swal.fire("復原失敗", error.response?.data?.message || "請稍後再試", "error");
      }
    },
    tripCurrentMember(trip) {
      return (trip.members || []).find((member) => member.id === trip.current_member_id) || null;
    },
    tripReportPreference(trip) {
      return this.tripCurrentMember(trip)?.monthly_report_preference || null;
    },
    tripReportPreferenceClass(trip) {
      const preference = this.tripReportPreference(trip);
      return {
        include: preference === "include",
        exclude: preference === "exclude",
        pending: preference === "pending",
      };
    },
    tripReportLabel(trip) {
      const preference = this.tripReportPreference(trip);
      if (preference === "include") return "計入我的月報";
      if (preference === "exclude") return "不計入我的月報";
      if (preference === "pending") return "尚未決定";
      return trip.include_in_monthly_report ? "計入月報" : "不計入月報";
    },
    tripDays(trip) {
      const start = new Date(`${trip.start_date}T00:00:00`);
      const end = new Date(`${trip.end_date}T00:00:00`);
      return Math.max(1, Math.round((end - start) / 86400000) + 1);
    },
    formatRange(trip) {
      return `${trip.start_date} - ${trip.end_date}`;
    },
    formatDateTime(value) {
      if (!value) return "";
      return new Date(value).toLocaleString("zh-TW", { hour12: false });
    },
  },
  created() {
    this.fetchTrips();
  },
};
</script>

<style scoped>
.trip-list-view {
  max-width: 720px;
  min-height: calc(100vh - 80px);
  margin: 0 auto;
  padding: 24px 16px calc(var(--app-bottom-nav-height) + 22px);
  color: #1f2933;
}

.page-header,
.list-heading,
.section-heading,
.managed-heading,
.managed-row,
.header-actions,
.primary-action,
.secondary-action,
.quiet-action,
.icon-button,
.card-topline,
.card-meta,
.toggle-row {
  display: flex;
  align-items: center;
}

.page-header,
.list-heading,
.managed-heading,
.managed-row,
.card-topline,
.card-meta {
  justify-content: space-between;
}

.page-header {
  gap: 12px;
  margin-bottom: 16px;
}

.eyebrow,
.section-heading span,
.list-heading span {
  margin: 0 0 2px;
  color: #0f766e;
  font-size: 0.72rem;
  font-weight: 900;
  letter-spacing: 0;
  text-transform: uppercase;
}

h1,
h2,
p {
  margin: 0;
}

h1 {
  font-size: 1.8rem;
}

h2 {
  font-size: 1.05rem;
}

.header-actions,
.primary-action,
.secondary-action,
.quiet-action,
.toggle-row {
  gap: 6px;
}

.primary-action,
.secondary-action,
.quiet-action,
.icon-button {
  justify-content: center;
  min-height: 38px;
  padding: 0 12px;
  border-radius: 8px;
  font-weight: 800;
}

.primary-action {
  color: #ffffff;
  background: #0f766e;
  border: 1px solid #0f766e;
}

.secondary-action,
.quiet-action,
.icon-button {
  color: #334155;
  background: #ffffff;
  border: 1px solid #cbd5e1;
}

.icon-button {
  width: 38px;
  padding: 0;
}

.icon-button svg,
.primary-action svg {
  width: 16px;
}

.create-panel,
.management-panel,
.page-state,
.empty-state {
  padding: 16px;
  background: #ffffff;
  border: 1px solid #dbe4ee;
  border-radius: 8px;
}

.create-panel,
.management-panel,
.list-section {
  display: grid;
  gap: 14px;
  margin-top: 14px;
}

.section-heading {
  justify-content: space-between;
  gap: 16px;
}

.section-heading p {
  max-width: 360px;
  color: #64748b;
  font-size: 0.82rem;
  text-align: right;
}

.trip-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.trip-form label {
  display: grid;
  gap: 6px;
  min-width: 0;
  color: #475569;
  font-size: 0.82rem;
  font-weight: 800;
}

.trip-form input,
.trip-form select {
  width: 100%;
  min-width: 0;
  min-height: 42px;
  padding: 0 10px;
  color: #1f2933;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 7px;
}

.full-row {
  grid-column: 1 / -1;
}

.toggle-row {
  grid-template-columns: auto 1fr !important;
}

.toggle-row input {
  width: 18px;
  min-height: 18px;
}

.field-hint,
.status-message,
.page-state,
.empty-state,
.managed-empty {
  color: #64748b;
  font-size: 0.85rem;
}

.page-state,
.empty-state {
  display: grid;
  justify-items: start;
  gap: 8px;
  margin-top: 14px;
}

.page-state.error {
  border-left: 4px solid #d97706;
}

.list-heading {
  gap: 12px;
}

.list-heading > div {
  display: grid;
  gap: 2px;
}

.list-heading strong {
  font-size: 1rem;
}

.trip-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.trip-groups,
.trip-group {
  display: grid;
  gap: 12px;
}

.trip-group + .trip-group {
  padding-top: 14px;
  border-top: 1px solid #dbe4ee;
}

.trip-group-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 12px;
}

.trip-group-heading > div {
  display: grid;
  gap: 2px;
}

.trip-group-heading span {
  color: #64748b;
  font-size: 0.75rem;
  font-weight: 800;
}

.trip-group-heading > div > span {
  color: #0f766e;
}

.trip-card {
  display: grid;
  gap: 5px;
  min-width: 0;
  min-height: 154px;
  padding: 14px;
  color: #475569;
  text-align: left;
  background: #ffffff;
  border: 1px solid #dbe4ee;
  border-left: 4px solid #0f766e;
  border-radius: 8px;
  box-shadow: none;
}

.trip-card:hover {
  background: #f8fafc;
  border-color: #99c9c2;
}

.trip-card > strong,
.trip-card > span,
.trip-card > small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.trip-card > strong {
  color: #1f2933;
  font-size: 1.05rem;
}

.card-topline > span:last-child,
.card-meta {
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 700;
}

.card-meta {
  align-self: end;
  padding-top: 4px;
  border-top: 1px solid #eef2f6;
}

.report-badge {
  width: fit-content;
  padding: 3px 7px;
  color: #475569;
  background: #f1f5f9;
  border-radius: 6px;
  font-size: 0.72rem;
  font-weight: 800;
}

.report-badge.include {
  color: #0f766e;
  background: #ccfbf1;
}

.report-badge.pending {
  color: #9a3412;
  background: #ffedd5;
}

.managed-group,
.managed-list {
  display: grid;
  gap: 8px;
}

.managed-group + .managed-group {
  padding-top: 12px;
  border-top: 1px solid #eef2f6;
}

.managed-heading span,
.managed-row span {
  color: #64748b;
  font-size: 0.8rem;
}

.managed-row {
  gap: 12px;
  padding: 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 7px;
}

.managed-row > div {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.managed-row.deleted {
  border-left: 3px solid #d97706;
}

@media (max-width: 820px) {
  .trip-list-view {
    padding: 18px 12px calc(var(--app-bottom-nav-height) + 22px);
  }

  .trip-grid,
  .trip-form {
    grid-template-columns: 1fr;
  }

  .page-header,
  .section-heading {
    align-items: flex-start;
  }

  .section-heading {
    flex-direction: column;
    gap: 4px;
  }

  .section-heading p {
    max-width: none;
    text-align: left;
  }

  h1 {
    font-size: 1.6rem;
  }
}

@media (max-width: 430px) {
  .managed-row {
    align-items: stretch;
    flex-direction: column;
  }

  .managed-row .quiet-action {
    width: 100%;
  }
}
</style>
