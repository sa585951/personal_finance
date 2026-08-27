<template>
  <fieldset class="appearance-picker">
    <legend>帳戶外觀</legend>

    <div class="appearance-preview">
      <AccountIcon
        :icon-key="iconKey"
        :color-key="colorKey"
        :label="selectedIconLabel"
        size="large"
      />
      <div>
        <strong>{{ selectedIconLabel }}</strong>
        <span>{{ selectedColorLabel }}</span>
      </div>
    </div>

    <div class="picker-group">
      <span>圖示</span>
      <div class="icon-options" aria-label="選擇帳戶圖示">
        <button
          v-for="option in iconOptions"
          :key="option.value"
          type="button"
          :class="{ selected: option.value === iconKey }"
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
          <small>{{ option.label }}</small>
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
  </fieldset>
</template>

<script>
import AccountIcon from "./AccountIcon.vue";
import {
  ACCOUNT_COLOR_OPTIONS,
  ACCOUNT_ICON_OPTIONS,
} from "@/constants/accountAppearance";

export default {
  name: "AccountAppearancePicker",
  components: { AccountIcon },
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
  gap: 12px;
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

.appearance-preview {
  display: flex;
  align-items: center;
  gap: 10px;
}

.appearance-preview > div {
  display: grid;
  gap: 2px;
}

.appearance-preview span {
  color: #64748b;
  font-size: 0.8rem;
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
  min-width: 0;
  min-height: 62px;
  padding: 6px 3px;
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

.icon-options small {
  max-width: 100%;
  overflow: hidden;
  font-size: 0.68rem;
  text-overflow: ellipsis;
  white-space: nowrap;
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

@media (max-width: 390px) {
  .icon-options {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>
