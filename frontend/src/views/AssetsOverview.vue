<template>
  <div class="page-container">
    <h1>個人資產總覽</h1>

    <TransferForm :assets="assets" @transfer-success="fetchAssets" />

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
import TransferForm from "../components/TransferForm.vue";

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

      // 處理完所有帳戶後，將「其他」類別的金額重新計算
      // 這是為了避免「其他」這個鍵可能被覆蓋的問題
      let totalOther = totals["總資產"];
      for (const type in totals) {
        if (type !== "總資產" && type !== "其他") {
          totalOther -= totals[type];
        }
      }
      totals["其他"] = totalOther;

      return totals;
    },
    async deleteAccount(accountId) {
      if (confirm(`確定要刪除此帳戶嗎？`)) {
        try {
          // 只傳遞唯一的 accountId
          await axios.delete(`/api/assets/${accountId}`);
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
        await axios.put(`/api/assets/${accountId}`, {
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
