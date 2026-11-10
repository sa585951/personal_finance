<template>
  <div class="universal-add-screen">
    <header class="add-header">
      <h1>記一筆</h1>
      <button type="button" class="text-button" aria-label="關閉" @click="leaveAdd">關閉</button>
    </header>

    <p v-if="recoveryLoading" role="status">正在核對待確認請求…</p>
    <p v-else-if="recoveryError" role="alert" class="notice error">{{ recoveryError }}</p>
    <PendingTransactionRecovery
      v-else-if="transactionCommand?.pending && (!sendingDaily || retryingDaily)"
      :payload="transactionCommand.pending.payload"
      :message="pendingMessage"
      :transaction-id="legacyTransactionId"
      :busy="retryingDaily"
      @retry="retryDailyPending"
      @acknowledge="acknowledgeDailyPending"
    />
    <ReceiptEntryFlow v-else-if="stage === 'receipt'" @manual="openManual('expense')" @cancel="resetDraft" />

    <template v-else-if="stage === 'input'">
      <form class="sentence" @submit.prevent="parseSentence">
        <label for="sentenceInput" class="sr-only">說一句話記帳</label>
        <textarea
          id="sentenceInput"
          v-model="sentence"
          rows="2"
          maxlength="200"
          placeholder="昨天跟同事吃午餐 刷國泰卡 120"
          @keydown.enter.exact.prevent="parseSentence"
        ></textarea>
        <div class="sentence-actions">
          <button type="button" class="text-button" @click="stage = 'receipt'">
            <Document aria-hidden="true" />掃描發票
          </button>
          <button type="submit" class="ink-button" :aria-busy="parsing">
            {{ parsing ? "辨識中" : "填入" }}
          </button>
        </div>
      </form>
      <p v-if="parseNote" class="notice" :class="{ error: parseNoteError }" role="status">{{ parseNote }}</p>
      <p v-if="aiOffer && aiStatus" class="ai-offer">
        <button type="button" class="text-button" :disabled="aiBusy" @click="parseWithAI">
          {{ aiBusy ? "AI 辨識中…" : "規則認不出來？用 AI 試試" }}
        </button>
        <small>今天還剩 {{ aiStatus.remaining }} 次</small>
      </p>
      <p v-if="parseFailure" class="notice error" role="alert">{{ parseFailure }}</p>

      <div class="type-switch" role="radiogroup" aria-label="收支類型">
        <button
          v-for="option in typeOptions"
          :key="option.value"
          type="button"
          role="radio"
          :aria-checked="activeType === option.value"
          :class="{ active: activeType === option.value }"
          @click="switchType(option.value)"
        >{{ option.label }}</button>
      </div>

      <TransactionForm
        :key="clientRequestId"
        class="manual-heading"
        :type="activeType"
        :draft="draftForForm"
        :client-request-id="clientRequestId"
        :external-submit="submitDailyTransaction"
        :submit-label="activeType === 'income' ? '記下收入' : '記下支出'"
        @transaction-added="handleAdded"
      />
    </template>

    <template v-else>
      <section class="success-panel" role="status">
        <CircleCheckFilled class="success-check" aria-hidden="true" />
        <h2>{{ successResult?.replayed ? "這筆紀錄先前已建立" : "已記下" }}</h2>
        <p v-if="successResult?.replayed">沒有重複建立或扣款。</p>
      </section>

      <AccountImpactCard
        v-if="successResult?.impact"
        :kind="successResult.impact.kind"
        :amount="successResult.impact.amount"
        :account="successResult.impact.account"
        :currency="successResult.impact.currency"
        confirmed
      />

      <div class="success-actions">
        <button type="button" class="ghost-button" @click="finishAdded">完成</button>
        <button type="button" class="ink-button" @click="resetDraft">再記一筆</button>
      </div>
    </template>
  </div>
</template>

<script>
import apiClient from "@/api";
import { openPendingCommand } from '@/utils/pendingFinancialCommand';
import PendingTransactionRecovery from '@/components/shared/PendingTransactionRecovery.vue';
import ReceiptEntryFlow from "@/components/receipts/ReceiptEntryFlow.vue";
import TransactionForm from "@/components/budgets/TransactionForm.vue";
import AccountImpactCard from "@/components/shared/AccountImpactCard.vue";
import { CircleCheckFilled, Document } from "@element-plus/icons-vue";

export default {
  name: "UniversalAddView",
  components: {
    PendingTransactionRecovery,
    ReceiptEntryFlow,
    TransactionForm,
    AccountImpactCard,
    CircleCheckFilled,
    Document,
  },
  data() {
    return {
      transactionCommand: null,
      transactionCommandPromise: null,
      recoveryLoading: true,
      recoveryError: '',
      pendingMessage: '',
      legacyTransactionId: '',
      sendingDaily: false,
      retryingDaily: false,
      stage: this.$route.query.mode === "receipt" ? "receipt" : "input",
      activeType: this.$route.query.type === "income" ? "income" : "expense",
      typeOptions: [{ value: "expense", label: "支出" }, { value: "income", label: "收入" }],
      draft: null,
      sentence: "",
      parsing: false,
      aiStatus: null,
      aiOffer: false,
      aiBusy: false,
      parseNote: "",
      parseNoteError: false,
      parseFailure: "",
      successResult: null,
      clientRequestId: this.createRequestId(),
      returnTo: this.safeReturnPath(window.history.state?.returnTo),
    };
  },
  mounted() {
    this.ensureTransactionCommand().catch(() => {});
    this.loadAiStatus();
  },
  computed: {
    draftForForm() {
      return this.draft && Object.keys(this.draft).length ? this.draft : null;
    },
  },
  methods: {
    async ensureTransactionCommand() {
      if (!this.transactionCommandPromise) {
        this.transactionCommandPromise = openPendingCommand('transaction:daily').then(command => {
          this.transactionCommand = command;
          return this.transactionCommand;
        }).catch(error => {
          this.recoveryError = '無法讀取待確認請求，請先核對紀錄並確認瀏覽器儲存可用。';
          throw error;
        }).finally(() => { this.recoveryLoading = false; });
      }
      return this.transactionCommandPromise;
    },
    async submitDailyTransaction(payload) {
      if (this.sendingDaily) {
        const error = new Error('上一筆請求仍在處理中');
        error.recoveryHandled = true;
        throw error;
      }
      this.sendingDaily = true;
      let command;
      let sent = false;
      let requestId;
      try {
        command = await this.ensureTransactionCommand();
        await command.verifyOwner();
        const intent = { ...payload };
        delete intent.client_request_id;
        const request = command.prepare(intent);
        requestId = request.client_request_id;
        sent = true;
        const response = await apiClient.post('/api/transactions', request, { headers: { 'X-Nomica-Request-Owner': command.ownerId } });
        if (response.data?.success !== true) throw new Error('結果尚未確認');
        command.clear(requestId);
        this.pendingMessage = '';
        this.legacyTransactionId = '';
        return response;
      } catch (error) {
        if (error.ownerChanged || error.response?.data?.code === 'REQUEST_OWNER_CHANGED') {
          this.recoveryError = error.response?.data?.message || error.message;
          error.recoveryHandled = true;
        } else if (sent && error.response?.status === 400) {
          command?.clear(requestId);
          this.parseFailure = error.response?.data?.message || '交易未建立，請調整資料後重新提交。';
        } else if (command?.pending) {
          this.pendingMessage = error.response?.data?.message || '結果尚未確認，請以保留的原資料重試。';
          this.legacyTransactionId = error.response?.data?.code === 'LEGACY_REQUEST_UNVERIFIABLE'
            ? String(error.response.data.data?.transaction_id || '') : '';
          error.recoveryHandled = true;
        } else if (!sent) {
          this.recoveryError = '無法保存待確認請求，未送出交易。請確認瀏覽器儲存可用後重試。';
          error.recoveryHandled = true;
        }
        throw error;
      } finally { this.sendingDaily = false; }
    },
    async retryDailyPending() {
      if (this.retryingDaily || !this.transactionCommand?.pending) return;
      this.retryingDaily = true;
      const payload = this.transactionCommand.pending.payload;
      try {
        const response = await this.submitDailyTransaction(payload);
        this.handleAdded({ type: payload.type, transactionId: response.data.data?.transaction_id,
          replayed: response.data.replayed === true });
      } catch { /* The pending panel retains the original intent and explains the failure. */ }
      finally { this.retryingDaily = false; }
    },
    acknowledgeDailyPending() {
      if (!this.legacyTransactionId || this.retryingDaily || !this.transactionCommand?.pending) return;
      try {
        this.transactionCommand.clear();
        this.legacyTransactionId = '';
        this.pendingMessage = '';
        this.resetDraft();
      } catch { this.recoveryError = '無法清除本機待確認狀態；既有交易未被修改，請確認瀏覽器儲存可用。'; }
    },
    createRequestId() {
      return crypto.randomUUID();
    },
    safeReturnPath(path) {
      if (typeof path !== "string" || !path.startsWith("/") || path.startsWith("//")) {
        return "";
      }
      return path === "/add" ? "" : path;
    },
    async loadAiStatus() {
      try {
        const response = await apiClient.get("/api/ai/status");
        const data = response.data?.data;
        this.aiStatus = data?.available ? data : null;
      } catch {
        this.aiStatus = null; // AI is optional: the page works without it.
      }
    },
    // Shows a recognised sentence as a draft. Returns true when a transaction was found.
    applyParseResponse(response, text) {
      const result = response.data?.data?.parse_result || {};
      const transaction = result.transaction;
      if (!transaction) return false;
      this.applyDraft({ ...transaction, raw_text: text, parse_event_id: response.data?.data?.parse_event_id || "" });
      const missing = (result.missing_fields || []).includes("amount") || !transaction.amount;
      this.parseNote = missing ? "已填入，請補上金額後確認。" : "已填入下方欄位，確認後按記下。";
      this.parseNoteError = missing;
      this.sentence = "";
      return true;
    },
    async parseSentence() {
      const text = this.sentence.trim();
      if (this.parsing) return;
      if (!text) {
        this.parseNote = "先輸入一句話，例如「午餐 120」。";
        this.parseNoteError = true;
        return;
      }
      this.parsing = true;
      this.parseNote = "";
      this.parseNoteError = false;
      this.parseFailure = "";
      this.aiOffer = false;
      try {
        const response = await apiClient.post("/api/parse/local", { text });
        if (!this.applyParseResponse(response, text)) {
          this.applyDraft({ type: this.activeType, title: text.slice(0, 40) });
          this.parseNote = "沒有認出這句話，已放進項目，請補上金額。";
          this.parseNoteError = true;
          this.aiOffer = Boolean(this.aiStatus && this.aiStatus.remaining > 0);
        }
      } catch (error) {
        this.parseNote = error.response?.data?.message || "目前無法辨識，請直接填寫下方欄位。";
        this.parseNoteError = true;
      } finally {
        this.parsing = false;
      }
    },
    async confirmAiConsent() {
      const answer = await this.$swal.fire({
        title: "使用 AI 解析這句話？",
        text: this.aiStatus.notice,
        icon: "info",
        showCancelButton: true,
        confirmButtonText: "同意並使用",
        cancelButtonText: "不用了",
      });
      if (!answer.isConfirmed) return false;
      await apiClient.post("/api/ai/consent", { consented: true });
      this.aiStatus = { ...this.aiStatus, consented: true };
      return true;
    },
    async parseWithAI() {
      const text = this.sentence.trim();
      if (this.aiBusy || !text || !this.aiStatus) return;
      this.aiBusy = true;
      this.parseFailure = "";
      try {
        if (!this.aiStatus.consented && !(await this.confirmAiConsent())) return;
        // A fresh id per attempt: the server counts and de-duplicates by it.
        const response = await apiClient.post("/api/parse/ai", {
          text, client_request_id: this.createRequestId(),
        });
        this.aiOffer = false;
        if (!this.applyParseResponse(response, text)) {
          this.parseNote = "AI 也看不懂這句話，請直接填寫下方欄位。";
          this.parseNoteError = true;
        }
      } catch (error) {
        const data = error.response?.data;
        if (data?.code === "AI_CONSENT_REQUIRED") this.aiStatus = { ...this.aiStatus, consented: false };
        if (data?.code === "AI_DAILY_LIMIT") this.aiStatus = { ...this.aiStatus, remaining: 0 };
        this.parseNote = data?.message || "AI 暫時無法使用，請直接填寫下方欄位。";
        this.parseNoteError = true;
        if (!["AI_BUSY", "AI_TOO_FAST", "AI_CONSENT_REQUIRED"].includes(data?.code)) this.aiOffer = false;
      } finally {
        this.aiBusy = false;
        this.loadAiStatus();
      }
    },
    applyDraft(draft) {
      this.activeType = draft.type === "income" ? "income" : "expense";
      this.draft = { ...draft, type: this.activeType };
    },
    switchType(type) {
      if (type === this.activeType) return;
      this.activeType = type;
      this.draft = null;
      this.parseNote = "";
      this.clientRequestId = this.createRequestId();
    },
    openManual(type) {
      this.activeType = type;
      this.draft = null;
      this.parseFailure = "";
      this.successResult = null;
      this.clientRequestId = this.createRequestId();
      this.stage = "input";
    },
    resetDraft() {
      this.stage = "input";
      this.draft = null;
      this.sentence = "";
      this.parseNote = "";
      this.parseFailure = "";
      this.successResult = null;
      this.clientRequestId = this.createRequestId();
    },
    handleAdded(result) {
      this.successResult = result || {};
      this.stage = "success";
      window.scrollTo({ top: 0, behavior: "smooth" });
    },
    finishAdded() {
      const fallback = "/";
      this.$router.replace(this.returnTo || fallback);
    },
    leaveAdd() {
      if (this.returnTo) {
        this.$router.replace(this.returnTo);
        return;
      }
      this.$router.push("/");
    },
  },
};
</script>

<style scoped>
.universal-add-screen {
  max-width: var(--compact-page-max-width);
  min-height: calc(100vh - var(--app-bottom-nav-height));
  margin: 0 auto;
  padding: 20px 16px calc(var(--app-bottom-nav-height) + 24px);
  color: var(--text-color);
}

.add-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.add-header h1 {
  margin: 0;
  font-size: 1.5rem;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
}

.sentence {
  display: grid;
  gap: 8px;
  margin-bottom: 12px;
  padding: 12px;
  border: 1px solid var(--brand-border);
  border-radius: 12px;
  background: var(--card-bg);
}

.sentence textarea {
  width: 100%;
  min-height: 56px;
  padding: 0;
  border: 0;
  resize: none;
  color: var(--text-color);
  background: transparent;
  font-size: 1.05rem;
  line-height: 1.5;
  outline: none;
}

.sentence:focus-within {
  border-color: var(--text-color);
}

.sentence-actions,
.success-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.text-button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 40px;
  padding: 0 8px;
  color: var(--light-text-color);
  background: transparent;
  border: 0;
  font-weight: 600;
}

.text-button svg {
  width: 16px;
  height: 16px;
}

.ink-button,
.ghost-button {
  min-height: 44px;
  padding: 0 18px;
  border-radius: 10px;
  font-weight: 700;
}

.ink-button {
  color: var(--on-primary);
  background: var(--primary-color);
  border: 0;
}

.ink-button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.ghost-button {
  color: var(--text-color);
  background: transparent;
  border: 1px solid var(--border-color);
}

.notice {
  margin: 0 0 12px;
  color: var(--light-text-color);
  font-size: 0.88rem;
}

.notice.error {
  color: var(--expense-color);
}

.ai-offer {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 0 12px;
}

.ai-offer small {
  color: var(--light-text-color);
}

.type-switch {
  display: inline-flex;
  margin: 4px 0 8px;
  padding: 3px;
  border-radius: 10px;
  background: var(--secondary-color);
}

.type-switch button {
  min-width: 72px;
  min-height: 36px;
  padding: 0 14px;
  border: 0;
  border-radius: 8px;
  color: var(--light-text-color);
  background: transparent;
  font-weight: 700;
}

.type-switch button.active {
  color: var(--text-color);
  background: var(--card-bg);
}

.success-panel {
  display: grid;
  justify-items: center;
  gap: 6px;
  padding: 24px 0 16px;
  text-align: center;
}

.success-panel h2,
.success-panel p {
  margin: 0;
}

.success-panel p {
  color: var(--light-text-color);
}

.success-check {
  width: 44px;
  height: 44px;
  color: var(--income-color);
}

.success-actions {
  margin-top: 16px;
}

.success-actions button {
  flex: 1;
}
</style>
