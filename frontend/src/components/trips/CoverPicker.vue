<template>
  <fieldset class="cover-picker">
    <legend>{{ label }}</legend>
    <div class="swatches" role="radiogroup" :aria-label="label">
      <button
        v-for="cover in covers"
        :key="cover.key"
        type="button"
        role="radio"
        class="swatch"
        :aria-checked="modelValue === cover.key"
        :aria-label="cover.label"
        :title="cover.label"
        :class="{ selected: modelValue === cover.key }"
        :style="{ background: cover.color }"
        :disabled="disabled"
        @click="$emit('update:modelValue', cover.key)"
      >
        <Check v-if="modelValue === cover.key" aria-hidden="true" />
      </button>
    </div>
  </fieldset>
</template>

<script>
import { Check } from "@element-plus/icons-vue";
import { TRIP_COVERS } from "@/constants/tripCovers";

export default {
  name: "CoverPicker",
  components: { Check },
  props: {
    modelValue: { type: String, default: "" },
    label: { type: String, default: "封面" },
    disabled: { type: Boolean, default: false },
  },
  emits: ["update:modelValue"],
  data() {
    return { covers: TRIP_COVERS };
  },
};
</script>

<style scoped>
.cover-picker {
  margin: 0;
  padding: 0;
  border: 0;
}

legend {
  margin-bottom: 8px;
  color: var(--text-color);
  font-weight: 600;
}

.swatches {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.swatch {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  min-height: 40px;
  padding: 0;
  border: 2px solid transparent;
  border-radius: 50%;
  color: #ffffff;
}

.swatch.selected {
  border-color: var(--text-color);
  box-shadow: inset 0 0 0 2px var(--card-bg);
}

.swatch svg {
  width: 18px;
  height: 18px;
}
</style>
