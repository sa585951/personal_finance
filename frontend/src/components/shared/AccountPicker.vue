<template>
  <div ref="picker" class="account-picker" :class="{ disabled }">
    <span class="picker-label">{{ label }}</span>
    <button
      type="button"
      class="picker-trigger"
      :aria-expanded="isOpen"
      :aria-label="`${label}：${selectedAccount ? accountName(selectedAccount) : noneLabel}`"
      :disabled="disabled"
      @click="togglePicker"
      @keydown.esc="closePicker"
    >
      <AccountIcon
        v-if="selectedAccount"
        :icon-key="accountIconKey(selectedAccount)"
        :color-key="accountColorKey(selectedAccount)"
        :label="`${accountName(selectedAccount)}圖示`"
        size="small"
      />
      <span v-else class="empty-icon" aria-hidden="true">−</span>
      <span class="trigger-copy">
        <strong>{{ selectedAccount ? accountName(selectedAccount) : noneLabel }}</strong>
        <small v-if="selectedAccount">{{ accountMeta(selectedAccount) }}</small>
        <small v-else>{{ placeholder }}</small>
      </span>
      <ArrowDown class="trigger-arrow" aria-hidden="true" />
    </button>

    <div v-if="isOpen" class="picker-panel">
      <label class="search-field">
        <span class="sr-only">搜尋{{ label }}</span>
        <Search aria-hidden="true" />
        <input
          ref="searchInput"
          v-model.trim="searchText"
          type="search"
          :placeholder="searchPlaceholder"
          @keydown.esc="closePicker"
        />
      </label>

      <div class="account-options" role="listbox" :aria-label="label">
        <button
          v-if="allowNone"
          type="button"
          class="account-option none-option"
          :class="{ selected: !modelValue }"
          role="option"
          :aria-selected="!modelValue"
          @click="selectAccount('')"
        >
          <span class="empty-icon" aria-hidden="true">−</span>
          <span>
            <strong>{{ noneLabel }}</strong>
            <small>不異動任何帳戶餘額</small>
          </span>
          <Check v-if="!modelValue" aria-hidden="true" />
        </button>

        <section v-for="group in groupedAccounts" :key="group.type" class="account-group">
          <h4>{{ group.label }}</h4>
          <button
            v-for="account in group.accounts"
            :key="accountId(account)"
            type="button"
            class="account-option"
            :class="{ selected: accountId(account) === modelValue }"
            role="option"
            :aria-selected="accountId(account) === modelValue"
            @click="selectAccount(accountId(account))"
          >
            <AccountIcon
              :icon-key="accountIconKey(account)"
              :color-key="accountColorKey(account)"
              :label="`${accountName(account)}圖示`"
              size="small"
            />
            <span>
              <strong>{{ accountName(account) }}</strong>
              <small>{{ accountMeta(account) }}</small>
            </span>
            <Check v-if="accountId(account) === modelValue" aria-hidden="true" />
          </button>
        </section>

        <p v-if="!filteredAccounts.length" class="empty-state">找不到符合條件的帳戶。</p>
      </div>
    </div>
  </div>
</template>

<script>
import { ArrowDown, Check, Search } from "@element-plus/icons-vue";
import AccountIcon from "@/components/assets/AccountIcon.vue";
import { defaultAccountAppearance } from "@/constants/accountAppearance";

const ACCOUNT_TYPE_LABELS = {
  bank: "銀行",
  cash: "現金",
  credit_card: "信用卡",
  e_wallet: "電子錢包",
  prepaid_card: "預付卡",
  investment: "投資",
  external: "外部帳戶",
  other: "其他",
};

const ACCOUNT_TYPE_ORDER = Object.keys(ACCOUNT_TYPE_LABELS);

export default {
  name: "AccountPicker",
  components: { AccountIcon, ArrowDown, Check, Search },
  props: {
    modelValue: { type: String, default: "" },
    accounts: { type: Array, default: () => [] },
    label: { type: String, default: "帳戶" },
    placeholder: { type: String, default: "點擊選擇帳戶" },
    searchPlaceholder: { type: String, default: "搜尋名稱、類型或幣別" },
    noneLabel: { type: String, default: "不連動帳戶" },
    allowNone: { type: Boolean, default: true },
    disabled: { type: Boolean, default: false },
  },
  emits: ["update:modelValue"],
  data() {
    return {
      isOpen: false,
      searchText: "",
    };
  },
  computed: {
    selectedAccount() {
      return this.accounts.find((account) => this.accountId(account) === this.modelValue) || null;
    },
    filteredAccounts() {
      const keyword = this.searchText.toLocaleLowerCase("zh-TW");
      return this.accounts
        .filter((account) => {
          if (!keyword) return true;
          return [
            this.accountName(account),
            this.accountTypeLabel(account),
            account.currency,
          ].join(" ").toLocaleLowerCase("zh-TW").includes(keyword);
        })
        .sort((left, right) => {
          const typeDifference = this.accountTypeOrder(left) - this.accountTypeOrder(right);
          if (typeDifference !== 0) return typeDifference;
          return this.accountName(left).localeCompare(this.accountName(right), "zh-TW");
        });
    },
    groupedAccounts() {
      const groups = [];
      for (const account of this.filteredAccounts) {
        const type = this.accountType(account);
        let group = groups.find((item) => item.type === type);
        if (!group) {
          group = { type, label: ACCOUNT_TYPE_LABELS[type] || "其他", accounts: [] };
          groups.push(group);
        }
        group.accounts.push(account);
      }
      return groups;
    },
  },
  mounted() {
    document.addEventListener("pointerdown", this.handleOutsideClick);
  },
  beforeUnmount() {
    document.removeEventListener("pointerdown", this.handleOutsideClick);
  },
  methods: {
    accountId(account) {
      return String(account?.id || account?.account_key || account?.key || "");
    },
    accountName(account) {
      return account?.bank_name || account?.bankName || account?.name || "未命名帳戶";
    },
    accountType(account) {
      return account?.account_type || account?.type || "other";
    },
    accountTypeLabel(account) {
      return ACCOUNT_TYPE_LABELS[this.accountType(account)] || "其他";
    },
    accountTypeOrder(account) {
      const index = ACCOUNT_TYPE_ORDER.indexOf(this.accountType(account));
      return index === -1 ? ACCOUNT_TYPE_ORDER.length : index;
    },
    accountMeta(account) {
      const currency = account?.currency || "TWD";
      const type = this.accountTypeLabel(account);
      if (account?.track_balance === false) return `${type} · ${currency} · 未追蹤餘額`;
      const balance = Number(account?.balance || 0).toLocaleString("zh-TW", {
        maximumFractionDigits: ["TWD", "JPY", "KRW"].includes(currency) ? 0 : 2,
      });
      return `${type} · ${currency} ${balance}`;
    },
    accountIconKey(account) {
      return account?.icon_key || defaultAccountAppearance(this.accountType(account)).iconKey;
    },
    accountColorKey(account) {
      return account?.color_key || defaultAccountAppearance(this.accountType(account)).colorKey;
    },
    togglePicker() {
      if (this.disabled) return;
      this.isOpen ? this.closePicker() : this.openPicker();
    },
    openPicker() {
      this.isOpen = true;
      this.$nextTick(() => this.$refs.searchInput?.focus());
    },
    closePicker() {
      this.isOpen = false;
      this.searchText = "";
    },
    selectAccount(accountId) {
      this.$emit("update:modelValue", accountId);
      this.closePicker();
    },
    handleOutsideClick(event) {
      if (this.isOpen && !this.$refs.picker?.contains(event.target)) {
        this.closePicker();
      }
    },
  },
};
</script>

<style scoped>
.account-picker {
  position: relative;
  display: grid;
  gap: 6px;
  min-width: 0;
  color: #475569;
  font-weight: 700;
}

.picker-label {
  font-size: 0.9rem;
}

.picker-trigger,
.account-option {
  display: flex;
  align-items: center;
  width: 100%;
  color: #0f172a;
  text-align: left;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  box-shadow: none;
}

.picker-trigger {
  min-height: 52px;
  gap: 10px;
  padding: 6px 10px;
}

.picker-trigger:hover,
.picker-trigger[aria-expanded="true"] {
  border-color: #0f766e;
  background: #f0fdfa;
}

.account-picker.disabled {
  opacity: 0.58;
}

.trigger-copy,
.account-option > span:nth-child(2) {
  display: grid;
  flex: 1;
  min-width: 0;
  gap: 2px;
}

.trigger-copy strong,
.account-option strong {
  overflow: hidden;
  font-size: 0.9rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.trigger-copy small,
.account-option small {
  overflow: hidden;
  color: #64748b;
  font-size: 0.72rem;
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-icon {
  display: inline-grid;
  flex: 0 0 auto;
  width: 30px;
  height: 30px;
  place-items: center;
  color: #64748b;
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
}

.trigger-arrow {
  flex: 0 0 auto;
  width: 17px;
  height: 17px;
  color: #64748b;
  transition: transform 0.2s ease;
}

.picker-trigger[aria-expanded="true"] .trigger-arrow {
  transform: rotate(180deg);
}

.picker-panel {
  position: absolute;
  z-index: 40;
  top: calc(100% + 6px);
  left: 0;
  display: grid;
  width: 100%;
  max-height: min(420px, 58vh);
  gap: 8px;
  padding: 10px;
  overflow: hidden;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  box-shadow: 0 14px 32px rgba(15, 23, 42, 0.16);
}

.search-field {
  display: flex;
  align-items: center;
  min-height: 42px;
  gap: 8px;
  padding: 0 10px;
  background: #f8fafc;
  border: 1px solid #dbe4ee;
  border-radius: 8px;
}

.search-field svg {
  width: 17px;
  height: 17px;
  color: #64748b;
}

.search-field input {
  width: 100%;
  min-width: 0;
  min-height: 38px;
  padding: 0;
  font: inherit;
  background: transparent;
  border: 0;
  outline: 0;
}

.account-options {
  display: grid;
  gap: 8px;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.account-group {
  display: grid;
  gap: 5px;
}

.account-group h4 {
  margin: 4px 4px 1px;
  color: #64748b;
  font-size: 0.72rem;
  letter-spacing: 0;
}

.account-option {
  min-height: 48px;
  gap: 9px;
  padding: 7px 9px;
}

.account-option:hover,
.account-option.selected {
  border-color: #5eead4;
  background: #f0fdfa;
}

.account-option > svg {
  flex: 0 0 auto;
  width: 18px;
  height: 18px;
  color: #0f766e;
}

.empty-state {
  margin: 0;
  padding: 18px 8px;
  color: #64748b;
  text-align: center;
  font-size: 0.84rem;
  font-weight: 500;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@media (max-width: 480px) {
  .picker-panel {
    max-height: min(390px, 54vh);
  }
}
</style>
