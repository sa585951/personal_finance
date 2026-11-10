<template>
  <section class="trip-members-panel">
    <div class="section-title">
      <User />
      <h3>旅伴</h3>
    </div>

    <div class="member-list">
      <div v-for="member in members" :key="member.id" class="member-row">
        <MemberAvatar :member="member" />
        <div>
          <span>{{ member.display_name }}</span>
          <small>
            {{ translateRole(member.role) }}
            <template v-if="member.id === currentMemberId"> · 你</template>
            <template v-else-if="!member.user_id"> · 未綁定帳號</template>
          </small>
        </div>
        <button
          v-if="isOwner || member.id === currentMemberId"
          class="member-edit"
          type="button"
          :aria-label="`修改 ${member.display_name} 的名稱`"
          @click="$emit('rename-member', member)"
        >
          <Edit />
        </button>
        <button
          v-if="isOwner && member.role !== 'owner' && member.user_id"
          class="quiet-mini-button"
          type="button"
          @click="$emit('release-member', member)"
        >
          釋放
        </button>
        <select
          v-if="isOwner && member.role !== 'owner'"
          class="member-role-select"
          :value="member.role"
          @change="$emit('update-role', member, $event.target.value)"
        >
          <option value="editor">編輯</option>
          <option value="viewer">檢視</option>
        </select>
        <button
          v-if="isOwner && member.role !== 'owner'"
          class="member-delete"
          type="button"
          aria-label="刪除旅伴"
          @click="$emit('delete-member', member)"
        >
          <Delete />
        </button>
      </div>
    </div>

    <section v-if="isOwner" class="invite-panel">
      <div>
        <strong>邀請連結</strong>
        <span>30 天內可重複使用，最多 15 位成員，加入後預設為編輯。</span>
      </div>
      <div v-if="activeInvite" class="invite-status-row">
        <span>連結已開啟至 {{ formatDateTime(activeInvite.expires_at) }}</span>
        <button class="quiet-mini-button" type="button" @click="$emit('close-invite')">關閉</button>
      </div>
      <div v-if="latestInviteUrl" class="invite-copy-row">
        <input :value="latestInviteUrl" readonly />
        <button class="secondary-action" type="button" @click="$emit('copy-invite')">複製</button>
      </div>
      <div v-if="latestInviteUrl" class="invite-share">
        <img v-if="qrSrc" class="invite-qr" :src="qrSrc" alt="邀請連結 QR Code" width="148" height="148" />
        <a class="secondary-action line-share" :href="lineShareUrl" target="_blank" rel="noopener noreferrer">
          用 LINE 分享
        </a>
      </div>
      <button
        v-if="!activeInvite"
        class="secondary-action"
        type="button"
        :disabled="submittingInvite"
        @click="$emit('create-invite')"
      >
        建立邀請連結
      </button>
      <p v-if="inviteMessage" class="status-message">{{ inviteMessage }}</p>
    </section>

    <form v-if="isOwner" class="member-form" @submit.prevent="$emit('add-member')">
      <input
        :value="newMember.display_name"
        type="text"
        required
        placeholder="朋友 A"
        @input="$emit('update-new-member', { display_name: $event.target.value.trimStart() })"
      />
      <select
        :value="newMember.role"
        @change="$emit('update-new-member', { role: $event.target.value })"
      >
        <option value="viewer">檢視</option>
        <option value="editor">編輯</option>
      </select>
      <button class="secondary-action" type="submit" :disabled="submittingMember">
        <Plus />
        新增
      </button>
    </form>
    <button
      v-else-if="currentMember && currentMember.role !== 'owner'"
      class="danger-action leave-trip-button"
      type="button"
      @click="$emit('leave')"
    >
      退出此帳本
    </button>
    <p v-if="memberMessage" class="status-message">{{ memberMessage }}</p>
  </section>
</template>

<script>
import { Delete, Edit, Plus, User } from "@element-plus/icons-vue";
import MemberAvatar from "@/components/trips/MemberAvatar.vue";

export default {
  name: "TripMembersPanel",
  components: { Delete, Edit, MemberAvatar, Plus, User },
  props: {
    members: { type: Array, default: () => [] },
    currentMemberId: { type: String, default: "" },
    isOwner: { type: Boolean, default: false },
    currentMember: { type: Object, default: null },
    activeInvite: { type: Object, default: null },
    latestInviteUrl: { type: String, default: "" },
    submittingInvite: { type: Boolean, default: false },
    submittingMember: { type: Boolean, default: false },
    inviteMessage: { type: String, default: "" },
    memberMessage: { type: String, default: "" },
    newMember: {
      type: Object,
      default: () => ({ display_name: "", role: "viewer" }),
    },
  },
  emits: [
    "add-member",
    "close-invite",
    "copy-invite",
    "create-invite",
    "delete-member",
    "leave",
    "release-member",
    "rename-member",
    "update-new-member",
    "update-role",
  ],
  data() {
    return { qrSrc: "" };
  },
  computed: {
    lineShareUrl() {
      return `https://line.me/R/share?text=${encodeURIComponent(`一起記旅行帳：${this.latestInviteUrl}`)}`;
    },
  },
  watch: {
    latestInviteUrl: {
      immediate: true,
      async handler(url) {
        this.qrSrc = "";
        if (!url) return;
        try {
          const { toDataURL } = await import("qrcode");
          const dataUrl = await toDataURL(url, { margin: 1, width: 296, errorCorrectionLevel: "M" });
          if (url === this.latestInviteUrl) this.qrSrc = dataUrl;
        } catch (error) {
          this.qrSrc = "";
        }
      },
    },
  },
  methods: {
    translateRole(role) {
      const roleMap = {
        owner: "擁有者",
        editor: "編輯",
        viewer: "檢視",
      };
      return roleMap[role] || role;
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
.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  color: var(--text-color);
}

.section-title h3 {
  margin: 0;
  letter-spacing: 0;
}

.section-title svg,
.secondary-action svg {
  width: 18px;
  height: 18px;
}

.member-list {
  display: grid;
  gap: 8px;
  margin-bottom: 12px;
}

.member-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 44px;
  padding: 10px 12px;
  background: var(--secondary-color);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.member-row > div {
  display: grid;
  flex: 1 1 auto;
  gap: 2px;
  min-width: 0;
}

.member-row span {
  color: var(--text-color);
  font-weight: 800;
}

.member-row small {
  color: var(--light-text-color);
  font-size: 0.78rem;
  font-weight: 700;
}

.member-delete {
  flex: 0 0 34px;
  width: 34px;
  min-height: 34px;
  padding: 0;
  color: var(--expense-color);
  background: var(--expense-soft);
  border: 0;
  border-radius: 8px;
  box-shadow: none;
}

.member-delete svg {
  width: 16px;
  height: 16px;
}

.member-role-select {
  flex: 0 0 96px;
  min-height: 34px;
  padding: 0 8px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  font-size: 0.85rem;
}

.invite-panel {
  display: grid;
  gap: 10px;
  margin: 0 0 12px;
  padding: 12px;
  background: var(--primary-soft);
  border: 1px solid var(--brand-border);
  border-radius: 8px;
}

.invite-panel > div:first-child {
  display: grid;
  gap: 3px;
}

.invite-panel strong {
  color: var(--primary-hover);
}

.invite-panel span {
  color: var(--light-text-color);
  font-size: 0.86rem;
  line-height: 1.45;
}

.invite-share {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.invite-qr {
  border-radius: 8px;
  background: #ffffff;
}

.line-share {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
}

.invite-status-row,
.invite-copy-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.invite-status-row {
  justify-content: space-between;
}

.invite-copy-row input {
  flex: 1;
  min-width: 0;
}

input,
select {
  box-sizing: border-box;
  width: 100%;
  max-width: 100%;
  min-height: 42px;
  min-width: 0;
  padding: 8px 10px;
  color: var(--text-color);
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  font-size: 1rem;
}

.member-form {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 120px auto;
  gap: 12px;
}

.secondary-action,
.danger-action,
.quiet-mini-button {
  white-space: nowrap;
  min-height: 38px;
  padding: 0 12px;
  color: #ffffff;
  border: 0;
  border-radius: 8px;
  box-shadow: none;
  font-weight: 800;
}

.secondary-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  background: var(--primary-color);
  color: var(--on-primary);
}

.danger-action {
  background: var(--expense-color);
}

.quiet-mini-button {
  min-height: 32px;
  padding: 0 10px;
  color: var(--light-text-color);
  background: var(--border-color);
  font-size: 0.86rem;
}

.leave-trip-button {
  width: 100%;
}

.status-message {
  margin: 12px 0 0;
  color: var(--light-text-color);
}

@media (max-width: 820px) {
  .member-form {
    grid-template-columns: minmax(0, 1fr) 108px;
  }

  .member-form .secondary-action {
    grid-column: 1 / -1;
  }

  .member-row {
    flex-wrap: nowrap;
    gap: 8px;
  }

  .member-role-select {
    flex: 0 0 32%;
    max-width: 128px;
    min-width: 92px;
  }

  .invite-status-row,
  .invite-copy-row {
    align-items: stretch;
    flex-direction: column;
  }

  .invite-copy-row .secondary-action {
    width: 100%;
  }
}
.member-edit {
  display: grid;
  place-items: center;
  width: 36px;
  min-height: 36px;
  padding: 0;
  color: var(--light-text-color);
  background: transparent;
  border: 0;
}

.member-edit svg {
  width: 16px;
  height: 16px;
}
</style>
