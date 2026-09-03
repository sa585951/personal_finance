<template>
  <fieldset class="appearance-picker">
    <legend>帳戶外觀</legend>

    <button
      type="button"
      class="appearance-trigger"
      :class="{ open: isOpen }"
      :aria-expanded="isOpen"
      @click="isOpen = !isOpen"
      @keydown.esc="isOpen = false"
    >
      <AccountIcon
        :icon-key="iconKey"
        :color-key="colorKey"
        :label="selectedIconLabel"
        size="large"
      />
      <span class="appearance-summary">
        <strong>已選外觀</strong>
        <span>{{ selectedIconLabel }} · {{ selectedColorLabel }}</span>
      </span>
      <ArrowDown class="trigger-arrow" />
    </button>

    <div v-if="isOpen" class="appearance-panel">
      <div class="picker-group">
        <span>圖示</span>
        <div class="icon-options" aria-label="選擇帳戶圖示">
          <button
            v-for="option in iconOptions"
            :key="option.value"
            type="button"
            :class="{ selected: option.value === iconKey }"
            :aria-label="`選擇${option.label}圖示`"
            :aria-pressed="option.value === iconKey"
            :title="option.label"
            @click="$emit('update:iconKey', option.value)"
          >
            <AccountIcon
              :icon-key="option.value"
              :color-key="colorKey"
              :label="option.label"
              size="small"
            />
          </button>
        </div>
      </div>

      <div class="picker-group">
        <span>顏色</span>
        <div class="color-options" aria-label="選擇帳戶顏色">
          <button
            v-for="option in colorOptions"
            :key="option.value"
            type="button"
            class="color-swatch"
            :class="[`swatch-${option.value}`, { selected: option.value === colorKey }]"
            :aria-label="option.label"
            :aria-pressed="option.value === colorKey"
            :title="option.label"
            @click="$emit('update:colorKey', option.value)"
          ></button>
        </div>
      </div>

      <div class="panel-footer">
        <p class="appearance-hint">只用於辨識，不影響帳戶類型或統計。</p>
        <button type="button" class="done-button" @click="isOpen = false">完成</button>
      </div>
    </div>
  </fieldset>
</template>

<script>
import { ArrowDown } from "@element-plus/icons-vue";
import AccountIcon from "./AccountIcon.vue";
import {
  ACCOUNT_COLOR_OPTIONS,
  ACCOUNT_ICON_OPTIONS,
} from "@/constants/accountAppearance";

export default {
  name: "AccountAppearancePicker",
  components: { AccountIcon, ArrowDown },
  props: {
    iconKey: {
      type: String,
      required: true,
    },
    colorKey: {
      type: String,
      required: true,
    },
  },
  emits: ["update:iconKey", "update:colorKey"],
  data() {
    return {
      iconOptions: ACCOUNT_ICON_OPTIONS,
      colorOptions: ACCOUNT_COLOR_OPTIONS,
      isOpen: false,
    };
  },
  computed: {
    selectedIconLabel() {
      return this.iconOptions.find((item) => item.value === this.iconKey)?.label || "其他";
    },
    selectedColorLabel() {
      return this.colorOptions.find((item) => item.value === this.colorKey)?.label || "灰藍";
    },
  },
};
</script>

<style scoped>
.appearance-picker {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 12px;
  border: 1px solid #dbe4ee;
  border-radius: 8px;
  background: #f8fafc;
}

.appearance-picker legend,
.picker-group > span {
  color: #475569;
  font-size: 0.86rem;
  font-weight: 800;
}

.appearance-trigger {
  display: flex;
  align-items: center;
  width: 100%;
  min-height: 64px;
  gap: 10px;
  padding: 8px;
  color: #0f172a;
  text-align: left;
  background: #ffffff;
  border: 1px solid #dbe4ee;
  border-radius: 8px;
  box-shadow: none;
}

.appearance-trigger:hover,
.appearance-trigger.open {
  border-color: #0f766e;
  background: #f0fdfa;
}

.appearance-summary {
  display: grid;
  flex: 1;
  gap: 2px;
}

.appearance-summary > span {
  color: #64748b;
  font-size: 0.8rem;
}

.trigger-arrow {
  width: 18px;
  height: 18px;
  color: #64748b;
  transition: transform 0.2s ease;
}

.appearance-trigger.open .trigger-arrow {
  transform: rotate(180deg);
}

.appearance-panel {
  display: grid;
  gap: 12px;
  padding: 12px;
  border: 1px solid #dbe4ee;
  border-radius: 8px;
  background: #ffffff;
}

.picker-group {
  display: grid;
  gap: 7px;
}

.icon-options {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 7px;
}

.icon-options button {
  display: grid;
  aspect-ratio: 1;
  min-width: 0;
  min-height: 48px;
  padding: 6px;
  place-items: center;
  color: #475569;
  background: #ffffff;
  border: 1px solid #dbe4ee;
  border-radius: 8px;
  box-shadow: none;
}

.icon-options button.selected {
  border-color: #0f766e;
  box-shadow: 0 0 0 2px rgba(15, 118, 110, 0.12);
}

.color-options {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
}

.color-swatch {
  width: 30px;
  min-height: 30px;
  padding: 0;
  background: var(--swatch);
  border: 3px solid #ffffff;
  border-radius: 50%;
  box-shadow: 0 0 0 1px #cbd5e1;
}

.color-swatch.selected {
  box-shadow: 0 0 0 3px #0f172a;
}

.swatch-teal { --swatch: #0f766e; }
.swatch-blue { --swatch: #2563eb; }
.swatch-green { --swatch: #16a34a; }
.swatch-amber { --swatch: #d97706; }
.swatch-rose { --swatch: #e11d48; }
.swatch-purple { --swatch: #9333ea; }
.swatch-slate { --swatch: #64748b; }

.appearance-hint {
  margin: 0;
  color: #64748b;
  font-size: 0.78rem;
  line-height: 1.45;
}

.panel-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-top: 2px;
}

.done-button {
  flex: 0 0 auto;
  min-height: 36px;
  padding: 6px 14px;
  color: #ffffff;
  background: #0f766e;
  border: 0;
  border-radius: 8px;
  box-shadow: none;
  font-size: 0.82rem;
  font-weight: 800;
}

@media (max-width: 390px) {
  .icon-options {
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }
}
</style>
