import apiClient from '@/api';

async function getPendingOwner() {
  const auth = await apiClient.get('/api/auth/me');
  const userId = auth.data?.data?.user_id;
  if (!userId) throw new Error('無法確認登入狀態，請重新登入後再試。');
  return userId;
}

// Preserve the original intent across lost responses/reloads, scoped by owner.
export async function openPendingCommand(scope) {
  return pendingCommand(await getPendingOwner(), scope);
}

export async function openPendingCommandGroup(scopePrefix) {
  const ownerId = await getPendingOwner();
  const ownerPrefix = `nomica-pending:${ownerId}:`;
  const commands = [];
  for (let index = 0; index < sessionStorage.length; index++) {
    const key = sessionStorage.key(index);
    if (key?.startsWith(ownerPrefix + scopePrefix)) {
      const command = pendingCommand(ownerId, key.slice(ownerPrefix.length));
      if (command.pending) commands.push(command);
    }
  }
  return { commands, open: scope => pendingCommand(ownerId, scope) };
}

function pendingCommand(userId, scope) {
  const key = `nomica-pending:${userId}:${scope}`;
  const raw = sessionStorage.getItem(key);
  const pending = raw ? JSON.parse(raw) : null;
  if (pending && (!pending.requestId || !pending.payload)) {
    throw new Error('上一筆提交資料無法讀取，請先核對紀錄，避免重複記帳。');
  }
  return {
    scope, pending, ownerId: userId,
    async verifyOwner() {
      const auth = await apiClient.get('/api/auth/me');
      if (auth.data?.data?.user_id !== userId) {
        const error = new Error('登入使用者已變更，未送出交易，請重新載入頁面。');
        error.ownerChanged = true;
        throw error;
      }
    },
    prepare(payload) {
      // Re-read shared tab storage: a restored/stale view cannot overwrite a newer intent.
      const raw = sessionStorage.getItem(key);
      const stored = raw ? JSON.parse(raw) : null;
      if (stored) {
        if (!stored.requestId || !stored.payload) throw new Error('待確認資料無法讀取，請先核對紀錄。');
        this.pending = stored;
      }
      if (this.pending && JSON.stringify(this.pending.payload) !== JSON.stringify(payload)) {
        throw new Error('上一筆提交結果尚未確認，請先以原資料重試。');
      }
      if (!this.pending) {
        // API payloads are JSON. Clone through JSON to detach nested Vue proxies.
        const record = { requestId: crypto.randomUUID(), payload: JSON.parse(JSON.stringify(payload)) };
        // Store before HTTP; a storage failure must not send an untracked write.
        sessionStorage.setItem(key, JSON.stringify(record));
        this.pending = record;
      }
      return { ...JSON.parse(JSON.stringify(this.pending.payload)), client_request_id: this.pending.requestId };
    },
    clear(expectedRequestId = this.pending?.requestId) {
      // A late response from an old view must never discard a newer intent.
      const raw = sessionStorage.getItem(key);
      const stored = raw ? JSON.parse(raw) : null;
      if (expectedRequestId && stored?.requestId === expectedRequestId) sessionStorage.removeItem(key);
      if (this.pending?.requestId === expectedRequestId) this.pending = null;
    },
  };
}
