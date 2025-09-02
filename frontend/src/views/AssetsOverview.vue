<template>
  <div class="assets-container">
    <h1>個人資產總覽</h1>
    <AccountForm @account-added="fetchAssets" />

    <div v-if="loading">載入中...</div>
    <div v-else-if="error">{{ error }}</div>
    <div v-else>
      <AssetsTable
        :assets="assets"
        @delete-account="deleteAccount"
        @update-balance="updateBalance"
      />

      <TotalCards :totals="totals" />
    </div>
  </div>
</template>

<script>
import axios from "axios";
import AccountForm from "../components/AccountForm.vue";
import AssetsTable from "../components/AssetsTable.vue";
import TotalCards from "../components/TotalCards.vue";

export default {
  name: "AssetsOverview",
  components: {
    AccountForm,
    AssetsTable,
    TotalCards,
  },
  data() {
    return {
      loading: true,
      error: null,
      assets: null,
      totals: null,
    };
  },
  created() {
    this.fetchAssets();
  },
  methods: {
    async fetchAssets() {
      try {
        const response = await axios.get("/api/assets");
        this.assets = response.data.data;
        this.totals = this.calculateTotals(this.assets);
      } catch (err) {
        this.error = "無法載入資產資料，請檢查後端伺服器是否運行。";
      } finally {
        this.loading = false;
      }
    },
    calculateTotals(assets) {
      const totals = {};
      let total = 0;
      for (const bank in assets) {
        for (const account in assets[bank]) {
          const balance = assets[bank][account].balance;
          total += balance;
          if (!totals[account]) {
            totals[account] = 0;
          }
          totals[account] += balance;
        }
      }
      totals["總資產"] = total;
      return totals;
    },
    async deleteAccount(bankName, accountType) {
      if (confirm(`確定要刪除 ${bankName} 的 ${accountType} 帳戶嗎？`)) {
        try {
          await axios.delete(`/api/assets/${bankName}/${accountType}`);
          await this.fetchAssets();
        } catch (err) {
          console.error("刪除失敗", err);
        }
      }
    },
    async updateBalance(bankName, accountType, newBalance) {
      if (newBalance === null || newBalance === undefined) {
        return;
      }

      try {
        await axios.put(`/api/assets/${bankName}/${accountType}`, {
          new_balance: newBalance,
        });
        await this.fetchAssets();
      } catch (err) {
        console.error("更新失敗", err);
      }
    },
  },
};
</script>

<style scoped>
/* 將原本的樣式移動到個別的子元件中後，這裡只保留 AssetsOverview 自己的樣式 */
.assets-container {
  max-width: 900px;
  margin: 40px auto;
  padding: 20px;
  background-color: var(--card-bg);
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

h1 {
  text-align: center;
  color: var(--text-color);
  font-size: 2.5rem;
  margin-bottom: 1rem;
}
</style>
