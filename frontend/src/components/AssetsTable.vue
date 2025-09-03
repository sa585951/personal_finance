<template>
  <div>
    <h2>帳戶餘額</h2>
    <table v-if="assets && Object.keys(assets).length > 0">
      <thead>
        <tr>
          <th>銀行</th>
          <th>帳戶類型</th>
          <th>餘額</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(accounts, bank) in assets" :key="bank">
          <td :rowspan="Object.keys(accounts).length">{{ bank }}</td>
          <td>{{ Object.keys(accounts)[0] }}</td>
          <td>
            ${{ accounts[Object.keys(accounts)[0]].balance.toLocaleString() }}
          </td>
          <td class="table-buttons">
            <input
              type="number"
              v-model.number="
                updatedBalances[bank + '-' + Object.keys(accounts)[0]]
              "
              :placeholder="accounts[Object.keys(accounts)[0]].balance"
            />
            <button
              class="update-btn"
              @click="
                $emit(
                  'update-balance',
                  bank,
                  Object.keys(accounts)[0],
                  updatedBalances[bank + '-' + Object.keys(accounts)[0]]
                )
              "
            >
              更新
            </button>
            <button
              class="delete-btn"
              @click="$emit('delete-account', bank, Object.keys(accounts)[0])"
            >
              刪除
            </button>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-else>
      <p>目前沒有資產資料。請新增一筆。</p>
    </div>
  </div>
</template>

<script>
export default {
  name: "AssetsTable",
  props: {
    assets: Object,
  },
  data() {
    return {
      updatedBalances: {},
    };
  },
  watch: {
    // 當資產數據改變時，清空輸入框
    assets() {
      this.updatedBalances = {};
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
.delete-btn {
  background-color: var(--danger-color);
}
.update-btn {
  background-color: var(--update-color);
}
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
