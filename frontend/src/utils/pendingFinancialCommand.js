import apiClient from '@/api';

// Preserve the original intent across lost responses/reloads, scoped by owner.
export async function openPendingCommand(scope) {
  const auth = await apiClient.get('/api/auth/me');
  const userId = auth.data?.data?.user_id;
  if (!userId) throw new Error('無法確認登入狀態，請重新登入後再試。');
  const key = `nomica-pending:${userId}:${scope}`;
  const raw = sessionStorage.getItem(key);
  const pending = raw ? JSON.parse(raw) : null;
  if (pending && (!pending.requestId || !pending.payload)) {
    throw new Error('上一筆提交資料無法讀取，請先核對紀錄，避免重複記帳。');
  }
  return {
    scope, pending,
    prepare(payload) {
      if (this.pending && JSON.stringify(this.pending.payload) !== JSON.stringify(payload)) {
        throw new Error('上一筆提交結果尚未確認，請先以原資料重試。');
      }
      if (!this.pending) {
        const record = { requestId: crypto.randomUUID(), payload: structuredClone(payload) };
        // Store before HTTP; a storage failure must not send an untracked write.
        sessionStorage.setItem(key, JSON.stringify(record));
        this.pending = record;
      }
      return { ...this.pending.payload, client_request_id: this.pending.requestId };
    },
    clear() {
      sessionStorage.removeItem(key);
      this.pending = null;
    },
  };
}
