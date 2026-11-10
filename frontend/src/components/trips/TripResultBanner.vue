<template>
  <button type="button" class="result-banner" :class="result.tone" @click="$emit('open-split')">
    <span class="result-copy">
      <small>目前結算</small>
      <strong>{{ result.headline }}</strong>
      <span>{{ result.detail }}</span>
    </span>
    <ArrowRight aria-hidden="true" />
  </button>
</template>

<script>
import { ArrowRight } from "@element-plus/icons-vue";

export default {
  name: "TripResultBanner",
  components: { ArrowRight },
  props: { result: { type: Object, required: true } },
  emits: ["open-split"],
};
</script>

<style scoped>
.result-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  padding: 14px 16px;
  border: 1px solid var(--border-color);
  border-radius: 14px;
  color: var(--text-color);
  background: var(--card-bg);
  text-align: left;
}

.result-copy {
  display: grid;
  gap: 2px;
}

.result-copy small,
.result-copy span {
  color: var(--light-text-color);
  font-size: 0.82rem;
}

.result-copy strong {
  font-size: 1.2rem;
  line-height: 1.35;
}

.owed strong {
  color: var(--income-color);
}

.owing strong {
  color: var(--expense-color);
}

.result-banner svg {
  flex: none;
  width: 16px;
  height: 16px;
  color: var(--light-text-color);
}
</style>
