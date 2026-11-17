<template>
  <section v-if="!allDone" class="checklist" aria-labelledby="checklist-title">
    <div class="checklist-head">
      <h2 id="checklist-title">{{ title }}</h2>
      <button v-if="hasAccounts" type="button" class="dismiss" @click="dismiss">不再顯示</button>
    </div>

    <ol class="steps">
      <li class="step" :class="{ done: hasAccounts }">
        <span class="mark" aria-hidden="true">{{ hasAccounts ? "✓" : "1" }}</span>
        <div class="step-body">
          <strong>建立現金帳戶</strong>
          <small v-if="!hasAccounts">記帳時餘額會跟著變動，之後可以改名或再新增銀行、信用卡。</small>
          <div v-if="!hasAccounts" class="step-actions">
            <button type="button" class="ink-button" :disabled="creating" @click="createCash">
              {{ creating ? "建立中" : "一鍵建立現金帳戶" }}
            </button>
            <router-link to="/assets" class="text-link">改成自己建立</router-link>
          </div>
          <small v-if="errorMessage" class="error" role="alert">{{ errorMessage }}</small>
        </div>
      </li>

      <li class="step" :class="{ done: hasRecords }">
        <span class="mark" aria-hidden="true">{{ hasRecords ? "✓" : "2" }}</span>
        <div class="step-body">
          <strong>記下第一筆</strong>
          <small v-if="!hasRecords">用一句話就好，例如「午餐 120」，確認後才會記帳。</small>
          <div v-if="hasAccounts && !hasRecords" class="step-actions">
            <router-link to="/add" class="ink-button" @click="$emit('track', 'onboarding_record')">記一筆</router-link>
          </div>
        </div>
      </li>

      <li class="step" :class="{ done: lineDone }">
        <span class="mark" aria-hidden="true">{{ lineDone ? "✓" : "3" }}</span>
        <div class="step-body">
          <strong>加 LINE 好友</strong>
          <small v-if="!lineDone">加好友後，在對話框傳「午餐 120」就能記帳，不用開網頁。</small>
          <div v-if="!lineDone" class="step-actions">
            <a :href="lineUrl" class="ink-button" target="_blank" rel="noopener" @click="$emit('track', 'onboarding_line')">加好友</a>
            <button type="button" class="text-link" @click="markLine">我已經加了</button>
          </div>
        </div>
      </li>

      <li v-if="showHomeScreenTip" class="step" :class="{ done: homeScreenDone }">
        <span class="mark" aria-hidden="true">{{ homeScreenDone ? "✓" : "4" }}</span>
        <div class="step-body">
          <strong>加到主畫面</strong>
          <small v-if="inLineBrowser">
            你現在是在 LINE 裡開啟，請先點右下角的選單，選「用 Safari 開啟」，再加到主畫面。
          </small>
          <small v-else>在 Safari 點下方的「分享」，選「加入主畫面」，之後一點就能開。</small>
          <div v-if="!homeScreenDone" class="step-actions">
            <button type="button" class="text-link" @click="markHomeScreen">知道了</button>
          </div>
        </div>
      </li>
    </ol>
  </section>
</template>

<script>
import apiClient from "@/api";
import { LINE_ADD_FRIEND_URL } from "@/constants/links";

const LINE_KEY = "nomica.onboarding.line";
const HOME_KEY = "nomica.onboarding.homescreen";
export const DISMISS_KEY = "nomica.onboarding.dismissed";

function read(key) {
  try {
    return window.localStorage.getItem(key) === "1";
  } catch {
    return false; // Storage can be blocked; the checklist still works for this visit.
  }
}

function write(key) {
  try {
    window.localStorage.setItem(key, "1");
  } catch {
    // Ignore: the step simply shows again next time.
  }
}

export function isIosBrowser(nav = window.navigator) {
  const ua = nav.userAgent || "";
  return /iPhone|iPad|iPod/.test(ua) || (/Macintosh/.test(ua) && nav.maxTouchPoints > 1);
}

export function isStandalone(nav = window.navigator, win = window) {
  return nav.standalone === true || Boolean(win.matchMedia?.("(display-mode: standalone)").matches);
}

export default {
  name: "OnboardingChecklist",
  props: {
    hasAccounts: { type: Boolean, required: true },
    hasRecords: { type: Boolean, required: true },
  },
  emits: ["created", "track", "dismissed"],
  data() {
    return {
      creating: false,
      errorMessage: "",
      lineDone: read(LINE_KEY),
      homeScreenDone: read(HOME_KEY),
      lineUrl: LINE_ADD_FRIEND_URL,
      showHomeScreenTip: isIosBrowser() && !isStandalone(),
      inLineBrowser: /Line\//i.test(window.navigator.userAgent || ""),
    };
  },
  computed: {
    allDone() {
      return this.hasAccounts && this.hasRecords && this.lineDone && (!this.showHomeScreenTip || this.homeScreenDone);
    },
    title() {
      return this.hasAccounts ? "開始使用 Nomica" : "先建立一個帳戶";
    },
  },
  methods: {
    async createCash() {
      if (this.creating) return;
      this.creating = true;
      this.errorMessage = "";
      try {
        await apiClient.post("/api/onboarding/cash-account");
        this.$emit("track", "onboarding_cash");
        this.$emit("created");
      } catch (error) {
        this.errorMessage = error.response?.data?.message || "建立失敗，請稍後再試，或改成自己建立。";
      } finally {
        this.creating = false;
      }
    },
    markLine() {
      write(LINE_KEY);
      this.lineDone = true;
    },
    markHomeScreen() {
      write(HOME_KEY);
      this.homeScreenDone = true;
    },
    dismiss() {
      write(DISMISS_KEY);
      this.$emit("dismissed");
    },
  },
};
</script>

<style scoped>
.checklist {
  display: grid;
  gap: 12px;
  margin-bottom: 20px;
  padding: 16px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 12px;
}

.checklist-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

h2 {
  margin: 0;
  font-size: 1.15rem;
}

.dismiss,
.text-link {
  min-height: 40px;
  padding: 0 4px;
  border: 0;
  color: var(--light-text-color);
  background: transparent;
  box-shadow: none;
  font-size: 0.85rem;
  text-decoration: underline;
}

.steps {
  display: grid;
  gap: 14px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.step {
  display: grid;
  grid-template-columns: 28px 1fr;
  gap: 12px;
}

.mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 1px solid var(--border-color);
  border-radius: 50%;
  color: var(--light-text-color);
  font-size: 0.85rem;
  font-weight: 700;
}

.step.done .mark {
  color: var(--on-primary);
  background: var(--primary-color);
  border-color: var(--primary-color);
}

.step.done strong {
  color: var(--light-text-color);
}

.step-body {
  display: grid;
  gap: 4px;
  min-width: 0;
}

small {
  color: var(--light-text-color);
  font-size: 0.84rem;
  line-height: 1.5;
}

.error {
  color: var(--danger-color, #b3261e);
}

.step-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 14px;
  margin-top: 6px;
}

.ink-button {
  display: inline-flex;
  align-items: center;
  min-height: 44px;
  padding: 0 18px;
  border: 0;
  border-radius: 10px;
  color: var(--on-primary);
  background: var(--primary-color);
  text-decoration: none;
  font-weight: 700;
}

.ink-button:disabled {
  opacity: 0.6;
}
</style>
