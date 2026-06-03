<template>
  <main class="invite-page">
    <section class="invite-card">
      <p class="eyebrow">Trip Invite</p>
      <h1>加入旅行帳本</h1>
      <p class="invite-message">{{ message }}</p>

      <button
        v-if="tripId"
        class="primary-action"
        type="button"
        @click="$router.replace({ name: 'Trips', query: { trip_id: tripId } })"
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

export default {
  name: "TripInviteAccept",
  data() {
    return {
      message: "正在確認邀請連結...",
      tripId: "",
    };
  },
  async created() {
    await this.acceptInvite();
  },
  methods: {
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
        this.message = result.already_joined
          ? "你已經在這個旅行帳本中。"
          : "已成功加入旅行帳本。";
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
  color: #1f2933;
}

.invite-card {
  width: min(100%, 420px);
  padding: 22px;
  border: 1px solid #dbe4ee;
  border-radius: 8px;
  background: #ffffff;
}

.eyebrow {
  margin: 0 0 6px;
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
}

h1 {
  margin: 0;
  font-size: 1.7rem;
  letter-spacing: 0;
}

.invite-message {
  margin: 16px 0;
  color: #475569;
  line-height: 1.6;
}

.primary-action,
.secondary-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 42px;
  width: 100%;
  border-radius: 8px;
}

.primary-action {
  color: #ffffff;
  background: #0f766e;
}

.secondary-action {
  color: #0f766e;
  background: #ccfbf1;
}
</style>
