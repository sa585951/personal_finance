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
          <div><dt>帳戶</dt><dd>{{ draft.account_hint || "不連動帳戶" }}</dd></div>
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

    <template v-else>
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
  </div>
</template>

<script>
import AIQuickInput from "@/components/budgets/AIQuickInput.vue";
import TransactionForm from "@/components/budgets/TransactionForm.vue";

export default {
  name: "UniversalAddView",
  components: { AIQuickInput, TransactionForm },
  data() {
    return {
      stage: "input",
      preferredType: this.$route.query.type === "income" ? "income" : "expense",
      activeType: "expense",
      draft: {},
      missingFields: [],
      expanded: false,
      parseFailure: "",
      clientRequestId: this.createRequestId(),
      returnTo: this.safeReturnPath(window.history.state?.returnTo),
    };
  },
  computed: {
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
      this.clientRequestId = this.createRequestId();
      this.stage = "preview";
    },
    openManual(type) {
      this.activeType = type;
      this.draft = {};
      this.missingFields = [];
      this.expanded = true;
      this.parseFailure = "";
      this.clientRequestId = this.createRequestId();
      this.stage = "manual";
    },
    resetDraft() {
      this.stage = "input";
      this.draft = {};
      this.missingFields = [];
      this.expanded = false;
      this.parseFailure = "";
      this.clientRequestId = this.createRequestId();
    },
    async handleAdded(result) {
      const fallback = `/transactions?type=${result?.type === "income" ? "income" : "expense"}`;
      await this.$swal.fire({
        title: result?.replayed ? "已完成" : "新增成功",
        text: result?.replayed ? "這筆紀錄先前已經建立。" : "交易已加入紀錄。",
        icon: "success",
        timer: 1000,
        showConfirmButton: false,
      });
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
.manual-heading {
  margin-bottom: 14px;
  padding: 16px;
  background: #ffffff;
  border: 1px solid #dbe4ee;
  border-radius: 10px;
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
  .preview-card dl {
    grid-template-columns: 1fr;
  }
}
</style>
