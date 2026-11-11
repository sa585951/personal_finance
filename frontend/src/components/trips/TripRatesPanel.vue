<template>
  <section class="trip-rates" aria-label="旅行匯率">
    <div class="rates-head">
      <strong>旅行匯率</strong>
      <small>
        整趟旅行共用，新增外幣支出時自動帶入。這是參考匯率，實際以信用卡帳單為準。
      </small>
    </div>

    <p v-if="!isOwner" class="rates-note">只有旅行擁有者可以修改匯率。</p>
    <p v-if="rates.locked" class="rates-note">
      這趟旅行已經有還款紀錄，已記的支出不能再改動匯率；之後新增的支出仍會使用新匯率。
    </p>

    <ul class="rate-list">
      <li v-for="row in visibleRows" :key="row.currency" class="rate-row">
        <div class="rate-main">
          <strong>1 {{ row.currency }} = {{ row.rate || row.default_rate || "—" }} {{ rates.base_currency }}</strong>
          <small v-if="row.rate">
            旅行匯率<template v-if="row.updated_by_name">，{{ row.updated_by_name }} 設定</template>
            <template v-if="row.recorded_expenses"> · 已記 {{ row.recorded_expenses }} 筆</template>
          </small>
          <small v-else>
            尚未設定，目前用參考匯率
            <template v-if="row.recorded_expenses"> · 已記 {{ row.recorded_expenses }} 筆</template>
          </small>
        </div>
        <div v-if="isOwner" class="rate-actions">
          <button type="button" class="rate-action" :disabled="busy" @click="$emit('set-rate', row)">
            {{ row.rate ? "修改" : "設定" }}
          </button>
          <button
            v-if="row.rate && row.recorded_expenses"
            type="button"
            class="rate-action"
            :disabled="busy || rates.locked"
            @click="$emit('apply-rate', row)"
          >
            套用到已記的支出
          </button>
        </div>
      </li>
    </ul>

    <label v-if="isOwner && otherRows.length" class="rate-add">
      <span>新增其他幣別</span>
      <select :disabled="busy" @change="addCurrency($event)">
        <option value="">選擇幣別</option>
        <option v-for="row in otherRows" :key="row.currency" :value="row.currency">{{ row.currency }}</option>
      </select>
    </label>

    <details v-if="rates.history.length" class="rate-history">
      <summary>變更紀錄</summary>
      <ul>
        <li v-for="(item, index) in rates.history" :key="index">
          {{ formatTime(item.changed_at) }} · {{ item.changed_by_name || "已刪除的使用者" }}
          <template v-if="item.action === 'apply'">
            把 {{ item.currency }} 匯率 {{ item.new_rate }} 套用到 {{ item.affected_count }} 筆已記的支出
          </template>
          <template v-else>
            將 {{ item.currency }} 匯率{{ item.old_rate ? `由 ${item.old_rate} ` : "" }}設為 {{ item.new_rate }}
          </template>
        </li>
      </ul>
    </details>
  </section>
</template>

<script>
export default {
  name: "TripRatesPanel",
  props: {
    rates: { type: Object, required: true },
    isOwner: { type: Boolean, default: false },
    defaultCurrency: { type: String, default: "" },
    busy: { type: Boolean, default: false },
  },
  emits: ["set-rate", "apply-rate"],
  computed: {
    // Currencies in play come first; the owner can add any other supported one on demand.
    visibleRows() {
      return this.rates.rates.filter((row) => row.rate || row.recorded_expenses || row.currency === this.defaultCurrency);
    },
    otherRows() {
      return this.rates.rates.filter((row) => !this.visibleRows.includes(row));
    },
  },
  methods: {
    addCurrency(event) {
      const row = this.rates.rates.find((item) => item.currency === event.target.value);
      event.target.value = "";
      if (row) this.$emit("set-rate", row);
    },
    formatTime(value) {
      const date = new Date(value);
      return Number.isNaN(date.getTime()) ? "" : date.toLocaleString("zh-TW", { hour12: false });
    },
  },
};
</script>

<style scoped>
.trip-rates {
  display: grid;
  gap: 10px;
  padding: 14px 0;
  border-top: 1px solid var(--border-color);
}

.rates-head {
  display: grid;
  gap: 2px;
}

.rates-head small,
.rates-note,
.rate-main small,
.rate-history {
  color: var(--light-text-color);
  font-size: 0.84rem;
  line-height: 1.5;
}

.rates-note {
  margin: 0;
}

.rate-list {
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.rate-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-color);
}

.rate-main {
  display: grid;
  gap: 2px;
}

.rate-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 14px;
}

.rate-action {
  min-height: 36px;
  padding: 0 2px;
  border: 0;
  color: var(--primary-color);
  background: transparent;
  box-shadow: none;
  font-weight: 700;
}

.rate-action:hover {
  transform: none;
  box-shadow: none;
  text-decoration: underline;
}

.rate-add {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.9rem;
}

.rate-add select {
  min-height: 38px;
  padding: 0 10px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: var(--card-bg);
}

.rate-history ul {
  margin: 6px 0 0;
  padding-left: 18px;
}
</style>
