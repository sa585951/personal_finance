export const ACCOUNT_ICON_OPTIONS = [
  { value: "bank", label: "建築" },
  { value: "wallet", label: "錢包" },
  { value: "card", label: "卡片" },
  { value: "investment", label: "折線" },
  { value: "savings", label: "硬幣" },
  { value: "deposit", label: "收藏冊" },
  { value: "digital", label: "手機" },
  { value: "external", label: "連結" },
  { value: "other", label: "收納盒" },
];

export const ACCOUNT_COLOR_OPTIONS = [
  { value: "teal", label: "青綠" },
  { value: "blue", label: "藍色" },
  { value: "green", label: "綠色" },
  { value: "amber", label: "金色" },
  { value: "rose", label: "玫紅" },
  { value: "purple", label: "紫色" },
  { value: "slate", label: "灰藍" },
];

const TYPE_DEFAULTS = {
  bank: { iconKey: "bank", colorKey: "blue" },
  cash: { iconKey: "wallet", colorKey: "green" },
  credit_card: { iconKey: "card", colorKey: "rose" },
  e_wallet: { iconKey: "digital", colorKey: "purple" },
  prepaid_card: { iconKey: "card", colorKey: "amber" },
  external: { iconKey: "external", colorKey: "slate" },
  investment: { iconKey: "investment", colorKey: "teal" },
  other: { iconKey: "other", colorKey: "slate" },
};

export function defaultAccountAppearance(accountType) {
  return TYPE_DEFAULTS[accountType] || TYPE_DEFAULTS.other;
}
