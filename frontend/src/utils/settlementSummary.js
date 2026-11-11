// Plain-text trip summary for pasting into a group chat. It is the same for everyone:
// no "my" figures, only what each member paid, owes and has been asked to repay.
const shortDate = (value) => String(value || "").slice(5).replace("-", "/");

export function buildSettlementSummary({ trip, total, members, suggestions, settlements, rates, formatMoney }) {
  const base = trip.base_currency;
  const name = String(trip.name || "").trim();
  const range = trip.start_date && trip.end_date ? `（${shortDate(trip.start_date)}–${shortDate(trip.end_date)}）` : "";
  const lines = [
    `${name ? `${name} ` : ""}結算摘要${range}`,
    `整團花費：${formatMoney(total, base)}`,
  ];

  if (members.length) {
    lines.push("", "各人墊付 / 應分擔");
    members.forEach((member) => {
      lines.push(`${member.display_name}：墊付 ${formatMoney(member.paid_amount, base)} / 分擔 ${formatMoney(member.share_amount, base)}`);
    });
  }

  lines.push("", "還款建議");
  if (suggestions.length === 0) {
    lines.push("目前已平衡或尚無需結算");
  } else {
    suggestions.forEach((item) => {
      lines.push(`${item.from_display_name} → ${item.to_display_name}：${formatMoney(item.amount, item.currency)}`);
    });
  }
  const repaid = settlements.reduce((sum, item) => sum + Number(item.amount || 0), 0);
  if (repaid > 0) lines.push(`（已還款 ${formatMoney(repaid, base)}，上面是扣掉已還款後剩下的）`);

  const used = rates.filter((row) => row.rate && row.recorded_expenses);
  if (used.length) {
    lines.push("");
    used.forEach((row) => lines.push(`匯率：1 ${row.currency} = ${row.rate} ${base}（旅行匯率）`));
  }
  return lines.join("\n");
}
