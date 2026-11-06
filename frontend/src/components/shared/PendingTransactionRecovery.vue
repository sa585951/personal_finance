<template>
  <section class="pending-transaction app-card" role="status" :aria-label="panelLabel">
    <h3>{{ heading }}</h3>
    <p>{{ explanation }}</p>
    <dl v-if="details">
      <div v-for="detail in details" :key="detail.label"><dt>{{ detail.label }}</dt><dd>{{ detail.value }}</dd></div>
    </dl>
    <dl v-else>
      <div><dt>項目</dt><dd>{{ payload.item }}</dd></div>
      <div><dt>日期</dt><dd>{{ payload.date }}</dd></div>
      <div><dt>金額</dt><dd>{{ payload.amount }} {{ payload.original_currency || '依原提交幣別' }}</dd></div>
      <div><dt>類別</dt><dd>{{ payload.budget_category }}</dd></div>
    </dl>
    <p v-if="message">{{ message }}</p>
    <p v-if="transactionId">既有交易 ID：{{ transactionId }}</p>
    <button type="button" class="app-button" :disabled="busy" @click="$emit('retry')">{{ busy ? '核對中' : '以原資料重試' }}</button>
    <template v-if="transactionId">
      <p>請先核對既有紀錄。結束此請求只清除本機待確認狀態，不會新增、修改或刪除交易。</p>
      <label><input v-model="acknowledged" type="checkbox" :disabled="busy" />我已核對既有紀錄</label>
      <button type="button" class="app-button" :disabled="busy || !acknowledged" @click="$emit('acknowledge')">結束這次待確認請求</button>
    </template>
  </section>
</template>

<script>
export default {
  name: 'PendingTransactionRecovery',
  props: {
    payload: { type: Object, required: true },
    message: { type: String, default: '' },
    panelLabel: { type: String, default: '待確認交易' },
    heading: { type: String, default: '上一筆交易結果尚未確認' },
    explanation: { type: String, default: '已保留原始資料，請勿另外建立相同交易。' },
    details: { type: Array, default: null },
    transactionId: { type: String, default: '' },
    busy: { type: Boolean, default: false },
  },
  emits: ['retry', 'acknowledge'],
  data() { return { acknowledged: false }; },
  watch: { transactionId() { this.acknowledged = false; } },
};
</script>

<style scoped>
.pending-transaction { padding: 16px; overflow-wrap: anywhere; }
.pending-transaction h3 { margin-block-start: 0; }
.pending-transaction dl div { display: flex; gap: 12px; margin-block: 8px; }
.pending-transaction dt { flex: 0 0 3em; white-space: nowrap; }
.pending-transaction dd { min-width: 0; margin: 0; }
.pending-transaction label { display: block; margin-block: 12px; }
</style>
