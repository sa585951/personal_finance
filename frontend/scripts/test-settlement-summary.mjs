import assert from 'node:assert/strict';
import { buildSettlementSummary } from '../src/utils/settlementSummary.js';

const formatMoney = (amount, currency) => `${currency} ${Number(amount).toLocaleString('en-US')}`;
const base = {
  trip: { name: '日本旅行', base_currency: 'TWD', start_date: '2026-11-05', end_date: '2026-11-09' },
  total: 1980,
  members: [
    { display_name: '郭維哲', paid_amount: 1380, share_amount: 660 },
    { display_name: 'A', paid_amount: 0, share_amount: 660 },
  ],
  suggestions: [{ from_display_name: 'A', to_display_name: '郭維哲', amount: 660, currency: 'TWD' }],
  settlements: [],
  rates: [{ currency: 'JPY', rate: '0.25', recorded_expenses: 3 }, { currency: 'USD', rate: null, recorded_expenses: 0 }],
  formatMoney,
};

const text = buildSettlementSummary(base);
assert.equal(text, [
  '日本旅行 結算摘要（11/05–11/09）',
  '整團花費：TWD 1,980',
  '',
  '各人墊付 / 應分擔',
  '郭維哲：墊付 TWD 1,380 / 分擔 TWD 660',
  'A：墊付 TWD 0 / 分擔 TWD 660',
  '',
  '還款建議',
  'A → 郭維哲：TWD 660',
  '',
  '匯率：1 JPY = 0.25 TWD（旅行匯率）',
].join('\n'));
assert.ok(!text.includes('我的'));

const repaid = buildSettlementSummary({ ...base, settlements: [{ amount: 60 }] });
assert.ok(repaid.includes('已還款 TWD 60'));

const balanced = buildSettlementSummary({ ...base, suggestions: [], rates: [], trip: { name: '', base_currency: 'TWD' } });
assert.ok(balanced.startsWith('結算摘要\n'));
assert.ok(balanced.includes('目前已平衡或尚無需結算'));
assert.ok(!balanced.includes('匯率'));
console.log('settlement summary tests passed');
