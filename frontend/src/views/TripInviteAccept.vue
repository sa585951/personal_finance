<template>
  <main class="invite-page">
    <section class="invite-card">
      <div v-if="preview" class="invite-cover" :style="{ background: cover.color }">
        <small>{{ preview.inviter_name }} 邀請你加入</small>
        <strong>{{ preview.trip_name }}</strong>
      </div>
      <h1>{{ heading }}</h1>
      <p class="invite-message">{{ message }}</p>

      <button v-if="state === 'login'" class="primary-action app-primary-action" type="button" @click="login">
        用 LINE 登入並加入
      </button>

      <template v-else-if="state === 'pick'">
        <p v-if="suggested" class="suggest">你是「{{ suggested.display_name }}」嗎？</p>
        <ul class="pick-list">
          <li v-for="member in orderedCandidates" :key="member.id">
            <button
              class="pick-item"
              :class="{ suggested: suggested && suggested.id === member.id }"
              type="button"
              :disabled="busy"
              @click="join(member.id)"
            >
              <MemberAvatar :member="member" />
              <span>{{ member.display_name }}</span>
            </button>
          </li>
        </ul>
        <button class="secondary-action" type="button" :disabled="busy" @click="join('')">
          我是新的旅伴（以「{{ myName }}」加入）
        </button>
      </template>

      <button v-else-if="tripId" class="primary-action app-primary-action" type="button" @click="openTrip">
        前往帳本
      </button>
      <button v-else-if="state === 'error'" class="secondary-action" type="button" @click="$router.replace({ name: 'Trips' })">
        回到旅行帳本
      </button>
    </section>
  </main>
</template>

<script>
import apiClient from "@/api";
import MemberAvatar from "@/components/trips/MemberAvatar.vue";
import { tripCover } from "@/constants/tripCovers";

const nameKey = (value) => String(value || "").normalize("NFKC").trim().toLowerCase();

export default {
  name: "TripInviteAccept",
  components: { MemberAvatar },
  data() {
    return {
      state: "loading", // loading | login | pick | done | error
      message: "正在確認邀請連結...",
      preview: null,
      candidates: [],
      myName: "",
      tripId: "",
      busy: false,
      redirectTimer: null,
    };
  },
  computed: {
    cover() {
      return tripCover({ cover_theme: this.preview?.cover_theme, id: this.preview?.trip_name });
    },
    heading() {
      return this.state === "pick" ? "你是哪一位？" : "加入旅行帳本";
    },
    suggested() {
      return this.candidates.find((member) => nameKey(member.display_name) === nameKey(this.myName)) || null;
    },
    orderedCandidates() {
      const hit = this.suggested;
      return hit ? [hit, ...this.candidates.filter((member) => member.id !== hit.id)] : this.candidates;
    },
  },
  async created() {
    await this.load();
  },
  beforeUnmount() {
    if (this.redirectTimer) window.clearTimeout(this.redirectTimer);
  },
  methods: {
    openTrip() {
      if (this.redirectTimer) window.clearTimeout(this.redirectTimer);
      this.$router.replace({ name: "TripDetail", params: { tripId: this.tripId } });
    },
    login() {
      this.$router.push({ name: "Login", query: { redirect: this.$route.fullPath } });
    },
    fail(error, fallback) {
      this.state = "error";
      this.message = error?.response?.data?.message || fallback;
    },
    async load() {
      const token = this.$route.params.token;
      if (!token) {
        this.fail(null, "邀請連結不完整，請重新確認。");
        return;
      }
      try {
        const response = await apiClient.get(`/api/trip-invites/${token}/preview`);
        this.preview = response.data.data;
      } catch (error) {
        this.fail(error, "邀請連結無法使用，可能已過期或已關閉。");
        return;
      }

      let listing;
      try {
        const response = await apiClient.get(`/api/trip-invites/${token}/candidates`);
        listing = response.data.data;
      } catch (error) {
        if (error.response?.status === 401) {
          this.state = "login";
          this.message = "登入後就能看到這趟旅行的分帳。";
          return;
        }
        this.fail(error, "邀請連結無法使用，可能已過期或已關閉。");
        return;
      }

      this.myName = listing.my_name;
      this.candidates = listing.candidates || [];
      this.tripId = listing.trip_id;
      if (listing.already_joined) {
        this.finish("你已經在這個旅行帳本中，正在前往帳本...");
      } else if (this.candidates.length) {
        this.state = "pick";
        this.message = "旅伴可能已經先被加進帳本了。選擇你自己，之前的記錄就會接到你的帳號。";
      } else {
        await this.join("");
      }
    },
    finish(message) {
      this.state = "done";
      this.message = message;
      this.redirectTimer = window.setTimeout(() => this.openTrip(), 1200);
    },
    async join(claimMemberId) {
      if (this.busy) return;
      this.busy = true;
      try {
        const body = claimMemberId ? { claim_member_id: claimMemberId } : {};
        const response = await apiClient.post(`/api/trip-invites/${this.$route.params.token}/accept`, body);
        const result = response.data.data || {};
        this.tripId = result.trip?.id || this.tripId;
        this.finish(result.already_joined ? "你已經在這個旅行帳本中，正在前往帳本..." : "已成功加入旅行帳本，正在前往帳本...");
      } catch (error) {
        this.busy = false;
        if (this.state === "pick") {
          this.message = error.response?.data?.message || "加入失敗，請稍後再試。";
          await this.refreshCandidates();
        } else {
          this.fail(error, "邀請連結無法使用，可能已過期或已關閉。");
        }
      }
    },
    async refreshCandidates() {
      try {
        const response = await apiClient.get(`/api/trip-invites/${this.$route.params.token}/candidates`);
        this.candidates = response.data.data.candidates || [];
      } catch (error) {
        // keep the list on screen; the message above already explains
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

.suggest {
  margin: 0 0 8px;
  font-weight: 700;
}

.pick-list {
  display: grid;
  gap: 8px;
  margin: 0 0 12px;
  padding: 0;
  list-style: none;
}

.pick-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  min-height: 48px;
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  color: var(--text-color);
  background: var(--card-bg);
  font-weight: 600;
  text-align: left;
}

.pick-item.suggested {
  border-color: var(--primary-color);
}
</style>
