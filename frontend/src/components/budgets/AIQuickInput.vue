<template>
  <section class="ai-quick-input">
    <div class="quick-header">
      <div>
        <p class="eyebrow">AI Quick Entry</p>
        <h2>一句話記帳</h2>
      </div>
      <span class="status-pill">先解析</span>
    </div>

    <form class="quick-form" @submit.prevent="parseInput">
      <label for="aiQuickText">
        快速輸入
        <textarea
          id="aiQuickText"
          v-model="text"
          rows="2"
          :placeholder="placeholderText"
          :disabled="isParsing"
        ></textarea>
      </label>
      <button type="submit" :disabled="isParsing || !text.trim()">
        {{ isParsing ? "解析中" : "解析" }}
      </button>
    </form>

    <div class="example-chips" aria-label="快速輸入範例">
      <button
        v-for="example in examples"
        :key="example"
        type="button"
        :disabled="isParsing"
        @click="useExample(example)"
      >
        {{ example }}
      </button>
    </div>

    <p v-if="errorMessage" class="parse-message error">{{ errorMessage }}</p>

    <div v-if="parseResult && !autoApply" class="parse-result">
      <div class="result-heading">
        <span>{{ resultTitle }}</span>
        <small>{{ sourceLabel }}</small>
      </div>

      <div v-if="transaction" class="result-grid">
        <div>
          <span>類型</span>
          <strong>{{ transaction.type === "income" ? "收入" : "支出" }}</strong>
        </div>
        <div>
          <span>金額</span>
          <strong>{{ transaction.amount || "未判斷" }}</strong>
        </div>
        <div>
          <span>類別</span>
          <strong>{{ transaction.budget_category || "未判斷" }}</strong>
        </div>
        <div>
          <span>項目</span>
          <strong>{{ transaction.title || "未判斷" }}</strong>
        </div>
        <div>
          <span>備註</span>
          <strong>{{ transaction.description || "無" }}</strong>
        </div>
        <div>
          <span>幣別</span>
          <strong>{{ transaction.currency || "預設" }}</strong>
        </div>
        <div>
          <span>帳戶提示</span>
          <strong>{{ transaction.account_name || transaction.account_hint || "無" }}</strong>
        </div>
      </div>

      <p v-if="missingFields.length" class="parse-message warning">
        尚缺：{{ missingFields.join("、") }}
      </p>
      <p v-if="!transaction" class="parse-message warning">
        {{ resultMessage }}
      </p>

      <button
        v-if="transaction"
        class="apply-button"
        type="button"
        @click="applyResult"
      >
        {{ hasAppliedResult ? "已套用，可再套用一次" : "套用到表單" }}
      </button>
    </div>
  </section>
</template>

<script>
import apiClient from "@/api";

export default {
  name: "AIQuickInput",
  props: {
    type: {
      type: String,
      default: "expense",
      validator: (value) => ["expense", "income"].includes(value),
    },
    autoApply: {
      type: Boolean,
      default: false,
    },
  },
  emits: ["apply-draft", "parsed", "parse-failed"],
  data() {
    return {
      text: "",
      isParsing: false,
      parseResult: null,
      parseEventId: "",
      errorMessage: "",
      hasAppliedResult: false,
    };
  },
  computed: {
    placeholderText() {
      return this.type === "income"
        ? "例如：薪資 50000 存入玉山帳戶"
        : "例如：晚餐 680 用國泰信用卡";
    },
    examples() {
      if (this.type === "income") {
        return [
          "薪資 50000 存入玉山帳戶",
          "獎金 8000 存入銀行",
          "退款 1200 存入現金",
          "利息 300 存入台新活存",
        ];
      }
      return [
        "午餐麥當勞 150",
        "晚餐 680 用國泰信用卡",
        "火車票 台北到台中 460 用現金",
        "拉麵 1200 日幣 用日幣現金",
      ];
    },
    transaction() {
      return this.parseResult?.transaction || null;
    },
    parseErrors() {
      return this.parseResult?.errors || [];
    },
    usableTransaction() {
      return Boolean(this.transaction && this.parseErrors.length === 0);
    },
    missingFields() {
      return this.parseResult?.missing_fields || [];
    },
    resultTitle() {
      if (this.transaction) {
        return "解析結果";
      }
      return "尚未形成交易";
    },
    resultMessage() {
      if (this.parseResult?.errors?.length) {
        return this.parseResult.errors[0];
      }
      return "目前這句話沒有解析成收入或支出，先不套用到表單。";
    },
    sourceLabel() {
      const labelMap = {
        quick: "規則解析",
        gemini: "AI 解析",
        local_fallback: "本地解析",
      };
      return labelMap[this.parseResult?.source] || "解析";
    },
  },
  watch: {
    type() {
      this.errorMessage = "";
      this.parseResult = null;
      this.parseEventId = "";
      this.hasAppliedResult = false;
    },
  },
  methods: {
    useExample(example) {
      if (this.isParsing) return;
      this.text = example;
      this.errorMessage = "";
      this.parseResult = null;
      this.parseEventId = "";
      this.hasAppliedResult = false;
    },
    async parseInput() {
      this.errorMessage = "";
      this.parseResult = null;
      this.parseEventId = "";
      this.hasAppliedResult = false;
      this.isParsing = true;
      try {
        const response = await apiClient.post("/api/ai/parse", {
          text: this.text.trim(),
        });
        const responseData = response.data.data || {};
        this.parseResult = responseData.parse_result || null;
        this.parseEventId = responseData.parse_event_id || "";
        if (this.usableTransaction) {
          this.text = "";
          if (this.autoApply) {
            this.applyResult();
          }
        } else {
          this.$emit("parse-failed", this.resultMessage);
        }
        this.$emit("parsed", this.parseResult);
      } catch (error) {
        console.error("AI 解析失敗", error);
        this.errorMessage = error.response?.data?.message || "解析失敗，請稍後再試。";
      } finally {
        this.isParsing = false;
      }
    },
    applyResult() {
      if (!this.usableTransaction) return;
      this.hasAppliedResult = true;
      this.$emit("apply-draft", {
        ...this.transaction,
        raw_text: this.parseResult.raw_text,
        parse_event_id: this.parseEventId,
        missing_fields: this.missingFields,
        errors: this.parseErrors,
      });
    },
  },
};
</script>

<style scoped>
.ai-quick-input {
  margin: 0 0 1rem;
  padding: 16px;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  background: #f8fbff;
}

.quick-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.quick-header h2 {
  margin: 0;
  color: #0f172a;
  font-size: 1.1rem;
}

.eyebrow {
  margin: 0 0 3px;
  color: #2563eb;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 0 9px;
  color: #1d4ed8;
  background: #dbeafe;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 800;
  white-space: nowrap;
}

.quick-form {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  align-items: end;
}

.quick-form label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
  color: #475569;
  font-size: 0.9rem;
  font-weight: 800;
  text-align: left;
}

.quick-form textarea {
  width: 100%;
  min-height: 58px;
  padding: 10px 12px;
  color: #0f172a;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font: inherit;
  resize: vertical;
}

.quick-form button,
.apply-button {
  min-height: 42px;
  padding: 0 16px;
  color: #ffffff;
  background: #2563eb;
  border: 0;
  border-radius: 8px;
  box-shadow: none;
  font-weight: 800;
}

.quick-form button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.example-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.example-chips button {
  min-height: 32px;
  padding: 0 10px;
  color: #1e3a8a;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 999px;
  font-size: 0.82rem;
  font-weight: 800;
}

.example-chips button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.parse-result {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #ffffff;
}

.result-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
  color: #0f172a;
  font-weight: 900;
}

.result-heading small {
  color: #64748b;
  font-size: 0.78rem;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.result-grid div {
  min-width: 0;
  padding: 10px;
  background: #f8fafc;
  border-radius: 8px;
}

.result-grid span {
  display: block;
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 800;
}

.result-grid strong {
  display: block;
  margin-top: 2px;
  color: #0f172a;
  overflow-wrap: anywhere;
}

.hint-line,
.parse-message {
  margin: 10px 0 0;
  color: #475569;
  font-size: 0.88rem;
  font-weight: 700;
}

.parse-message.error {
  color: #b91c1c;
}

.parse-message.warning {
  color: #b45309;
}

.apply-button {
  width: 100%;
  margin-top: 12px;
}

@media (max-width: 520px) {
  .quick-form {
    grid-template-columns: 1fr;
  }

  .quick-form button {
    width: 100%;
  }
}
</style>
