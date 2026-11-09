<template>
  <main class="invite-page">
    <section class="invite-card">
      <div v-if="trip" class="invite-cover" :style="{ background: cover.color }">
        <small>{{ trip.destination || "旅行" }}</small>
        <strong>{{ trip.name }}</strong>
      </div>
      <h1>加入旅行帳本</h1>
      <p class="invite-message">{{ message }}</p>

      <button
        v-if="tripId"
        class="primary-action app-primary-action"
        type="button"
        @click="openTrip"
      >
        前往帳本
      </button>
      <button v-else class="secondary-action" type="button" @click="$router.replace({ name: 'Trips' })">
        回到旅行帳本
      </button>
    </section>
  </main>
</template>

<script>
import apiClient from "@/api";
import { tripCover } from "@/constants/tripCovers";

export default {
  name: "TripInviteAccept",
  data() {
    return {
      message: "正在確認邀請連結...",
      tripId: "",
      trip: null,
      redirectTimer: null,
    };
  },
  computed: {
    cover() {
      return tripCover(this.trip);
    },
  },
  async created() {
    await this.acceptInvite();
  },
  beforeUnmount() {
    if (this.redirectTimer) {
      window.clearTimeout(this.redirectTimer);
    }
  },
  methods: {
    openTrip() {
      if (this.redirectTimer) window.clearTimeout(this.redirectTimer);
      this.$router.replace({ name: "TripDetail", params: { tripId: this.tripId } });
    },
    async acceptInvite() {
      const token = this.$route.params.token;
      if (!token) {
        this.message = "邀請連結不完整，請重新確認。";
        return;
      }

      try {
        const response = await apiClient.post(`/api/trip-invites/${token}/accept`);
        const result = response.data.data || {};
        this.tripId = result.trip?.id || "";
        this.trip = result.trip || null;
        this.message = result.already_joined
          ? "你已經在這個旅行帳本中，正在前往帳本..."
          : "已成功加入旅行帳本，正在前往帳本...";
        if (this.tripId) {
          this.redirectTimer = window.setTimeout(() => this.openTrip(), 1500);
        }
      } catch (error) {
        this.message = error.response?.data?.message || "邀請連結無法使用，可能已過期或已關閉。";
      }
    },
  },
};
</script>

<style scoped>
.invite-page {
  display: grid;
  min-height: calc(100vh - 80px);
  place-items: center;
  padding: 24px 16px calc(var(--app-bottom-nav-height) + 22px);
  color: var(--text-color);
}

.invite-card {
  width: min(100%, 420px);
  padding: 22px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: var(--card-bg);
}

.eyebrow {
  margin: 0 0 6px;
  color: var(--light-text-color);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
}

.invite-cover {
  display: grid;
  gap: 2px;
  margin-bottom: 16px;
  padding: 36px 16px 16px;
  border-radius: 12px;
  color: #ffffff;
}

.invite-cover strong {
  font-size: 1.3rem;
}

h1 {
  margin: 0;
  font-size: 1.7rem;
  letter-spacing: 0;
}

.invite-message {
  margin: 16px 0;
  color: var(--light-text-color);
  line-height: 1.6;
}

.primary-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 42px;
  width: 100%;
}

.secondary-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 42px;
  width: 100%;
  border-radius: 8px;
}

.secondary-action {
  color: var(--primary-color);
  background: var(--primary-soft);
}
</style>
