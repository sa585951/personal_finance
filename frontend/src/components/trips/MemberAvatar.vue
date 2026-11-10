<template>
  <span
    class="member-avatar"
    :class="size"
    :style="{ background: failed || !member.avatar_url ? color : 'transparent' }"
    role="img"
    :aria-label="member.display_name"
  >
    <img
      v-if="member.avatar_url && !failed"
      :src="member.avatar_url"
      alt=""
      referrerpolicy="no-referrer"
      loading="lazy"
      @error="failed = true"
    />
    <template v-else>{{ initial }}</template>
  </span>
</template>

<script>
// Stable, distinct colours; white text on each keeps a contrast of at least 5.6:1.
const COLORS = ["#1F5A73", "#A84B26", "#3A6438", "#2D3C6B", "#9E3F63", "#7A5C2E", "#2F6B6A", "#52575E"];

export default {
  name: "MemberAvatar",
  props: {
    member: { type: Object, required: true },
    size: { type: String, default: "md" },
  },
  data() {
    return { failed: false };
  },
  computed: {
    initial() {
      // First visible character; Array.from keeps a surrogate pair together.
      return Array.from(String(this.member.display_name || "?").trim())[0]?.toUpperCase() || "?";
    },
    color() {
      let hash = 0;
      for (const char of String(this.member.id || this.member.display_name)) {
        hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
      }
      return COLORS[hash % COLORS.length];
    },
  },
  watch: {
    "member.avatar_url"() {
      this.failed = false;
    },
  },
};
</script>

<style scoped>
.member-avatar {
  display: inline-flex;
  flex: none;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 50%;
  /* Parent rules such as ".row span" must not turn the initial grey on a coloured disc. */
  color: #ffffff !important;
  font-weight: 700 !important;
  user-select: none;
}

.member-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.sm {
  width: 24px;
  height: 24px;
  font-size: 0.75rem;
}

.md {
  width: 36px;
  height: 36px;
  font-size: 0.95rem;
}

.lg {
  width: 48px;
  height: 48px;
  font-size: 1.15rem;
}
</style>
