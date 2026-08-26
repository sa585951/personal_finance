<template>
  <div class="universal-add-screen">
    <header class="add-header">
      <button type="button" aria-label="返回" @click="leaveAdd">返回</button>
      <div>
        <p>Nomica Quick Entry</p>
        <h1>新增收支</h1>
      </div>
      <span aria-hidden="true"></span>
    </header>

    <template v-if="stage === 'input'">
      <AIQuickInput
        :type="preferredType"
        auto-apply
        @apply-draft="openPreview"
        @parse-failed="parseFailure = $event"
      />

      <p v-if="parseFailure" class="parse-failure">{{ parseFailure }}</p>

      <section class="manual-options" aria-labelledby="manualEntryTitle">
        <div>
          <p>Manual Entry</p>
          <h2 id="manualEntryTitle">改用手動輸入</h2>
        </div>
        <div class="manual-buttons">
          <button type="button" class="expense" @click="openManual('expense')">
            手動新增支出
          </button>
          <button type="button" class="income" @click="openManual('income')">
            手動新增收入
          </button>
        </div>
      </section>
    </template>

    <template v-else-if="stage === 'preview'">
      <section class="preview-card">
        <div class="preview-heading">
          <div>
            <p>AI Preview</p>
            <h2>確認解析內容</h2>
          </div>
          <span :class="activeType">{{ activeType === "income" ? "收入" : "支出" }}</span>
        </div>
        <dl>
          <div><dt>項目</dt><dd>{{ draft.title || "待補" }}</dd></div>
          <div><dt>金額</dt><dd>{{ draft.amount || "待補" }}</dd></div>
          <div><dt>類別</dt><dd>{{ draft.budget_category || "待補" }}</dd></div>
          <div><dt>日期</dt><dd>{{ draft.date || "今天" }}</dd></div>
          <div><dt>帳戶</dt><dd>{{ draft.account_name || draft.account_hint || "不連動帳戶" }}</dd></div>
          <div><dt>備註</dt><dd>{{ draft.description || "無" }}</dd></div>
        </dl>
        <p v-if="missingFieldLabels.length" class="missing-fields">
          請先補上：{{ missingFieldLabels.join("、") }}
        </p>
        <div class="preview-actions">
          <button type="button" @click="expanded = !expanded">
            {{ expanded ? "只看必要欄位" : "調整資料" }}
          </button>
          <button type="button" @click="resetDraft">重新輸入</button>
        </div>
      </section>

      <TransactionForm
        :key="clientRequestId"
        :type="activeType"
        :draft="draft"
        mode="preview"
        :missing-fields="missingFields"
        :expanded="expanded"
        :client-request-id="clientRequestId"
        submit-label="確認新增"
        @transaction-added="handleAdded"
      />
    </template>

    <template v-else-if="stage === 'manual'">
      <section class="manual-heading">
        <div>
          <p>Manual Entry</p>
          <h2>{{ activeType === "income" ? "手動新增收入" : "手動新增支出" }}</h2>
        </div>
        <button type="button" @click="resetDraft">改用 AI</button>
      </section>
      <TransactionForm
        :key="clientRequestId"
        :type="activeType"
        :client-request-id="clientRequestId"
        @transaction-added="handleAdded"
      />
    </template>

    <template v-else>
      <section class="success-panel">
        <div
          class="success-visual"
          :class="successKind"
          :aria-label="successKind === 'income' ? '收入已存入帳戶' : '支出已由帳戶扣除'"
          role="img"
        >
          <div class="success-account">
            <span></span>
            <component :is="successKind === 'income' ? 'BottomLeft' : 'TopRight'" />
          </div>
          <CircleCheckFilled class="success-check" aria-hidden="true" />
        </div>
        <p>Entry completed</p>
        <h2>{{ successResult?.replayed ? "這筆紀錄先前已建立" : "記帳完成" }}</h2>
        <span class="success-copy">
          {{ successResult?.replayed ? "系統沒有重複建立或扣款。" : "交易已加入紀錄，以下是實際採用的帳務影響。" }}
        </span>
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
        <button type="button" class="secondary-action" @click="resetDraft">再記一筆</button>
        <button type="button" class="primary-action" @click="finishAdded">完成並返回</button>
      </div>
    </template>
  </div>
</template>

<script>
import AIQuickInput from "@/components/budgets/AIQuickInput.vue";
import TransactionForm from "@/components/budgets/TransactionForm.vue";
import AccountImpactCard from "@/components/shared/AccountImpactCard.vue";
import { BottomLeft, CircleCheckFilled, TopRight } from "@element-plus/icons-vue";

export default {
  name: "UniversalAddView",
  components: {
    AIQuickInput,
    TransactionForm,
    AccountImpactCard,
    BottomLeft,
    CircleCheckFilled,
    TopRight,
  },
  data() {
    return {
      stage: "input",
      preferredType: this.$route.query.type === "income" ? "income" : "expense",
      activeType: "expense",
      draft: {},
      missingFields: [],
      expanded: false,
      parseFailure: "",
      successResult: null,
      clientRequestId: this.createRequestId(),
      returnTo: this.safeReturnPath(window.history.state?.returnTo),
    };
  },
  computed: {
    successKind() {
      return this.successResult?.type === "income" ? "income" : "expense";
    },
    missingFieldLabels() {
      const labels = {
        amount: "金額",
        title: "項目",
        budget_category: "類別",
      };
      return this.missingFields.map((field) => labels[field] || field);
    },
  },
  methods: {
    createRequestId() {
      return crypto.randomUUID();
    },
    safeReturnPath(path) {
      if (typeof path !== "string" || !path.startsWith("/") || path.startsWith("//")) {
        return "";
      }
      return path === "/add" ? "" : path;
    },
    openPreview(draft) {
      this.draft = draft;
      this.activeType = draft.type === "income" ? "income" : "expense";
      this.missingFields = Array.isArray(draft.missing_fields) ? draft.missing_fields : [];
      this.expanded = false;
      this.parseFailure = "";
      this.successResult = null;
      this.clientRequestId = this.createRequestId();
      this.stage = "preview";
    },
    openManual(type) {
      this.activeType = type;
      this.draft = {};
      this.missingFields = [];
      this.expanded = true;
      this.parseFailure = "";
      this.successResult = null;
      this.clientRequestId = this.createRequestId();
      this.stage = "manual";
    },
    resetDraft() {
      this.stage = "input";
      this.draft = {};
      this.missingFields = [];
      this.expanded = false;
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
      const fallback = `/transactions?type=${this.successResult?.type === "income" ? "income" : "expense"}`;
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
  max-width: 520px;
  min-height: calc(100vh - var(--app-bottom-nav-height));
  margin: 0 auto;
  padding: 18px 14px calc(var(--app-bottom-nav-height) + 24px);
  color: #1f2933;
}

.add-header,
.preview-heading,
.manual-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.add-header {
  margin-bottom: 16px;
}

.add-header > span {
  width: 50px;
}

.add-header button,
.preview-actions button,
.manual-heading button {
  min-height: 38px;
  padding: 0 12px;
  color: #0f766e;
  background: #f0fdfa;
  border: 1px solid #99f6e4;
  border-radius: 8px;
  font-weight: 800;
}

.add-header p,
.preview-heading p,
.manual-heading p,
.manual-options p {
  margin: 0 0 3px;
  color: #64748b;
  font-size: 0.75rem;
  font-weight: 800;
}

.add-header h1,
.preview-heading h2,
.manual-heading h2,
.manual-options h2 {
  margin: 0;
  letter-spacing: 0;
}

.add-header h1 {
  font-size: 1.55rem;
}

.manual-options,
.preview-card,
.manual-heading,
.success-panel {
  margin-bottom: 14px;
  padding: 16px;
  background: #ffffff;
  border: 1px solid #dbe4ee;
  border-radius: 10px;
}

.success-panel {
  display: grid;
  justify-items: center;
  text-align: center;
}

.success-visual {
  position: relative;
  width: 92px;
  height: 76px;
  margin-bottom: 10px;
  animation: success-arrive 320ms ease-out both;
}

.success-account {
  position: absolute;
  inset: 8px 10px 4px 4px;
  display: grid;
  place-items: center;
  color: #0f766e;
  background: #ecfdf5;
  border: 1px solid #99f6e4;
  border-radius: 12px;
  box-shadow: 0 8px 18px rgba(15, 118, 110, 0.12);
}

.success-account::before,
.success-account::after,
.success-account span {
  position: absolute;
  left: 12px;
  width: 22px;
  height: 3px;
  content: "";
  background: currentColor;
  border-radius: 999px;
  opacity: 0.35;
}

.success-account::before {
  top: 18px;
}

.success-account span {
  top: 27px;
}

.success-account::after {
  top: 36px;
  width: 15px;
}

.success-account > svg {
  width: 28px;
  height: 28px;
  margin-left: 34px;
  stroke-width: 2.2;
}

.success-visual.expense .success-account {
  color: #b45309;
  background: #fffbeb;
  border-color: #fde68a;
  box-shadow: 0 8px 18px rgba(180, 83, 9, 0.12);
}

.success-check {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 25px;
  height: 25px;
  color: #0f766e;
  background: #ffffff;
  border: 3px solid #ffffff;
  border-radius: 50%;
}

@keyframes success-arrive {
  from {
    opacity: 0;
    transform: translateY(6px) scale(0.94);
  }

  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@media (prefers-reduced-motion: reduce) {
  .success-visual {
    animation: none;
  }
}

.success-panel p,
.success-panel h2,
.success-copy {
  margin: 0;
}

.success-panel p {
  color: #0f766e;
  font-size: 0.72rem;
  font-weight: 900;
  text-transform: uppercase;
}

.success-panel h2 {
  margin-top: 3px;
  letter-spacing: 0;
}

.success-copy {
  margin-top: 7px;
  color: #64748b;
  font-size: 0.88rem;
  line-height: 1.5;
}

.success-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 14px;
}

.success-actions button {
  min-height: 46px;
  border-radius: 8px;
  font-weight: 900;
}

.success-actions .secondary-action {
  color: #0f766e;
  background: #f0fdfa;
  border: 1px solid #99f6e4;
}

.success-actions .primary-action {
  color: #ffffff;
  background: #0f766e;
  border: 1px solid #0f766e;
}

.manual-buttons {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 14px;
}

.manual-buttons button {
  min-height: 46px;
  border-radius: 8px;
  font-weight: 900;
}

.manual-buttons .expense {
  color: #b91c1c;
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.manual-buttons .income {
  color: #0f766e;
  background: #f0fdfa;
  border: 1px solid #99f6e4;
}

.preview-heading > span {
  padding: 5px 9px;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 900;
}

.preview-heading > span.expense {
  color: #b91c1c;
  background: #fee2e2;
}

.preview-heading > span.income {
  color: #0f766e;
  background: #ccfbf1;
}

.preview-card dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin: 16px 0 0;
}

.preview-card dl div {
  min-width: 0;
  padding: 10px;
  background: #f8fafc;
  border-radius: 8px;
}

.preview-card dt {
  color: #64748b;
  font-size: 0.76rem;
  font-weight: 800;
}

.preview-card dd {
  margin: 3px 0 0;
  color: #0f172a;
  font-weight: 900;
  overflow-wrap: anywhere;
}

.missing-fields,
.parse-failure {
  padding: 10px 12px;
  color: #92400e;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
  font-weight: 800;
}

.preview-actions {
  display: flex;
  gap: 8px;
  margin-top: 14px;
}

@media (max-width: 430px) {
  .manual-buttons,
  .preview-card dl,
  .success-actions {
    grid-template-columns: 1fr;
  }
}
</style>
