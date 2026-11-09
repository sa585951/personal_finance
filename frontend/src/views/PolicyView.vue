<template>
  <div class="policy-page">
    <button type="button" class="back" @click="goBack">返回</button>
    <h1>{{ title }}</h1>
    <p class="meta">生效日期：{{ effectiveDate }} · 營運者：{{ operator }}</p>
    <section v-for="section in sections" :key="section.title">
      <h2>{{ section.title }}</h2>
      <ul>
        <li v-for="item in section.items" :key="item">{{ item }}</li>
      </ul>
    </section>
    <p class="meta">
      <router-link v-if="kind === 'privacy'" to="/terms">服務條款</router-link>
      <router-link v-else to="/privacy">隱私權政策</router-link>
    </p>
  </div>
</template>

<script>
import { CONTACT, EFFECTIVE_DATE, OPERATOR, privacySections, termsSections } from "@/constants/policies";

export default {
  name: "PolicyView",
  props: { kind: { type: String, required: true } },
  data() {
    return { effectiveDate: EFFECTIVE_DATE, operator: OPERATOR, contact: CONTACT };
  },
  computed: {
    title() {
      return this.kind === "privacy" ? "隱私權政策" : "服務條款";
    },
    sections() {
      return this.kind === "privacy" ? privacySections : termsSections;
    },
  },
  methods: {
    goBack() {
      if (window.history.length > 1) this.$router.back();
      else this.$router.push("/");
    },
  },
};
</script>

<style scoped>
.policy-page {
  max-width: 680px;
  margin: 0 auto;
  padding: 24px 16px 48px;
  color: var(--text-color);
  line-height: 1.7;
}

.back {
  min-height: 40px;
  padding: 0;
  color: var(--light-text-color);
  background: transparent;
  border: 0;
  font-weight: 600;
}

h1 {
  margin: 8px 0 4px;
  font-size: 1.6rem;
}

h2 {
  margin: 24px 0 6px;
  font-size: 1.05rem;
}

ul {
  margin: 0;
  padding-left: 1.2em;
}

li + li {
  margin-top: 4px;
}

.meta {
  margin: 0;
  color: var(--light-text-color);
  font-size: 0.88rem;
}

.meta a {
  color: var(--text-color);
}
</style>
