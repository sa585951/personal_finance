<template>
  <div class="page-container">
    <h1>個人資產總覽</h1>

    <TransferForm :assets="assets" @transfer-success="fetchAssets" />
    <br></br>
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
import apiClient from "../api";
import AccountForm from "../components/assets/AccountForm.vue";
import AssetsTable from "../components/assets/AssetsTable.vue";
import TotalCards from "../components/assets/TotalCards.vue";
import TransferForm from "../components/assets/TransferForm.vue";

export default {
  name: "AssetsOverview",
  components: {
    AccountForm,
    AssetsTable,
    TotalCards,
    TransferForm,
  },
  data() {
    return {
      loading: true,
      error: null,
      assets: {},
      totals: null,
    };
  },
  created() {
    this.fetchAssets();
  },
  methods: {
    async fetchAssets() {
      try {
        const response = await apiClient.get(`/api/assets`);
        this.assets = response.data.data;
        this.totals = this.calculateTotals(this.assets);
      } catch (err) {
        console.error("無法載入資產資料:", err); // 改為 console.error
        this.error = "無法載入資產資料，請檢查後端伺服器或查看主控台錯誤。";
      } finally {
        this.loading = false;
      }
    },
    calculateTotals(assets) {
      const totals = {
        總資產: 0,
        其他: 0,
      };

      for (const accountId in assets) {
        const asset = assets[accountId];
        const balance = asset.balance;
        const type = asset.account_type;

        totals["總資產"] += balance;

        if (totals[type] === undefined) {
          totals[type] = 0;
        }

        // 累加金額
        totals[type] += balance;
      }

      const calculatedTotals = {
        總資產: 0,
        活存: 0, // Explicitly initialize common types if they are expected
        定存: 0,
        投資: 0,
        其他: 0,
      };

      for (const accountId in assets) {
        const asset = assets[accountId];
        const balance = parseFloat(asset.balance); // Ensure balance is a number
        const type = asset.account_type;

        if (isNaN(balance)) {
          console.warn(`Asset ${accountId} has invalid balance: ${asset.balance}`);
          continue; // Skip if balance is not a valid number
        }

        calculatedTotals["總資產"] += balance;

        if (type === "活存" || type === "定存" || type === "投資") {
          calculatedTotals[type] += balance;
        } else {
          calculatedTotals["其他"] += balance;
        }
      }

      return calculatedTotals;
    },
    async deleteAccount(accountId) {
      if (confirm(`確定要刪除此帳戶嗎？`)) {
        try {
          // 只傳遞唯一的 accountId
          await apiClient.delete(`/api/assets/${accountId}`);
          await this.fetchAssets();
        } catch (err) {
          console.error("刪除失敗", err);
        }
      }
    },
    async updateBalance(accountId, newBalance) {
      if (newBalance === null || newBalance === undefined) {
        return;
      }

      try {
        // 只傳遞唯一的 accountId 和新的餘額
        await apiClient.put(`/api/assets/${accountId}`, {
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
.page-container {
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
