<template>
  <div class="card">
    <div class="card-header">
      <h3 class="card-title">資產列表</h3>
    </div>
    <div class="card-body" v-if="assets && Object.keys(assets).length > 0">
      <table class="assets-table">
        <thead>
          <tr>
            <th>銀行名稱</th>
            <th>帳戶類型</th>
            <th>餘額</th>
            <th>動作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(asset, key) in assets" :key="key">
            <td>{{ asset.bank_name }}</td>
            <td>{{ asset.account_type }}</td>
            <td>${{ asset.balance.toLocaleString() }}</td>
            <td class="table-buttons">
              <button class="update-btn" @click="promptUpdate(key)">
                更新
              </button>
              <button class="delete-btn" @click="promptDelete(key)">
                刪除
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else class="no-data">
      <p>目前沒有資產，請點擊 "新增帳戶" 來新增一筆資產。</p>
    </div>
  </div>
</template>

<script>
export default {
  name: "AssetsTable",
  props: {
    assets: {
      type: Object,
      required: true,
      default: () => ({}),
    },
  },
  methods: {
    async promptUpdate(accountId) {
      const { value: newBalance } = await this.$swal.fire({
        title: "更新餘額",
        input: "number",
        inputLabel: "請輸入新的餘額：",
        showCancelButton: true,
        confirmButtonText: "確定",
        cancelButtonText: "取消",
        inputValidator: (value) => {
          if (!value || isNaN(value) || parseFloat(value) < 0) {
            return "輸入無效，餘額必須為非負數！";
          }
        },
      });

      if (newBalance) {
        this.$emit("update-balance", accountId, parseFloat(newBalance));
      }
    },
    async promptDelete(accountId) {
      const result = await this.$swal.fire({
        title: "確定刪除？",
        text: "此操作無法復原。",
        icon: "warning",
        showCancelButton: true,
        confirmButtonColor: "#d33",
        cancelButtonColor: "#3085d6",
        confirmButtonText: "確定刪除",
        cancelButtonText: "取消",
      });

      if (result.isConfirmed) {
        this.$emit("delete-account", accountId);
      }
    },
  },
};
</script>
<style scoped>
table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0 10px;
}

thead th {
  background-color: var(--primary-color);
  color: var(--card-bg);
  padding: 12px;
  text-align: center;
  font-size: 1rem;
  white-space: nowrap;
}

tbody td {
  padding: 12px;
  text-align: center;
}

tbody tr {
  background-color: var(--card-bg);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  box-shadow: 0 1px 5px rgba(0, 0, 0, 0.05);
}

tbody tr:hover {
  transform: translateY(-3px);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

/* 這裡是它們各自獨有的樣式，請保留 */
thead tr th:first-child {
  border-top-left-radius: 8px;
}
thead tr th:last-child {
  /* 因為現在只有四個 th，所以要改為 last-child */
  border-top-right-radius: 8px;
}

td:first-child {
  font-weight: bold;
}

.table-buttons {
  display: flex;
  justify-content: center;
  gap: 8px;
}

td input[type="number"] {
  width: 120px;
  padding: 6px;
  border: 1px solid #ccc;
  border-radius: 4px;
}
</style>
