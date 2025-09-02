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
/* 這裡保留所有表格相關的樣式 */
h2 {
  font-size: 1.8rem;
  margin-top: 2rem;
  margin-bottom: 1rem;
  border-bottom: 2px solid #eee;
  padding-bottom: 0.5rem;
}

table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0 10px;
  margin-top: 20px;
}

thead tr th {
  background-color: var(--primary-color);
  color: var(--card-bg);
  padding: 12px;
  text-align: center;
  font-size: 1rem;
}

thead tr th:first-child {
  border-top-left-radius: 8px;
}
thead tr th:last-child {
  /* 因為現在只有四個 th，所以要改為 last-child */
  border-top-right-radius: 8px;
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

td {
  padding: 12px;
  text-align: center;
  vertical-align: middle;
}

td:first-child {
  font-weight: bold;
}

button {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  color: white;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
}

.delete-btn {
  background-color: var(--danger-color);
  margin-right: 5px;
}

.update-btn {
  background-color: var(--update-color);
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
