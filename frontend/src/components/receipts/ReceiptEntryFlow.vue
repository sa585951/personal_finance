<template>
  <section class="receipt-flow" aria-label="發票掃描記帳">
    <div class="receipt-heading">
      <span class="receipt-symbol"><Document aria-hidden="true" /></span>
      <div><p class="eyebrow">Receipt entry</p><h2>掃描發票</h2></div>
      <span class="step-badge">{{ receipt ? '確認紀錄' : '快速掃描' }}</span>
    </div>
    <p class="intro">{{ receipt ? '核對發票資料，再選擇連結既有紀錄或新增支出。' : '將左側 QR Code 放入框內，或從相簿選擇發票圖片。' }}</p>
    <template v-if="!receipt">
      <div class="scanner-stage" :class="{ active: camera }">
        <video v-show="camera" ref="video" muted playsinline aria-label="相機預覽"></video>
        <div v-if="!camera" class="scanner-placeholder"><Camera aria-hidden="true" /><span>對準發票左側 QR Code</span></div>
        <div class="scan-guide" aria-hidden="true"><i></i><i></i><i></i><i></i></div>
        <span v-if="camera" class="scan-hint" role="status">{{ scanHint || '保持穩定，等待辨識' }}</span>
      </div>
      <div class="scan-actions">
        <button v-if="!camera" class="primary-action" type="button" :disabled="busy" @click="startCamera"><Camera aria-hidden="true" />開啟相機</button>
        <button v-else type="button" :disabled="busy" @click="switchCamera"><Switch aria-hidden="true" />切換鏡頭</button>
        <button type="button" :disabled="busy" @click="$refs.imageFile.click()"><Picture aria-hidden="true" />選擇圖片</button>
      </div>
      <input ref="imageFile" class="image-file" type="file" aria-label="選擇發票圖片" accept="image/jpeg,image/png,image/webp" :disabled="busy" @change="scanImage" />
      <button v-if="camera" class="text-action" type="button" @click="stopCamera">關閉相機</button>
      <p class="privacy-note">圖片在裝置上解碼，不會上傳或保存。框線只輔助對準，不裁切掃描範圍。</p>
    </template>
    <template v-else>
      <dl class="receipt-details">
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
      <template v-else-if="receipt.status === 'pending'">
        <label class="merchant-field">店名（選填）<input v-model="merchant" placeholder="例如：全家、午餐店家" maxlength="255" :disabled="busy" /></label>
        <button type="button" :disabled="busy" @click="loadMatches">比對既有紀錄</button>
        <p>日期與金額相同也可能是不同消費，請自行確認。</p>
        <div v-for="candidate in candidates" :key="candidate.id" class="candidate">
          <span>{{ candidate.date }} · {{ candidate.merchant || candidate.title }} · {{ candidate.amount }} TWD</span>
          <small>{{ candidate.reasons.join('、') }}</small>
          <button type="button" :disabled="busy" @click="resolve('link', candidate.id)">連結這筆</button>
        </div>
        <p v-if="matched && !candidates.length">沒有找到符合日期與金額的既有紀錄。</p>
        <button v-if="!creating" class="primary-action" type="button" :disabled="busy" @click="creating = true">建立新交易</button>
        <TransactionForm v-if="creating" type="expense" :draft="draft" :external-submit="createTransaction" locked-receipt-fields @transaction-added="handleCreated" />
        <div class="secondary-actions"><button class="text-action" type="button" :disabled="busy" @click="resolve('ignore')">略過這張發票</button>
        <button class="text-action" type="button" :disabled="busy" @click="$emit('cancel')">稍後處理</button></div>
      </template>
      <router-link v-if="receipt.status === 'linked'" class="record-link" :to="`/transactions?type=expense&month=${receipt.issued_on.slice(0, 7)}`">查看紀錄</router-link>
      <button type="button" :disabled="busy" @click="reset">再掃一張</button>
    </template>
    <p v-if="busy" class="status-note" role="status">處理中…</p>
    <p v-if="error" class="error-note" role="alert">{{ error }}</p>
    <div class="secondary-actions"><button class="text-action" type="button" :disabled="busy" @click="$emit('manual')">改用手動記帳</button>
    <button class="text-action" type="button" :disabled="busy" @click="$emit('cancel')">返回輸入方式</button></div>
  </section>
</template>

<script>
import { BrowserQRCodeReader } from "@zxing/browser";
import apiClient from "@/api";
import TransactionForm from "@/components/budgets/TransactionForm.vue";
import AccountImpactCard from "@/components/shared/AccountImpactCard.vue";
import { Camera, Picture, Switch, Document } from "@element-plus/icons-vue";

export default {
  components: { TransactionForm, AccountImpactCard, Camera, Picture, Switch, Document },
  emits: ["manual", "cancel"],
  data() {
    return { receipt: null, merchant: "", candidates: [], matched: false, creating: false, busy: false, error: "", camera: false, controls: null, reader: null, generation: 0, resolvedReceipt: null, successImpact: null, createdHere: false, facingMode: 'environment', scanHint: '' };
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
      this.scanHint = "";
      this.camera = true;
      const generation = ++this.generation;
      try {
        await this.$nextTick();
        this.reader = new BrowserQRCodeReader();
        const controls = await this.reader.decodeFromConstraints(
          { video: { facingMode: { ideal: this.facingMode } }, audio: false },
          this.$refs.video,
          (result) => {
            if (result && !this.busy && !this.receipt && generation === this.generation) {
              const text = result.getText();
              // Right-side QR and unrelated QR should not stop the live scanner.
              if (!/^[A-Z]{2}\d{8}\d{7}/.test(text)) {
                this.scanHint = '請移到發票左側 QR Code';
                return;
              }
              this.importQr(text, "qr_camera");
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
    async switchCamera() {
      this.stopCamera();
      this.facingMode = this.facingMode === 'environment' ? 'user' : 'environment';
      await this.startCamera();
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
.receipt-flow { display: grid; gap: 16px; padding: 20px; color: var(--text-color); background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--card-radius); box-shadow: var(--surface-shadow); }
.receipt-heading { display: flex; align-items: center; gap: 12px; }
.receipt-symbol { display: grid; place-items: center; width: 44px; height: 44px; border-radius: 12px; color: var(--primary-color); background: var(--primary-soft); flex: none; }
.receipt-symbol svg { width: 24px; height: 24px; }
h2 { margin: 2px 0 0; font-size: 1.3rem; letter-spacing: -.03em; }
.eyebrow { color: var(--light-text-color); font-size: .7rem; font-weight: 800; text-transform: uppercase; letter-spacing: .07em; }
.step-badge { margin-left: auto; padding: 5px 8px; color: var(--primary-color); background: var(--primary-soft); border-radius: 8px; font-size: .7rem; font-weight: 700; white-space: nowrap; }
.intro, .privacy-note { color: var(--light-text-color); line-height: 1.6; font-size: .88rem; }
.privacy-note { font-size: .76rem; }
button, .record-link { display: inline-flex; justify-content: center; align-items: center; gap: 8px; min-height: 44px; padding: 10px 14px; border: 1px solid var(--border-color); border-radius: 10px; color: var(--text-color); background: var(--secondary-color); cursor: pointer; font-weight: 700; text-decoration: none; transition: background-color var(--motion-fast); }
button svg { width: 19px; height: 19px; flex: none; }
button.primary-action, .record-link { color: var(--on-primary); background: var(--primary-color); border-color: var(--primary-color); }
button.primary-action:hover { background: var(--primary-hover); }
button.text-action { color: var(--light-text-color); background: transparent; border-color: transparent; font-size: .8rem; padding: 8px 4px; }
button:focus-visible, input:focus-visible { outline: 3px solid var(--primary-color); outline-offset: 3px; }
button:disabled { opacity: .5; cursor: wait; }
input { width: 100%; min-width: 0; min-height: 44px; padding: 10px 12px; color: var(--text-color); background: var(--page-bg); border: 1px solid var(--border-color); border-radius: 10px; }
.image-file { display: none; }
.merchant-field { display: grid; gap: 8px; font-size: .85rem; font-weight: 700; }
.scanner-stage { position: relative; display: grid; place-items: center; min-height: 268px; border-radius: 14px; overflow: hidden; background: var(--page-bg); border: 1px solid var(--border-color); }
.scanner-stage.active { background: #101216; }
video { display: block; width: 100%; height: 300px; object-fit: contain; }
.scanner-placeholder { display: grid; justify-items: center; gap: 12px; color: var(--light-text-color); font-size: .8rem; }
.scanner-placeholder svg { width: 36px; height: 36px; color: var(--primary-color); }
.scan-guide { position: absolute; width: 190px; height: 190px; top: 50%; left: 50%; transform: translate(-50%, -50%); pointer-events: none; }
.scan-guide i { position: absolute; width: 28px; height: 28px; border: 3px solid var(--primary-color); }
.scan-guide i:nth-child(1) { top: 0; left: 0; border-right: 0; border-bottom: 0; border-radius: 12px 0 0; }
.scan-guide i:nth-child(2) { top: 0; right: 0; border-left: 0; border-bottom: 0; border-radius: 0 12px 0 0; }
.scan-guide i:nth-child(3) { bottom: 0; left: 0; border-right: 0; border-top: 0; border-radius: 0 0 0 12px; }
.scan-guide i:nth-child(4) { bottom: 0; right: 0; border-left: 0; border-top: 0; border-radius: 0 0 12px; }
.scan-hint { position: absolute; bottom: 12px; padding: 6px 10px; color: #fff; background: rgba(0,0,0,.72); border-radius: 8px; font-size: .78rem; }
.scan-actions, .secondary-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.receipt-details { margin: 0; display: grid; grid-template-columns: 1fr 1fr; gap: 12px; padding: 16px; background: var(--page-bg); border: 1px solid var(--border-color); border-radius: 12px; }
.receipt-details div { display: grid; gap: 5px; min-width: 0; } dt { color: var(--light-text-color); font-size: .75rem; } dd { margin: 0; overflow-wrap: anywhere; font-weight: 750; }
.candidate { display: grid; gap: 8px; padding: 14px; border: 1px solid var(--brand-border); border-radius: 12px; background: var(--primary-soft); }
.status-note, .error-note { padding: 12px; border-radius: 10px; font-size: .85rem; }
.status-note { color: var(--primary-color); background: var(--primary-soft); }
.error-note { color: var(--expense-color); background: var(--expense-soft); }
p { margin: 0; } small { color: var(--light-text-color); }
</style>
