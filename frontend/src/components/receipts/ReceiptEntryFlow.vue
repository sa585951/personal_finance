<template>
  <section class="receipt-flow" aria-label="發票掃描記帳">
    <h2>掃描發票</h2>
    <p>請對準台灣電子發票左側 QR Code。圖片只在裝置解析，不會上傳或保存。</p>
    <template v-if="!receipt">
      <button type="button" :disabled="busy || camera" @click="startCamera">開啟相機</button>
      <label class="image-choice">選擇圖片<input type="file" accept="image/jpeg,image/png,image/webp" :disabled="busy" @change="scanImage" /></label>
      <video v-show="camera" ref="video" muted playsinline aria-label="相機預覽"></video>
      <button v-if="camera" type="button" @click="stopCamera">關閉相機</button>
    </template>
    <template v-else>
      <dl>
        <div><dt>發票號碼</dt><dd>{{ receipt.invoice_number }}</dd></div>
        <div><dt>日期</dt><dd>{{ receipt.issued_on }}</dd></div>
        <div><dt>總額</dt><dd>{{ receipt.total_amount }} TWD</dd></div>
        <div><dt>賣方統編</dt><dd>{{ receipt.seller_identifier }}</dd></div>
      </dl>
      <p v-if="receipt.status === 'linked'" role="status">{{ createdHere ? '記帳完成，發票已連結這筆支出。' : '這張發票已連結交易，沒有再次建立支出。' }}</p>
      <AccountImpactCard v-if="successImpact" :kind="successImpact.kind" :amount="successImpact.amount" :account="successImpact.account" :currency="successImpact.currency" confirmed />
      <template v-else-if="receipt.status === 'ignored'">
        <p>這張發票先前已略過。</p>
        <button type="button" :disabled="busy" @click="resolve('reopen')">重新處理</button>
      </template>
      <template v-else>
        <label>店名（選填）<input v-model="merchant" maxlength="255" :disabled="busy" /></label>
        <button type="button" :disabled="busy" @click="loadMatches">比對既有紀錄</button>
        <p>日期與金額相同也可能是不同消費，請自行確認。</p>
        <div v-for="candidate in candidates" :key="candidate.id" class="candidate">
          <span>{{ candidate.date }} · {{ candidate.merchant || candidate.title }} · {{ candidate.amount }} TWD</span>
          <small>{{ candidate.reasons.join('、') }}</small>
          <button type="button" :disabled="busy" @click="resolve('link', candidate.id)">連結這筆</button>
        </div>
        <p v-if="matched && !candidates.length">沒有找到符合日期與金額的既有紀錄。</p>
        <button v-if="!creating" type="button" :disabled="busy" @click="creating = true">建立新交易</button>
        <TransactionForm v-if="creating" type="expense" :draft="draft" :external-submit="createTransaction" locked-receipt-fields @transaction-added="handleCreated" />
        <button type="button" :disabled="busy" @click="resolve('ignore')">略過這張發票</button>
        <button type="button" :disabled="busy" @click="$emit('cancel')">稍後處理（再掃描可繼續）</button>
      </template>
      <router-link v-if="receipt.status === 'linked'" :to="`/transactions?type=expense&month=${receipt.issued_on.slice(0, 7)}`">查看紀錄</router-link>
      <button type="button" :disabled="busy" @click="reset">再掃一張</button>
    </template>
    <p v-if="busy" role="status">處理中…</p>
    <p v-if="error" role="alert">{{ error }}</p>
    <button type="button" :disabled="busy" @click="$emit('manual')">改用手動記帳</button>
    <button type="button" :disabled="busy" @click="$emit('cancel')">返回輸入方式</button>
  </section>
</template>

<script>
import { BrowserQRCodeReader } from "@zxing/browser";
import apiClient from "@/api";
import TransactionForm from "@/components/budgets/TransactionForm.vue";
import AccountImpactCard from "@/components/shared/AccountImpactCard.vue";

export default {
  components: { TransactionForm, AccountImpactCard },
  emits: ["manual", "cancel"],
  data() {
    return { receipt: null, merchant: "", candidates: [], matched: false, creating: false, busy: false, error: "", camera: false, controls: null, reader: null, generation: 0, resolvedReceipt: null, successImpact: null, createdHere: false };
  },
  computed: {
    draft() {
      return { type: "expense", date: this.receipt.issued_on, amount: this.receipt.total_amount, currency: "TWD", title: "發票支出" };
    },
  },
  beforeUnmount() { this.stopCamera(); },
  methods: {
    stopCamera() {
      this.generation += 1;
      this.controls?.stop();
      this.controls = null;
      this.$refs.video?.srcObject?.getTracks().forEach((track) => track.stop());
      if (this.$refs.video) this.$refs.video.srcObject = null;
      this.camera = false;
    },
    async startCamera() {
      this.error = "";
      this.camera = true;
      const generation = ++this.generation;
      try {
        await this.$nextTick();
        this.reader = new BrowserQRCodeReader();
        const controls = await this.reader.decodeFromConstraints(
          { video: { facingMode: { ideal: "environment" } }, audio: false },
          this.$refs.video,
          (result) => {
            if (result && !this.busy && !this.receipt && generation === this.generation) {
              this.importQr(result.getText(), "qr_camera");
            }
          }
        );
        if (generation !== this.generation) controls.stop();
        else this.controls = controls;
      } catch {
        this.stopCamera();
        this.error = "無法開啟相機，請確認權限或改用圖片。";
      }
    },
    async scanImage(event) {
      const file = event.target.files?.[0];
      event.target.value = "";
      if (!file || this.busy) return;
      this.stopCamera();
      if (!["image/jpeg", "image/png", "image/webp"].includes(file.type) || file.size > 10 * 1024 * 1024) {
        this.error = "請選擇 10 MB 以下的 JPEG、PNG 或 WebP 圖片。";
        return;
      }
      this.busy = true;
      this.error = "";
      const generation = this.generation;
      const url = URL.createObjectURL(file);
      try {
        const result = await new BrowserQRCodeReader().decodeFromImageUrl(url);
        if (generation !== this.generation) return;
        this.busy = false;
        await this.importQr(result.getText(), "qr_image");
      } catch {
        this.error = "找不到可辨識的 QR Code，請裁切左側 QR 後再試。";
      } finally {
        URL.revokeObjectURL(url);
        this.busy = false;
      }
    },
    async importQr(qrPayload, inputMethod) {
      if (this.busy) return;
      this.busy = true;
      this.stopCamera();
      this.error = "";
      try {
        const response = await apiClient.post("/api/receipt-imports", { qr_payload: qrPayload, input_method: inputMethod });
        this.receipt = response.data.data.receipt;
        this.merchant = this.receipt.merchant_name || "";
        if (this.receipt.status === "pending") await this.fetchMatches();
      } catch (error) {
        this.error = error.response?.data?.message || "匯入失敗，請稍後再試。";
      } finally { this.busy = false; }
    },
    async fetchMatches() {
      const response = await apiClient.get(`/api/receipt-imports/${this.receipt.id}/matches`, { params: { merchant: this.merchant } });
      this.candidates = response.data.data.candidates;
      this.matched = true;
    },
    async loadMatches() {
      if (this.busy) return;
      this.busy = true;
      this.error = "";
      try { await this.fetchMatches(); }
      catch (error) { this.error = error.response?.data?.message || "比對失敗，請重試。"; }
      finally { this.busy = false; }
    },
    async resolve(action, transactionId) {
      if (this.busy) return;
      this.busy = true;
      this.error = "";
      try {
        const response = await apiClient.post(`/api/receipt-imports/${this.receipt.id}/resolve`, { action, transaction_id: transactionId, merchant: this.merchant });
        this.receipt = response.data.data.receipt;
        this.creating = false;
        if (action === "reopen") await this.fetchMatches();
      } catch (error) { this.error = error.response?.data?.message || "處理失敗，請重試。"; }
      finally { this.busy = false; }
    },
    async createTransaction(payload) {
      if (this.busy) throw new Error("發票處理中");
      this.busy = true;
      try {
        const response = await apiClient.post(`/api/receipt-imports/${this.receipt.id}/resolve`, { ...payload, action: "create", merchant: this.merchant });
        this.resolvedReceipt = response.data.data.receipt;
        return { data: { data: { transaction_id: this.resolvedReceipt.transaction_id }, replayed: response.data.data.replayed } };
      } catch (error) { this.busy = false; throw error; }
    },
    handleCreated(result) { this.receipt = this.resolvedReceipt; this.successImpact = result.impact; this.creating = false; this.busy = false; this.createdHere = !result.replayed; },
    reset() { this.stopCamera(); this.receipt = null; this.candidates = []; this.matched = false; this.creating = false; this.error = ""; this.successImpact = null; this.resolvedReceipt = null; this.createdHere = false; },
  },
};
</script>

<style scoped>
.receipt-flow { display: grid; gap: 14px; padding: 16px; color: var(--text-color); background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; }
button, .image-choice { min-height: 44px; padding: 10px; border: 1px solid var(--brand-border); border-radius: 8px; color: var(--text-color); background: var(--primary-soft); cursor: pointer; }
button:disabled { opacity: .5; cursor: wait; }
input { max-width: 100%; min-height: 44px; }
video { width: 100%; max-height: 340px; }
dl { margin: 0; } dl div { display: flex; justify-content: space-between; gap: 8px; } dd { margin: 0; overflow-wrap: anywhere; }
.candidate { display: grid; gap: 6px; padding: 10px; border: 1px solid var(--border-color); border-radius: 8px; }
p { margin: 0; } small { color: var(--light-text-color); }
</style>
