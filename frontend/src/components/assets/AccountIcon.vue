<template>
  <span
    class="account-icon"
    :class="[`color-${resolvedColor}`, `size-${size}`]"
    role="img"
    :aria-label="label"
  >
    <component :is="iconComponent" />
  </span>
</template>

<script>
import {
  Box,
  Cellphone,
  Coin,
  Collection,
  CreditCard,
  Link,
  Money,
  OfficeBuilding,
  TrendCharts,
  Wallet,
} from "@element-plus/icons-vue";

const ICON_COMPONENTS = {
  bank: OfficeBuilding,
  wallet: Wallet,
  card: CreditCard,
  investment: TrendCharts,
  savings: Coin,
  deposit: Collection,
  digital: Cellphone,
  external: Link,
  other: Box,
};

const COLOR_KEYS = new Set(["teal", "blue", "green", "amber", "rose", "purple", "slate"]);

export default {
  name: "AccountIcon",
  props: {
    iconKey: {
      type: String,
      default: "other",
    },
    colorKey: {
      type: String,
      default: "slate",
    },
    label: {
      type: String,
      default: "帳戶",
    },
    size: {
      type: String,
      default: "medium",
      validator: (value) => ["small", "medium", "large"].includes(value),
    },
  },
  computed: {
    iconComponent() {
      return ICON_COMPONENTS[this.iconKey] || Money;
    },
    resolvedColor() {
      return COLOR_KEYS.has(this.colorKey) ? this.colorKey : "slate";
    },
  },
};
</script>

<style scoped>
.account-icon {
  display: inline-grid;
  flex: 0 0 auto;
  place-items: center;
  color: var(--icon-fg);
  background: var(--icon-bg);
  border: 1px solid color-mix(in srgb, var(--icon-fg) 22%, transparent);
  border-radius: 8px;
}

.account-icon svg {
  width: 54%;
  height: 54%;
}

.size-small {
  width: 30px;
  height: 30px;
}

.size-medium {
  width: 40px;
  height: 40px;
}

.size-large {
  width: 48px;
  height: 48px;
}

.color-teal { --icon-fg: #0f766e; --icon-bg: #ccfbf1; }
.color-blue { --icon-fg: #1d4ed8; --icon-bg: #dbeafe; }
.color-green { --icon-fg: #15803d; --icon-bg: #dcfce7; }
.color-amber { --icon-fg: #b45309; --icon-bg: #fef3c7; }
.color-rose { --icon-fg: #be123c; --icon-bg: #ffe4e6; }
.color-purple { --icon-fg: #7e22ce; --icon-bg: #f3e8ff; }
.color-slate { --icon-fg: #475569; --icon-bg: #e2e8f0; }
</style>
