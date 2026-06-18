<template>
  <div class="trips-page">
    <header class="trips-header">
      <div>
        <p class="eyebrow">Nomica Travel</p>
        <h1>旅行帳本</h1>
      </div>
      <div class="header-actions">
        <button class="icon-button" type="button" @click="fetchTrips" title="重新整理">
          <Refresh />
        </button>
        <button
          v-if="trips.length === 0"
          class="quiet-action"
          type="button"
          @click="toggleTripManagement"
        >
          管理
        </button>
        <button class="new-trip-button" type="button" @click="showCreateTrip = !showCreateTrip">
          <Plus />
          {{ showCreateTrip ? "收合" : "新增" }}
        </button>
      </div>
    </header>

    <section v-if="showCreateTrip || trips.length === 0" class="create-panel">
      <div class="section-title">
        <Plus />
        <h2>新增旅行</h2>
      </div>
      <form class="trip-form" @submit.prevent="createTrip">
        <label>
          名稱
          <input v-model.trim="newTrip.name" type="text" required placeholder="日本 2027" />
        </label>
        <label>
          地點
          <input v-model.trim="newTrip.destination" type="text" placeholder="Tokyo" />
        </label>
        <label>
          開始
          <input v-model="newTrip.start_date" type="date" required />
        </label>
        <label>
          結束
          <input v-model="newTrip.end_date" type="date" required />
        </label>
        <label>
          本幣
          <select v-model="newTrip.base_currency">
            <option value="TWD">TWD</option>
            <option value="JPY">JPY</option>
            <option value="KRW">KRW</option>
            <option value="USD">USD</option>
            <option value="EUR">EUR</option>
          </select>
        </label>
        <label>
          當地幣別
          <select v-model="newTrip.default_currency">
            <option value="TWD">TWD</option>
            <option value="JPY">JPY</option>
            <option value="KRW">KRW</option>
            <option value="USD">USD</option>
            <option value="EUR">EUR</option>
          </select>
        </label>
        <label class="toggle-row">
          <input v-model="newTrip.include_in_monthly_report" type="checkbox" />
          計入日常統計
        </label>
        <p class="field-hint">
          開啟後，此旅行支出會一起出現在首頁與收支統計；關閉則只保留在旅行帳本內。
        </p>
        <button class="primary-action" type="submit" :disabled="submittingTrip">
          <Plus />
          建立
        </button>
      </form>
      <p v-if="tripMessage" class="status-message">{{ tripMessage }}</p>
    </section>

    <section v-if="showTripManagement && !selectedTrip" class="management-panel standalone-management">
      <div>
        <strong>旅行管理</strong>
        <span>可在這裡找回已封存或 30 天內軟刪除的帳本。</span>
      </div>
      <div class="managed-trip-group">
        <div class="managed-trip-heading">
          <strong>已封存帳本</strong>
          <span>{{ archivedManagedTrips.length }} 本</span>
        </div>
        <div v-if="archivedManagedTrips.length === 0" class="managed-empty">尚無封存帳本</div>
        <div v-else class="managed-trip-list">
          <div v-for="trip in archivedManagedTrips" :key="trip.id" class="managed-trip-row">
            <div>
              <strong>{{ trip.name }}</strong>
              <span>{{ trip.destination || "未設定地點" }} · {{ formatRange(trip) }}</span>
            </div>
            <button class="quiet-mini-button" type="button" @click="unarchiveTrip(trip)">解除封存</button>
          </div>
        </div>
      </div>
      <div class="managed-trip-group">
        <div class="managed-trip-heading">
          <strong>已刪除帳本</strong>
          <span>{{ deletedManagedTrips.length }} 本</span>
        </div>
        <div v-if="deletedManagedTrips.length === 0" class="managed-empty">尚無可復原帳本</div>
        <div v-else class="managed-trip-list">
          <div v-for="trip in deletedManagedTrips" :key="trip.id" class="managed-trip-row deleted">
            <div>
              <strong>{{ trip.name }}</strong>
              <span>可復原至 {{ formatDateTime(trip.purge_after) || "30 天內" }}</span>
            </div>
            <button class="quiet-mini-button" type="button" @click="restoreTrip(trip)">復原</button>
          </div>
        </div>
      </div>
    </section>

    <div v-if="loading" class="loading-state">載入中...</div>
    <div v-else-if="trips.length === 0" class="empty-state">尚未建立旅行帳本</div>

    <section v-else class="trips-layout">
      <article v-if="selectedTrip" class="trip-detail">
        <div class="current-trip-card">
          <div>
            <span class="trip-state-badge" :class="{ included: selectedTrip.include_in_monthly_report }">
              {{ tripReportLabel(selectedTrip) }}
            </span>
            <strong>{{ selectedTrip.name }}</strong>
            <span>{{ selectedTrip.destination || "未設定地點" }} · {{ formatRange(selectedTrip) }}</span>
            <div class="trip-compact-meta">
              <span>{{ tripDays(selectedTrip) }} 天</span>
              <span>{{ selectedTrip.members.length }} 人</span>
              <span>{{ selectedTrip.default_currency }} / {{ selectedTrip.base_currency }}</span>
            </div>
          </div>
          <div class="current-trip-actions">
            <button
              v-if="canManageSelectedTrip"
              class="quiet-action"
              type="button"
              :disabled="updatingTripSettings"
              @click="toggleSelectedTripReportScope"
            >
              {{ selectedTrip.include_in_monthly_report ? "改為獨立統計" : "計入日常統計" }}
            </button>
            <button class="secondary-action" type="button" @click="showTripSwitcher = true">
              切換旅行
            </button>
          </div>
        </div>

        <nav class="trip-tabs" aria-label="旅行操作">
          <button
            v-for="tab in operationTabs"
            :key="tab.key"
            type="button"
            :class="{ active: activeSection === tab.key }"
            @click="activeSection = tab.key"
          >
            <component :is="tab.icon" />
            <span>{{ tab.label }}</span>
          </button>
        </nav>

        <button
          class="trip-summary-compact"
          type="button"
          @click="showTripSummary = !showTripSummary"
        >
          <span>
            我的成本 {{ formatMoney(myTripShareAmount, selectedTrip.base_currency) }}
          </span>
          <strong :class="myTripNetStatus.amountClass">
            {{ myTripNetStatus.label }} {{ formatMoney(Math.abs(myTripNetAmount), selectedTrip.base_currency) }}
          </strong>
        </button>

        <div class="trip-summary-grid" :class="{ expanded: showTripSummary }">
          <div class="summary-card share">
            <span>我的成本</span>
            <strong>{{ formatMoney(myTripShareAmount, selectedTrip.base_currency) }}</strong>
            <small>分帳後歸屬於你的支出</small>
          </div>
          <div class="summary-card group">
            <span>整團花費</span>
            <strong>{{ formatMoney(tripExpenseTotal, selectedTrip.base_currency) }}</strong>
            <small>整趟旅行總額</small>
          </div>
          <div class="summary-card" :class="myTripNetStatus.tone">
            <span>{{ myTripNetStatus.label }}</span>
            <strong :class="myTripNetStatus.amountClass">
              {{ formatMoney(Math.abs(myTripNetAmount), selectedTrip.base_currency) }}
            </strong>
            <small>{{ myTripNetStatus.hint }}</small>
          </div>
        </div>

        <div class="trip-category-panel" :class="{ expanded: showTripSummary }">
          <TripCategoryChart
            :transactions="tripTransactions"
            :currency="selectedTrip.base_currency"
          />
        </div>

        <div class="members-section app-panel" :class="{ active: activeSection === 'members' }">
          <div class="section-title">
            <User />
            <h3>旅伴</h3>
          </div>
          <div class="member-list">
            <div v-for="member in selectedTrip.members" :key="member.id" class="member-row">
              <div>
                <span>{{ member.display_name }}</span>
                <small>
                  {{ translateRole(member.role) }}
                  <template v-if="member.id === selectedTrip.current_member_id"> · 你</template>
                </small>
              </div>
              <select
                v-if="isTripOwner && member.role !== 'owner'"
                class="member-role-select"
                :value="member.role"
                @change="updateMemberRole(member, $event.target.value)"
              >
                <option value="editor">編輯</option>
                <option value="viewer">檢視</option>
              </select>
              <button
                v-if="isTripOwner && member.role !== 'owner'"
                class="member-delete"
                type="button"
                aria-label="刪除旅伴"
                @click="deleteMember(member)"
              >
                <Delete />
              </button>
            </div>
          </div>

          <section v-if="isTripOwner" class="invite-panel">
            <div>
              <strong>邀請連結</strong>
              <span>30 天內可重複使用，最多 15 位成員，加入後預設為編輯。</span>
            </div>
            <div v-if="activeInvite" class="invite-status-row">
              <span>連結已開啟至 {{ formatDateTime(activeInvite.expires_at) }}</span>
              <button class="quiet-mini-button" type="button" @click="closeInvite">關閉</button>
            </div>
            <div v-if="latestInviteUrl" class="invite-copy-row">
              <input :value="latestInviteUrl" readonly />
              <button class="secondary-action" type="button" @click="copyInviteLink">
                複製
              </button>
            </div>
            <button
              v-if="!activeInvite"
              class="secondary-action"
              type="button"
              :disabled="submittingInvite"
              @click="createInvite"
            >
              建立邀請連結
            </button>
            <p v-if="inviteMessage" class="status-message">{{ inviteMessage }}</p>
          </section>

          <form v-if="isTripOwner" class="member-form" @submit.prevent="addMember">
            <input v-model.trim="newMember.display_name" type="text" required placeholder="朋友 A" />
            <select v-model="newMember.role">
              <option value="viewer">檢視</option>
              <option value="editor">編輯</option>
            </select>
            <button class="secondary-action" type="submit" :disabled="submittingMember">
              <Plus />
              新增
            </button>
          </form>
          <button
            v-else-if="currentTripMember && currentTripMember.role !== 'owner'"
            class="danger-action leave-trip-button"
            type="button"
            @click="leaveSelectedTrip"
          >
            退出此帳本
          </button>
          <p v-if="memberMessage" class="status-message">{{ memberMessage }}</p>
        </div>

        <div
          v-if="canCreateTripTransaction"
          class="expense-section app-panel"
          :class="{ active: activeSection === 'expense' }"
        >
          <div class="section-title">
            <Money />
            <h3>新增旅行支出</h3>
          </div>
          <form class="expense-form" @submit.prevent="addTripExpense">
            <label>
              品項
              <input v-model.trim="newExpense.item" type="text" required placeholder="拉麵" />
            </label>
            <label>
              金額
              <input v-model.number="newExpense.amount" type="number" min="1" step="1" required />
            </label>
            <div class="quick-currency-row full-row">
              <button
                v-for="currency in quickCurrencies"
                :key="currency"
                type="button"
                :class="{ active: newExpense.original_currency === currency }"
                @click="newExpense.original_currency = currency"
              >
                {{ currency }}
              </button>
            </div>
            <label>
              類別
              <select v-model="newExpense.budget_category" required>
                <option v-for="category in expenseCategories" :key="category" :value="category">
                  {{ category }}
                </option>
              </select>
            </label>
            <label>
              付款人
              <select v-model="newExpense.paid_by_member_id">
                <option
                  v-for="member in selectedTrip.members"
                  :key="member.id"
                  :value="member.id"
                >
                  {{ member.display_name }}
                </option>
              </select>
            </label>
            <label class="full-row">
              搜尋付款帳戶
              <input
                v-model.trim="tripAccountSearchText"
                type="search"
                placeholder="輸入銀行、信用卡、現金或帳戶名稱"
                :disabled="!isCurrentUserPayer"
              />
            </label>
            <label class="full-row">
              付款帳戶
              <select v-model="newExpense.account_id" :disabled="!isCurrentUserPayer">
                <option value="">不連動帳戶</option>
                <optgroup
                  v-for="group in groupedTripAccounts"
                  :key="group.type"
                  :label="group.label"
                >
                  <option
                    v-for="account in group.accounts"
                    :key="account.id"
                    :value="account.id"
                  >
                    {{ account.label }}
                  </option>
                </optgroup>
              </select>
            </label>
            <p v-if="!isCurrentUserPayer" class="account-link-hint full-row">
              只有自己付款時才會連動帳戶。其他旅伴墊款會進入分帳結算，不會異動你的帳戶餘額。
            </p>
            <div v-if="expensePreview" class="expense-preview full-row">
              <div>
                <span>約略本幣</span>
                <strong>{{ expensePreview.convertedText }}</strong>
              </div>
              <div>
                <span>帳戶扣款</span>
                <strong>{{ expensePreview.accountDebitText }}</strong>
              </div>
            </div>
            <div class="split-box full-row">
              <div class="split-header">
                <span>分帳方式</span>
                <div class="split-mode-tabs">
                  <button
                    type="button"
                    :class="{ active: newExpense.split_mode === 'equal' }"
                    @click="setSplitMode('equal')"
                  >
                    均分
                  </button>
                  <button
                    type="button"
                    :class="{ active: newExpense.split_mode === 'custom' }"
                    @click="setSplitMode('custom')"
                  >
                    自訂
                  </button>
                </div>
              </div>

              <template v-if="newExpense.split_mode === 'equal'">
                <button class="split-member-toggle" type="button" @click="showSplitMemberOptions = !showSplitMemberOptions">
                  <span>{{ splitMemberSummary }}</span>
                  <strong>{{ showSplitMemberOptions ? "收合" : "調整" }}</strong>
                </button>
                <div v-if="showSplitMemberOptions" class="split-member-options">
                  <label
                    v-for="member in selectedTrip.members"
                    :key="member.id"
                    class="split-option"
                  >
                    <input v-model="newExpense.split_member_ids" type="checkbox" :value="member.id" />
                    {{ member.display_name }}
                  </label>
                </div>
              </template>

              <div v-else class="custom-split-list">
                <label
                  v-for="member in selectedTrip.members"
                  :key="member.id"
                  class="custom-split-row"
                >
                  <span>{{ member.display_name }}</span>
                  <input
                    v-model.number="newExpense.split_allocations[member.id]"
                    type="number"
                    min="0"
                    step="1"
                  />
                </label>
                <div class="custom-split-summary" :class="{ invalid: customSplitDifference !== 0 }">
                  <span>合計 {{ formatMoney(customSplitTotal, newExpense.original_currency) }}</span>
                  <strong>
                    {{ customSplitDifference === 0 ? "已平衡" : `差額 ${formatMoney(customSplitDifference, newExpense.original_currency)}` }}
                  </strong>
                </div>
              </div>
            </div>
            <button class="advanced-toggle full-row" type="button" @click="showExpenseAdvanced = !showExpenseAdvanced">
              {{ showExpenseAdvanced ? "收合進階設定" : "進階設定" }}
            </button>
            <div v-if="showExpenseAdvanced" class="advanced-expense-grid full-row">
              <label>
                日期
                <input v-model="newExpense.date" type="date" required />
              </label>
              <label>
                店家
                <input v-model.trim="newExpense.merchant" type="text" placeholder="一蘭" />
              </label>
              <label>
                匯率
                <input v-model.number="newExpense.exchange_rate" type="number" min="0.00000001" step="0.00000001" required />
              </label>
              <label>
                備註
                <input v-model.trim="newExpense.description" type="text" placeholder="可留空" />
              </label>
              <label>
                確認狀態
                <select v-model="newExpense.review_status">
                  <option value="confirmed">已確認</option>
                  <option value="pending">待確認</option>
                </select>
              </label>
            </div>
            <button
              v-if="editingTransactionId"
              class="quiet-action full-row"
              type="button"
              @click="cancelEditExpense"
            >
              取消編輯
            </button>
            <button class="primary-action full-row" type="submit" :disabled="submittingExpense">
              <Plus />
              {{ editingTransactionId ? "更新支出" : "新增支出" }}
            </button>
          </form>
          <p v-if="expenseMessage" class="status-message">{{ expenseMessage }}</p>
        </div>

        <div class="transactions-section app-panel" :class="{ active: activeSection === 'transactions' }">
          <div class="section-title split-title-row">
            <div>
              <List />
              <h3>旅行交易</h3>
            </div>
            <button
              v-if="tripTransactions.length > 0"
              class="copy-summary-button"
              type="button"
              @click="exportTripTransactionsCsv"
            >
              匯出 CSV
            </button>
          </div>
          <div
            v-if="tripDateFilters.length > 1"
            class="transaction-date-tabs"
            aria-label="旅行交易日期篩選"
          >
            <button
              v-for="filter in tripDateFilters"
              :key="filter.key"
              type="button"
              :class="{ active: selectedTransactionDate === filter.key }"
              @click="selectedTransactionDate = filter.key"
            >
              <span>{{ filter.label }}</span>
              <small>{{ filter.count }} 筆</small>
            </button>
          </div>
          <div v-if="tripTransactions.length === 0" class="empty-state">尚未新增旅行支出</div>
          <div v-else-if="filteredTripTransactions.length === 0" class="empty-state">這一天尚無旅行支出</div>
          <div v-else class="transaction-list">
            <div
              v-for="transaction in filteredTripTransactions"
              :key="transaction.id"
              class="transaction-row"
              :class="{ selected: selectedTransactionDetail && selectedTransactionDetail.id === transaction.id }"
              @click="loadTransactionDetail(transaction.id)"
            >
              <div>
                <strong>{{ transaction.category }}</strong>
                <span>{{ transaction.date }} · {{ transaction.merchant || transaction.budget_category }}</span>
              </div>
              <div class="transaction-amount">
                <span>{{ formatMoney(transaction.amount, transaction.currency) }}</span>
                <small>{{ formatMoney(transaction.converted_amount, transaction.base_currency) }}</small>
              </div>
              <button
                v-if="transaction.can_delete !== false"
                class="transaction-delete"
                type="button"
                title="刪除交易"
                @click.stop="deleteTripTransaction(transaction)"
              >
                <Delete />
              </button>
              <button
                v-if="transaction.can_edit !== false"
                class="transaction-edit"
                type="button"
                title="編輯交易"
                @click.stop="startEditTransaction(transaction.id)"
              >
                <Edit />
              </button>
            </div>
          </div>
        </div>

        <div v-if="selectedTransactionDetail" class="transaction-detail-section app-panel" :class="{ active: activeSection === 'transactions' }">
          <div class="section-title">
            <Document />
            <h3>交易明細</h3>
          </div>
          <div class="detail-grid">
            <div>
              <span>品項</span>
              <strong>{{ selectedTransactionDetail.category }}</strong>
            </div>
            <div>
              <span>付款人</span>
              <strong>{{ selectedTransactionDetail.paid_by_member?.display_name || "未設定" }}</strong>
            </div>
            <div>
              <span>記錄者</span>
              <strong>{{ selectedTransactionDetail.created_by_display_name || "未設定" }}</strong>
            </div>
            <div>
              <span>確認狀態</span>
              <strong>{{ translateReviewStatus(selectedTransactionDetail.review_status) }}</strong>
            </div>
            <div>
              <span>原幣金額</span>
              <strong>{{ formatMoney(selectedTransactionDetail.amount, selectedTransactionDetail.currency) }}</strong>
            </div>
            <div>
              <span>換算金額</span>
              <strong>{{ formatMoney(selectedTransactionDetail.converted_amount, selectedTransactionDetail.base_currency) }}</strong>
            </div>
            <div>
              <span>此筆成本</span>
              <strong>{{ formatMyTransactionShare(selectedTransactionDetail) }}</strong>
            </div>
            <div>
              <span>匯率</span>
              <strong>{{ selectedTransactionDetail.exchange_rate }}</strong>
            </div>
            <div>
              <span>類別</span>
              <strong>{{ selectedTransactionDetail.budget_category }}</strong>
            </div>
            <div class="full-row">
              <span>備註</span>
              <strong>{{ selectedTransactionDetail.description || "無" }}</strong>
            </div>
          </div>

          <div class="split-detail-list">
            <div
              v-for="split in selectedTransactionDetail.splits"
              :key="split.id"
              class="split-detail-row"
            >
              <span>{{ split.display_name }}</span>
              <strong>
                {{ formatMoney(split.share_amount, split.share_currency) }}
                <small>{{ formatMoney(split.converted_share_amount, split.base_currency) }}</small>
              </strong>
            </div>
          </div>
        </div>

        <div class="split-summary-section app-panel" :class="{ active: activeSection === 'split' }">
          <div class="trip-closeout-panel" :class="tripCloseoutStatus.tone">
            <div class="closeout-header">
              <span>旅行收尾檢查</span>
              <strong :class="tripCloseoutStatus.tone">{{ tripCloseoutStatus.label }}</strong>
            </div>
            <div class="closeout-list">
              <div
                v-for="item in tripCloseoutChecks"
                :key="item.label"
                class="closeout-item"
                :class="item.tone"
              >
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
              </div>
            </div>
          </div>

          <div class="section-title split-title-row">
            <div>
              <TrendCharts />
              <h3>誰要給誰</h3>
            </div>
            <button class="copy-summary-button" type="button" @click="copySettlementSummary">
              複製摘要
            </button>
          </div>
          <div v-if="settlementSuggestions.length === 0" class="empty-state">目前已平衡或尚無需結算</div>
          <div v-else class="settlement-list settlement-action-list">
            <div
              v-for="suggestion in settlementSuggestions"
              :key="`${suggestion.from_member_id}-${suggestion.to_member_id}-${suggestion.amount}`"
              class="settlement-row settlement-action-row"
            >
              <div class="settlement-route">
                <strong>{{ suggestion.from_display_name }}</strong>
                <span>→</span>
                <strong>{{ suggestion.to_display_name }}</strong>
              </div>
              <div class="settlement-actions">
                <strong>{{ formatMoney(suggestion.amount, suggestion.currency) }}</strong>
                <button
                  v-if="suggestion.can_confirm !== false"
                  class="confirm-settlement-button"
                  type="button"
                  @click="confirmSettlement(suggestion)"
                >
                  已付款
                </button>
              </div>
            </div>
          </div>

          <button
            class="detail-toggle settlement-title"
            type="button"
            @click="showSplitDetails = !showSplitDetails"
          >
            <span>
              <TrendCharts />
              核對明細
            </span>
            <strong>{{ showSplitDetails ? "收合" : "展開" }}</strong>
          </button>
          <div v-if="showSplitDetails && splitSummary.length === 0" class="empty-state">尚無分帳資料</div>
          <div v-else-if="showSplitDetails" class="split-summary-list">
            <div
              v-for="member in splitSummary"
              :key="member.member_id"
              class="split-summary-row"
              :class="splitStatusClass(member)"
            >
              <div>
                <strong>{{ member.display_name }}</strong>
                <span>
                  付款 {{ formatMoney(member.paid_amount, member.currency) }} · 分攤 {{ formatMoney(member.share_amount, member.currency) }}
                </span>
              </div>
              <strong
                class="net-amount"
                :class="member.net_amount >= 0 ? 'positive-net' : 'negative-net'"
              >
                <small>{{ splitNetStatus(member) }}</small>
                {{ formatMoney(Math.abs(member.net_amount), member.currency) }}
              </strong>
            </div>
          </div>

          <div class="section-title settlement-title">
            <TrendCharts />
            <h3>已確認結算</h3>
          </div>
          <div v-if="settlementRecords.length === 0" class="empty-state">尚無已確認結算</div>
          <div v-else class="settlement-list">
            <div
              v-for="settlement in settlementRecords"
              :key="settlement.id"
              class="settlement-row settled"
            >
              <span>
                {{ settlement.from_display_name }} 已付給 {{ settlement.to_display_name }}
              </span>
              <div class="settlement-actions">
                <strong>{{ formatMoney(settlement.amount, settlement.currency) }}</strong>
                <button
                  v-if="settlement.can_void !== false"
                  class="quiet-mini-button"
                  type="button"
                  @click="deleteSettlement(settlement)"
                >
                  撤銷
                </button>
              </div>
            </div>
          </div>
        </div>

        <section v-if="isTripOwner" class="trip-management">
          <button class="management-toggle" type="button" @click="toggleTripManagement">
            {{ showTripManagement ? "收合旅行管理" : "旅行管理" }}
          </button>
          <div v-if="showTripManagement" class="management-panel">
            <div>
              <strong>帳本狀態</strong>
              <span>封存會保留資料；刪除會先保留 30 天。</span>
            </div>
            <div class="danger-row">
              <button class="quiet-action" type="button" @click="archiveSelectedTrip">封存帳本</button>
              <button class="danger-action" type="button" @click="deleteSelectedTrip">刪除帳本</button>
            </div>
            <div class="managed-trip-group">
              <div class="managed-trip-heading">
                <strong>已封存帳本</strong>
                <span>{{ archivedManagedTrips.length }} 本</span>
              </div>
              <div v-if="archivedManagedTrips.length === 0" class="managed-empty">尚無封存帳本</div>
              <div v-else class="managed-trip-list">
                <div v-for="trip in archivedManagedTrips" :key="trip.id" class="managed-trip-row">
                  <div>
                    <strong>{{ trip.name }}</strong>
                    <span>{{ trip.destination || "未設定地點" }} · {{ formatRange(trip) }}</span>
                  </div>
                  <button class="quiet-mini-button" type="button" @click="unarchiveTrip(trip)">解除封存</button>
                </div>
              </div>
            </div>
            <div class="managed-trip-group">
              <div class="managed-trip-heading">
                <strong>已刪除帳本</strong>
                <span>{{ deletedManagedTrips.length }} 本</span>
              </div>
              <div v-if="deletedManagedTrips.length === 0" class="managed-empty">尚無可復原帳本</div>
              <div v-else class="managed-trip-list">
                <div v-for="trip in deletedManagedTrips" :key="trip.id" class="managed-trip-row deleted">
                  <div>
                    <strong>{{ trip.name }}</strong>
                    <span>可復原至 {{ formatDateTime(trip.purge_after) || "30 天內" }}</span>
                  </div>
                  <button class="quiet-mini-button" type="button" @click="restoreTrip(trip)">復原</button>
                </div>
              </div>
            </div>
          </div>
        </section>
      </article>
    </section>

    <div v-if="showTripSwitcher" class="modal-backdrop" @click.self="showTripSwitcher = false">
      <section class="trip-switcher">
        <div class="switcher-header">
          <h2>切換旅行</h2>
          <button class="quiet-action" type="button" @click="showTripSwitcher = false">關閉</button>
        </div>
        <div class="trip-switcher-list">
          <button
            v-for="trip in trips"
            :key="trip.id"
            class="switcher-row"
            :class="{ active: selectedTrip && selectedTrip.id === trip.id }"
            type="button"
            @click="switchTrip(trip.id)"
          >
            <div>
              <span class="trip-state-badge" :class="{ included: trip.include_in_monthly_report }">
                {{ tripReportLabel(trip) }}
              </span>
              <strong>{{ trip.name }}</strong>
              <span>{{ trip.destination || "未設定地點" }} · {{ formatRange(trip) }}</span>
            </div>
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<script>
import { Calendar, Delete, Document, Edit, List, Location, Money, Plus, Refresh, TrendCharts, User } from "@element-plus/icons-vue";
import apiClient from "@/api";
import TripCategoryChart from "@/components/charts/TripCategoryChart.vue";

export default {
  name: "TripsView",
  components: {
    Calendar,
    Delete,
    Document,
    Edit,
    List,
    Location,
    Money,
    Plus,
    Refresh,
    TrendCharts,
    TripCategoryChart,
    User,
  },
  data() {
    const today = new Date().toISOString().slice(0, 10);
    return {
      loading: true,
      submittingTrip: false,
      submittingMember: false,
      submittingExpense: false,
      submittingInvite: false,
      updatingTripSettings: false,
      showCreateTrip: false,
      showTripSwitcher: false,
      showTripManagement: false,
      activeSection: "expense",
      trips: [],
      managedTrips: [],
      selectedTrip: null,
      assets: {},
      tripTransactions: [],
      selectedTransactionDetail: null,
      splitSummary: [],
      settlementSuggestions: [],
      settlementRecords: [],
      splitDetailsLoaded: false,
      inviteStatusLoaded: false,
      activeInvite: null,
      latestInviteUrl: "",
      expenseCategories: [],
      editingTransactionId: null,
      selectedTransactionDate: "all",
      showExpenseAdvanced: false,
      showSplitDetails: false,
      showTripSummary: false,
      showSplitMemberOptions: false,
      newTrip: {
        name: "",
        destination: "",
        start_date: today,
        end_date: today,
        timezone: "Asia/Taipei",
        base_currency: "TWD",
        default_currency: "JPY",
        include_in_monthly_report: false,
      },
      newMember: {
        display_name: "",
        role: "viewer",
      },
      newExpense: {
        date: today,
        item: "",
        merchant: "",
        budget_category: "伙食",
        amount: null,
        original_currency: "JPY",
        exchange_rate: 0.22,
        paid_by_member_id: "",
        account_id: "",
        description: "",
        review_status: "confirmed",
        split_mode: "equal",
        split_member_ids: [],
        split_allocations: {},
      },
      tripMessage: "",
      memberMessage: "",
      expenseMessage: "",
      inviteMessage: "",
      tripAccountSearchText: "",
    };
  },
  computed: {
    operationTabs() {
      const tabs = [
        { key: "expense", label: "記支出", icon: "Money" },
        { key: "transactions", label: "交易", icon: "List" },
        { key: "split", label: "分帳", icon: "TrendCharts" },
        { key: "members", label: "旅伴", icon: "User" },
      ];
      return this.canCreateTripTransaction
        ? tabs
        : tabs.filter((tab) => tab.key !== "expense");
    },
    quickCurrencies() {
      if (!this.selectedTrip) {
        return ["TWD"];
      }
      return Array.from(new Set([
        this.selectedTrip.default_currency,
        this.selectedTrip.base_currency,
        "TWD",
      ].filter(Boolean)));
    },
    tripExpenseTotal() {
      return this.tripTransactions
        .filter((transaction) => transaction.type === "expense")
        .reduce((sum, transaction) => sum + Number(transaction.converted_amount || 0), 0);
    },
    tripDateFilters() {
      const dateMap = new Map();
      this.tripTransactions.forEach((transaction) => {
        if (!transaction.date) return;
        const current = dateMap.get(transaction.date) || {
          key: transaction.date,
          label: this.formatDateChip(transaction.date),
          count: 0,
        };
        current.count += 1;
        dateMap.set(transaction.date, current);
      });

      const dates = Array.from(dateMap.values())
        .sort((left, right) => left.key.localeCompare(right.key));

      return [
        {
          key: "all",
          label: "全部",
          count: this.tripTransactions.length,
        },
        ...dates,
      ];
    },
    filteredTripTransactions() {
      if (this.selectedTransactionDate === "all") {
        return this.tripTransactions;
      }
      return this.tripTransactions.filter(
        (transaction) => transaction.date === this.selectedTransactionDate
      );
    },
    tripCloseoutStatus() {
      if (this.tripTransactions.length === 0) {
        return { label: "尚無支出", tone: "neutral" };
      }
      if (this.settlementSuggestions.length > 0) {
        return { label: "待結算", tone: "warning" };
      }
      return { label: "已平衡", tone: "success" };
    },
    tripCloseoutChecks() {
      return [
        {
          label: "旅行支出",
          value: this.tripTransactions.length > 0 ? `${this.tripTransactions.length} 筆` : "尚未記錄",
          tone: this.tripTransactions.length > 0 ? "success" : "neutral",
        },
        {
          label: "待收待付",
          value: this.settlementSuggestions.length > 0 ? `${this.settlementSuggestions.length} 筆待處理` : "已平衡",
          tone: this.settlementSuggestions.length > 0 ? "warning" : "success",
        },
        {
          label: "已確認付款",
          value: this.settlementRecords.length > 0 ? `${this.settlementRecords.length} 筆` : "尚無",
          tone: this.settlementRecords.length > 0 ? "success" : "neutral",
        },
      ];
    },
    currentMemberSummary() {
      if (!this.selectedTrip || !this.selectedTrip.current_member_id) return null;
      return this.splitSummary.find(
        (member) => member.member_id === this.selectedTrip.current_member_id
      ) || null;
    },
    canManageSelectedTrip() {
      if (!this.selectedTrip || !this.selectedTrip.current_member_id) return false;
      const currentMember = this.selectedTrip.members.find(
        (member) => member.id === this.selectedTrip.current_member_id
      );
      return currentMember?.role === "owner";
    },
    myTripShareAmount() {
      return Number(this.currentMemberSummary?.share_amount || 0);
    },
    myTripNetAmount() {
      return Number(this.currentMemberSummary?.net_amount || 0);
    },
    myTripNetStatus() {
      const amount = Number(this.myTripNetAmount || 0);
      if (amount > 0) {
        return {
          label: "待收",
          hint: "旅伴需還你",
          tone: "positive",
          amountClass: "positive-net",
        };
      }
      if (amount < 0) {
        return {
          label: "待付",
          hint: "你需要補給旅伴",
          tone: "negative",
          amountClass: "negative-net",
        };
      }
      return {
        label: "已平衡",
        hint: "目前不用結算",
        tone: "balanced",
        amountClass: "",
      };
    },
    compatibleTripAccounts() {
      if (!this.selectedTrip || !this.isCurrentUserPayer) return [];
      const compatibleCurrencies = new Set([
        this.newExpense.original_currency,
        this.selectedTrip.base_currency,
      ]);
      return Object.values(this.assets || {})
        .filter((asset) => compatibleCurrencies.has(asset.currency))
        .map((asset) => ({
          id: asset.id,
          type: asset.account_type || "other",
          bankName: asset.bank_name || "",
          currency: asset.currency || "TWD",
          label: `${asset.bank_name} - ${this.translateAccountType(asset.account_type)} (${asset.currency} ${Number(asset.balance || 0).toLocaleString()})`,
        }))
        .sort((a, b) => {
          const typeOrder = this.accountTypeOrder(a.type) - this.accountTypeOrder(b.type);
          if (typeOrder !== 0) return typeOrder;
          return a.bankName.localeCompare(b.bankName, "zh-TW");
        });
    },
    filteredTripAccounts() {
      const keyword = this.tripAccountSearchText.toLowerCase();
      if (!keyword) return this.compatibleTripAccounts;
      return this.compatibleTripAccounts.filter((account) => {
        const searchableText = [
          account.bankName,
          account.type,
          this.translateAccountType(account.type),
          account.currency,
        ].join(" ").toLowerCase();
        return searchableText.includes(keyword);
      });
    },
    groupedTripAccounts() {
      return this.groupAccountsByType(this.filteredTripAccounts);
    },
    archivedManagedTrips() {
      return this.managedTrips.filter((trip) => !trip.deleted_at && trip.status === "archived");
    },
    deletedManagedTrips() {
      return this.managedTrips.filter((trip) => trip.deleted_at);
    },
    selectedPaymentAccount() {
      if (!this.newExpense.account_id) return null;
      return Object.values(this.assets || {}).find(
        (asset) => asset.id === this.newExpense.account_id
      ) || null;
    },
    isCurrentUserPayer() {
      return Boolean(
        this.selectedTrip?.current_member_id &&
        this.newExpense.paid_by_member_id === this.selectedTrip.current_member_id
      );
    },
    expensePreview() {
      if (!this.selectedTrip || !Number(this.newExpense.amount)) {
        return null;
      }

      const amount = Number(this.newExpense.amount || 0);
      const exchangeRate = Number(this.newExpense.exchange_rate || 0);
      const convertedAmount = amount * exchangeRate;
      const baseCurrency = this.selectedTrip.base_currency;
      const account = this.selectedPaymentAccount;
      let accountDebitText = "未連動帳戶";

      if (account) {
        const debitAmount = account.currency === this.newExpense.original_currency
          ? amount
          : convertedAmount;
        accountDebitText = `${account.bank_name} ${this.formatMoney(debitAmount, account.currency)}`;
      }

      return {
        convertedText: `${this.formatMoney(amount, this.newExpense.original_currency)} ≈ ${this.formatMoney(convertedAmount, baseCurrency)}`,
        accountDebitText,
      };
    },
    customSplitTotal() {
      return Object.values(this.newExpense.split_allocations || {})
        .reduce((sum, amount) => sum + Number(amount || 0), 0);
    },
    customSplitDifference() {
      return Number(this.newExpense.amount || 0) - this.customSplitTotal;
    },
    splitMemberSummary() {
      const selectedCount = this.newExpense.split_member_ids.length;
      const totalCount = this.selectedTrip?.members.length || 0;
      if (selectedCount === 0) {
        return "尚未選擇分帳成員";
      }
      if (selectedCount === 1) {
        const selectedMemberId = this.newExpense.split_member_ids[0];
        const selectedMember = this.selectedTrip?.members.find((member) => member.id === selectedMemberId);
        if (selectedMemberId === this.selectedTrip?.current_member_id) {
          return "僅自己負擔";
        }
        return selectedMember ? `僅 ${selectedMember.display_name} 負擔` : "僅 1 人負擔";
      }
      if (selectedCount === totalCount) {
        return `全員均分 ${selectedCount} 人`;
      }
      return `選擇 ${selectedCount}/${totalCount} 人均分`;
    },
    currentTripMember() {
      if (!this.selectedTrip?.current_member_id) return null;
      return this.selectedTrip.members.find(
        (member) => member.id === this.selectedTrip.current_member_id
      ) || null;
    },
    isTripOwner() {
      return this.currentTripMember?.role === "owner";
    },
    canCreateTripTransaction() {
      return ["owner", "editor"].includes(this.currentTripMember?.role);
    },
  },
  watch: {
    "newExpense.original_currency"() {
      this.applyDefaultExchangeRate();
      if (
        this.newExpense.account_id &&
        !this.compatibleTripAccounts.some((account) => account.id === this.newExpense.account_id)
      ) {
        this.newExpense.account_id = "";
      }
    },
    "newExpense.paid_by_member_id"() {
      if (!this.isCurrentUserPayer) {
        this.newExpense.account_id = "";
      }
    },
    activeSection(section) {
      this.ensureActiveSectionData(section);
    },
  },
  methods: {
    accountTypeOrder(type) {
      const order = ["bank", "cash", "credit_card", "e_wallet", "prepaid_card", "investment", "external", "other"];
      const index = order.indexOf(type);
      return index === -1 ? order.length : index;
    },
    groupAccountsByType(accounts) {
      const groups = [];
      for (const account of accounts) {
        let group = groups.find((item) => item.type === account.type);
        if (!group) {
          group = {
            type: account.type,
            label: this.translateAccountType(account.type),
            accounts: [],
          };
          groups.push(group);
        }
        group.accounts.push(account);
      }
      return groups;
    },
    setSplitMode(mode) {
      this.newExpense.split_mode = mode;
      if (mode === "custom") {
        this.showSplitMemberOptions = false;
        this.initializeCustomSplitAllocations();
      }
    },
    initializeCustomSplitAllocations() {
      if (!this.selectedTrip) return;
      const amount = Number(this.newExpense.amount || 0);
      const members = this.selectedTrip.members;
      const allocations = {};
      const splitMemberIds = this.newExpense.split_member_ids.length > 0
        ? this.newExpense.split_member_ids
        : this.getDefaultSplitMemberIds();

      members.forEach((member) => {
        allocations[member.id] = 0;
      });

      if (amount > 0 && splitMemberIds.length > 0) {
        const baseShare = Math.floor(amount / splitMemberIds.length);
        const remainder = amount % splitMemberIds.length;
        splitMemberIds.forEach((memberId, index) => {
          allocations[memberId] = baseShare + (index === 0 ? remainder : 0);
        });
      }

      this.newExpense.split_allocations = allocations;
    },
    getDefaultSplitMemberIds() {
      if (!this.selectedTrip) return [];
      const defaultMemberId = this.selectedTrip.current_member_id ||
        this.newExpense.paid_by_member_id ||
        this.selectedTrip.members[0]?.id ||
        "";
      return defaultMemberId ? [defaultMemberId] : [];
    },
    getDefaultExchangeRate(originalCurrency, baseCurrency) {
      if (!originalCurrency || !baseCurrency || originalCurrency === baseCurrency) {
        return 1;
      }

      const defaultRates = {
        "JPY:TWD": 0.22,
        "KRW:TWD": 0.023,
        "USD:TWD": 32,
        "EUR:TWD": 35,
        "TWD:JPY": 4.55,
        "TWD:KRW": 43.5,
        "TWD:USD": 0.031,
        "TWD:EUR": 0.029,
        "USD:JPY": 145,
        "JPY:USD": 0.0069,
        "EUR:JPY": 158,
        "JPY:EUR": 0.0063,
        "USD:EUR": 0.92,
        "EUR:USD": 1.09,
        "KRW:JPY": 0.11,
        "JPY:KRW": 9.1,
      };

      return defaultRates[`${originalCurrency}:${baseCurrency}`] || 1;
    },
    applyDefaultExchangeRate() {
      if (!this.selectedTrip) return;
      this.newExpense.exchange_rate = this.getDefaultExchangeRate(
        this.newExpense.original_currency,
        this.selectedTrip.base_currency
      );
    },
    normalizeActiveSection() {
      if (!this.operationTabs.some((tab) => tab.key === this.activeSection)) {
        this.activeSection = this.operationTabs[0]?.key || "transactions";
      }
    },
    async fetchTrips() {
      this.loading = true;
      try {
        const response = await apiClient.get("/api/trips");
        this.trips = response.data.data || [];
        if (this.trips.length > 0) {
          const currentId = this.selectedTrip && this.selectedTrip.id;
          const routeTripId = this.$route.query.trip_id;
          const nextTrip = this.trips.find((trip) => trip.id === routeTripId)
            || this.trips.find((trip) => trip.id === currentId)
            || this.trips[0];
          await this.selectTrip(nextTrip.id);
        } else {
          this.selectedTrip = null;
        }
      } catch (error) {
        console.error("無法載入旅行資料", error);
        this.trips = [];
        this.selectedTrip = null;
      } finally {
        this.loading = false;
      }
    },
    async fetchManagedTrips() {
      try {
        const response = await apiClient.get("/api/trips?include_archived=true&include_deleted=true");
        this.managedTrips = response.data.data || [];
      } catch (error) {
        console.error("無法載入旅行管理資料", error);
        this.managedTrips = [];
      }
    },
    async toggleTripManagement() {
      this.showTripManagement = !this.showTripManagement;
      if (this.showTripManagement) {
        await this.fetchManagedTrips();
      }
    },
    async selectTrip(tripId) {
      try {
        const response = await apiClient.get(`/api/trips/${tripId}/overview`);
        this.applyTripOverview(response.data.data);
        await this.ensureActiveSectionData(this.activeSection);
      } catch (error) {
        console.error("無法載入旅行明細", error);
      }
    },
    applyTripOverview(overview) {
      this.selectedTrip = overview.trip;
      this.tripTransactions = overview.transactions || [];
      this.splitSummary = overview.split_summary || [];
      this.settlementSuggestions = overview.settlement_suggestions || [];
      this.settlementRecords = overview.settlements || [];
      this.splitDetailsLoaded = false;
      this.inviteStatusLoaded = false;
      this.activeInvite = overview.invite || null;
      this.latestInviteUrl = "";
      this.selectedTransactionDetail = null;
      this.selectedTransactionDate = "all";
      this.showTripManagement = false;
      this.normalizeActiveSection();
      this.prepareExpenseDefaults();
      this.memberMessage = "";
      if (this.activeInvite) {
        this.inviteStatusLoaded = true;
        this.inviteMessage = "安全起見，既有邀請連結只在建立當下顯示；若遺失可關閉後重建。";
      } else {
        this.inviteMessage = "";
      }
    },
    async ensureActiveSectionData(section = this.activeSection) {
      if (!this.selectedTrip) return;
      if (section === "split" && !this.splitDetailsLoaded) {
        await this.fetchSplitState();
      }
      if (section === "members" && !this.inviteStatusLoaded) {
        await this.fetchTripInvite();
      }
    },
    async switchTrip(tripId) {
      await this.selectTrip(tripId);
      this.showTripSwitcher = false;
    },
    async createTrip() {
      this.submittingTrip = true;
      this.tripMessage = "";
      try {
        const response = await apiClient.post("/api/trips", this.newTrip);
        const createdTrip = response.data.data;
        this.tripMessage = response.data.message;
        this.trips = [
          createdTrip,
          ...this.trips.filter((trip) => trip.id !== createdTrip.id),
        ];
        await this.selectTrip(createdTrip.id);
        this.newTrip.name = "";
        this.newTrip.destination = "";
        this.showCreateTrip = false;
        this.activeSection = "expense";
      } catch (error) {
        this.tripMessage = error.response?.data?.message || "旅行建立失敗";
      } finally {
        this.submittingTrip = false;
      }
    },
    async toggleSelectedTripReportScope() {
      if (!this.selectedTrip || this.updatingTripSettings) return;

      const nextValue = !this.selectedTrip.include_in_monthly_report;
      const result = await this.$swal.fire({
        title: nextValue ? "計入日常統計？" : "改為旅行獨立統計？",
        text: nextValue
          ? "此旅行支出會一起出現在首頁與收支統計中。"
          : "此旅行支出將只保留在旅行帳本內，不併入日常統計。",
        icon: "question",
        showCancelButton: true,
        confirmButtonText: nextValue ? "計入日常統計" : "改為獨立統計",
        cancelButtonText: "取消",
      });
      if (!result.isConfirmed) return;

      this.updatingTripSettings = true;
      try {
        const response = await apiClient.patch(`/api/trips/${this.selectedTrip.id}`, {
          include_in_monthly_report: nextValue,
        });
        const updatedTrip = response.data.data;
        this.selectedTrip = {
          ...this.selectedTrip,
          ...updatedTrip,
        };
        this.trips = this.trips.map((trip) => (
          trip.id === updatedTrip.id ? { ...trip, ...updatedTrip } : trip
        ));
        this.$swal.fire("已更新", response.data.message || "旅行設定已更新。", "success");
      } catch (error) {
        this.$swal.fire(
          "更新失敗",
          error.response?.data?.message || "請稍後再試。",
          "error"
        );
      } finally {
        this.updatingTripSettings = false;
      }
    },
    async addMember() {
      if (!this.selectedTrip) return;
      this.submittingMember = true;
      this.memberMessage = "";
      try {
        const response = await apiClient.post(
          `/api/trips/${this.selectedTrip.id}/members`,
          this.newMember
        );
        this.memberMessage = response.data.message;
        this.selectedTrip.members = [
          ...this.selectedTrip.members,
          response.data.data,
        ];
        this.newMember.display_name = "";
        this.newMember.role = "viewer";
        this.prepareExpenseDefaults();
      } catch (error) {
        this.memberMessage = error.response?.data?.message || "旅伴新增失敗";
      } finally {
        this.submittingMember = false;
      }
    },
    async deleteMember(member) {
      if (!this.selectedTrip) return;
      const result = await this.$swal.fire({
        title: "刪除旅伴？",
        text: `確定要刪除 ${member.display_name}？已有付款、分攤或結算紀錄的旅伴會被系統阻擋。`,
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "刪除",
        cancelButtonText: "取消",
      });
      if (!result.isConfirmed) return;

      try {
        const response = await apiClient.delete(
          `/api/trips/${this.selectedTrip.id}/members/${member.id}`
        );
        this.memberMessage = response.data.message;
        this.selectedTrip.members = this.selectedTrip.members.filter(
          (tripMember) => tripMember.id !== member.id
        );
        this.prepareExpenseDefaults();
      } catch (error) {
        this.$swal.fire(
          "刪除失敗",
          error.response?.data?.message || "旅伴刪除失敗，請稍後再試。",
          "error"
        );
      }
    },
    async updateMemberRole(member, role) {
      if (!this.selectedTrip || member.role === role) return;
      try {
        const response = await apiClient.patch(
          `/api/trips/${this.selectedTrip.id}/members/${member.id}/role`,
          { role }
        );
        this.memberMessage = response.data.message;
        this.selectedTrip.members = this.selectedTrip.members.map((tripMember) => (
          tripMember.id === member.id ? response.data.data : tripMember
        ));
        this.normalizeActiveSection();
      } catch (error) {
        this.$swal.fire("更新失敗", error.response?.data?.message || "權限更新失敗", "error");
        await this.selectTrip(this.selectedTrip.id);
      }
    },
    async leaveSelectedTrip() {
      if (!this.selectedTrip || !this.currentTripMember) return;
      const result = await this.$swal.fire({
        title: "退出旅行帳本？",
        text: `退出後將不會在列表看到 ${this.selectedTrip.name}，有效邀請連結仍可重新加入。`,
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "退出",
        cancelButtonText: "取消",
      });
      if (!result.isConfirmed) return;

      try {
        await apiClient.post(`/api/trips/${this.selectedTrip.id}/leave`);
        this.selectedTrip = null;
        await this.fetchTrips();
        this.$swal.fire("已退出", "你已離開此旅行帳本。", "success");
      } catch (error) {
        this.$swal.fire("退出失敗", error.response?.data?.message || "請稍後再試", "error");
      }
    },
    async fetchTripInvite() {
      this.activeInvite = null;
      this.latestInviteUrl = "";
      this.inviteMessage = "";
      if (!this.selectedTrip || !this.isTripOwner) {
        this.inviteStatusLoaded = true;
        return;
      }

      try {
        const response = await apiClient.get(`/api/trips/${this.selectedTrip.id}/invite`);
        this.activeInvite = response.data.data || null;
        if (this.activeInvite) {
          this.inviteMessage = "安全起見，既有邀請連結只在建立當下顯示；若遺失可關閉後重建。";
        }
        this.inviteStatusLoaded = true;
      } catch (error) {
        this.inviteMessage = error.response?.data?.message || "無法載入邀請狀態";
        this.inviteStatusLoaded = false;
      }
    },
    async createInvite() {
      if (!this.selectedTrip) return;
      this.submittingInvite = true;
      this.inviteMessage = "";
      try {
        const response = await apiClient.post(`/api/trips/${this.selectedTrip.id}/invite`, {
          role: "editor",
        });
        this.activeInvite = response.data.data;
        this.latestInviteUrl = this.activeInvite.invite_url || "";
        this.inviteStatusLoaded = true;
        this.inviteMessage = "邀請連結已建立，請複製後傳給旅伴。";
      } catch (error) {
        this.inviteMessage = error.response?.data?.message || "邀請連結建立失敗";
      } finally {
        this.submittingInvite = false;
      }
    },
    async closeInvite() {
      if (!this.selectedTrip) return;
      const result = await this.$swal.fire({
        title: "關閉邀請連結？",
        text: "關閉後，舊連結將無法再加入此帳本。",
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "關閉",
        cancelButtonText: "取消",
      });
      if (!result.isConfirmed) return;

      try {
        await apiClient.delete(`/api/trips/${this.selectedTrip.id}/invite`);
        this.activeInvite = null;
        this.latestInviteUrl = "";
        this.inviteStatusLoaded = true;
        this.inviteMessage = "邀請連結已關閉。";
      } catch (error) {
        this.inviteMessage = error.response?.data?.message || "邀請連結關閉失敗";
      }
    },
    async copyInviteLink() {
      if (!this.latestInviteUrl) return;
      try {
        await this.writeTextToClipboard(this.latestInviteUrl);
        this.$swal.fire("已複製", "邀請連結已複製到剪貼簿。", "success");
      } catch (error) {
        this.$swal.fire({
          title: "請手動複製",
          html: `<textarea class="swal-copy-textarea" readonly>${this.latestInviteUrl}</textarea>`,
          icon: "info",
          confirmButtonText: "我知道了",
          didOpen: () => {
            const textarea = document.querySelector(".swal-copy-textarea");
            textarea?.focus();
            textarea?.select();
          },
        });
      }
    },
    async fetchExpenseCategories() {
      try {
        const response = await apiClient.get("/api/budgets/categories");
        this.expenseCategories = (response.data.data || []).filter((category) => category !== "收入");
        if (!this.expenseCategories.includes(this.newExpense.budget_category)) {
          this.newExpense.budget_category = this.expenseCategories[0] || "伙食";
        }
      } catch (error) {
        console.error("無法載入交易類別", error);
        this.expenseCategories = ["伙食", "交通", "住宿", "購物", "娛樂", "醫療", "工作", "生活", "其他"];
      }
    },
    async fetchAssets() {
      try {
        const response = await apiClient.get("/api/assets");
        this.assets = response.data.data || {};
      } catch (error) {
        console.error("無法載入帳戶資料", error);
        this.assets = {};
      }
    },
    async fetchTripTransactions() {
      if (!this.selectedTrip) return;
      try {
        const response = await apiClient.get(`/api/transactions?trip_id=${this.selectedTrip.id}&limit=50`);
        this.tripTransactions = response.data.data || [];
        this.syncSelectedTransactionDate();
        if (
          this.selectedTransactionDetail &&
          !this.tripTransactions.some((transaction) => transaction.id === this.selectedTransactionDetail.id)
        ) {
          this.selectedTransactionDetail = null;
        }
      } catch (error) {
        console.error("無法載入旅行交易", error);
        this.tripTransactions = [];
        this.selectedTransactionDate = "all";
      }
    },
    syncSelectedTransactionDate() {
      if (this.selectedTransactionDate === "all") return;
      const hasSelectedDate = this.tripTransactions.some(
        (transaction) => transaction.date === this.selectedTransactionDate
      );
      if (!hasSelectedDate) {
        this.selectedTransactionDate = "all";
      }
    },
    async loadTransactionDetail(transactionId, options = {}) {
      if (!options.force && this.selectedTransactionDetail && this.selectedTransactionDetail.id === transactionId) {
        this.selectedTransactionDetail = null;
        return;
      }

      try {
        const response = await apiClient.get(`/api/transactions/${transactionId}`);
        this.selectedTransactionDetail = response.data.data;
      } catch (error) {
        this.$swal.fire("載入失敗", error.response?.data?.message || "請稍後再試", "error");
      }
    },
    async startEditTransaction(transactionId) {
      try {
        if (this.settlementRecords.length > 0) {
          const result = await this.$swal.fire({
            title: "此旅行已有確認結算",
            text: "修改交易可能會影響剩餘待收/待付金額，但不會自動撤銷已確認付款。",
            icon: "warning",
            showCancelButton: true,
            confirmButtonText: "仍要編輯",
            cancelButtonText: "取消",
          });
          if (!result.isConfirmed) return;
        }

        const response = await apiClient.get(`/api/transactions/${transactionId}`);
        const transaction = response.data.data;
        if (transaction.can_edit === false) {
          await this.fetchTripTransactions();
          this.$swal.fire("沒有編輯權限", "你目前只能檢視這筆交易。", "warning");
          return;
        }
        const splitMethod = transaction.splits[0]?.split_method || "equal";

        this.editingTransactionId = transaction.id;
        this.newExpense.date = transaction.date;
        this.newExpense.item = transaction.category;
        this.newExpense.merchant = transaction.merchant || "";
        this.newExpense.budget_category = transaction.budget_category;
        this.newExpense.amount = transaction.amount;
        this.newExpense.original_currency = transaction.currency;
        this.newExpense.exchange_rate = transaction.exchange_rate;
        this.newExpense.paid_by_member_id = transaction.paid_by_member_id || "";
        this.newExpense.account_id = transaction.account_id || "";
        this.newExpense.description = transaction.description || "";
        this.newExpense.review_status = transaction.review_status || "confirmed";
        this.newExpense.split_mode = splitMethod === "custom" ? "custom" : "equal";
        this.newExpense.split_member_ids = transaction.splits.map((split) => split.trip_member_id);
        this.newExpense.split_allocations = transaction.splits.reduce((allocations, split) => {
          allocations[split.trip_member_id] = split.share_amount;
          return allocations;
        }, {});
        this.selectedTransactionDetail = transaction;
        this.showExpenseAdvanced = true;
        this.showSplitMemberOptions = false;
        this.activeSection = "expense";
      } catch (error) {
        this.$swal.fire("載入失敗", error.response?.data?.message || "請稍後再試", "error");
      }
    },
    cancelEditExpense() {
      this.resetExpenseForm();
      this.expenseMessage = "";
    },
    async fetchSplitSummary() {
      if (!this.selectedTrip) return;
      try {
        const response = await apiClient.get(`/api/trips/${this.selectedTrip.id}/split-summary`);
        this.splitSummary = response.data.data || [];
      } catch (error) {
        console.error("無法載入分帳狀態", error);
        this.splitSummary = [];
      }
    },
    async fetchSplitState() {
      if (!this.selectedTrip) return;
      try {
        const response = await apiClient.get(`/api/trips/${this.selectedTrip.id}/split-state`);
        const splitState = response.data.data || {};
        this.splitSummary = splitState.split_summary || [];
        this.settlementSuggestions = splitState.settlement_suggestions || [];
        this.settlementRecords = splitState.settlements || [];
        this.splitDetailsLoaded = true;
      } catch (error) {
        console.error("無法載入分帳狀態", error);
        this.splitDetailsLoaded = false;
      }
    },
    invalidateSplitDetails() {
      this.splitDetailsLoaded = false;
      this.settlementSuggestions = [];
      this.settlementRecords = [];
    },
    async fetchSettlementSuggestions() {
      if (!this.selectedTrip) return;
      try {
        const response = await apiClient.get(`/api/trips/${this.selectedTrip.id}/settlement-suggestions`);
        this.settlementSuggestions = response.data.data || [];
      } catch (error) {
        console.error("無法載入建議結算", error);
        this.settlementSuggestions = [];
      }
    },
    async fetchSettlements() {
      if (!this.selectedTrip) return;
      try {
        const response = await apiClient.get(`/api/trips/${this.selectedTrip.id}/settlements`);
        this.settlementRecords = response.data.data || [];
      } catch (error) {
        console.error("無法載入已確認結算", error);
        this.settlementRecords = [];
      }
    },
    prepareExpenseDefaults() {
      if (!this.selectedTrip) return;
      const owner = this.selectedTrip.members.find((member) => member.role === "owner");
      this.newExpense.original_currency = this.selectedTrip.default_currency;
      this.applyDefaultExchangeRate();
      this.newExpense.paid_by_member_id = owner ? owner.id : this.selectedTrip.members[0]?.id || "";
      if (this.selectedTrip.current_member_id) {
        this.newExpense.paid_by_member_id = this.selectedTrip.current_member_id;
      }
      if (
        this.newExpense.account_id &&
        !this.compatibleTripAccounts.some((account) => account.id === this.newExpense.account_id)
      ) {
        this.newExpense.account_id = "";
      }
      this.newExpense.split_member_ids = this.getDefaultSplitMemberIds();
      this.initializeCustomSplitAllocations();
    },
    buildExpensePayload() {
      const splitAllocations = Object.entries(this.newExpense.split_allocations || {})
        .map(([memberId, amount]) => ({
          trip_member_id: memberId,
          amount: Number(amount || 0),
        }))
        .filter((allocation) => allocation.amount > 0);

      return {
        date: this.newExpense.date,
        item: this.newExpense.item,
        amount: this.newExpense.amount,
        type: "expense",
        budget_category: this.newExpense.budget_category,
        description: this.newExpense.description,
        review_status: this.newExpense.review_status,
        trip_id: this.selectedTrip.id,
        paid_by_member_id: this.newExpense.paid_by_member_id,
        account_id: this.newExpense.account_id,
        merchant: this.newExpense.merchant,
        original_currency: this.newExpense.original_currency,
        exchange_rate: this.newExpense.exchange_rate,
        timezone: this.selectedTrip.timezone,
        split_member_ids: this.newExpense.split_mode === "equal" ? this.newExpense.split_member_ids : undefined,
        split_allocations: this.newExpense.split_mode === "custom" ? splitAllocations : undefined,
      };
    },
    resetExpenseForm() {
      this.newExpense.item = "";
      this.newExpense.merchant = "";
      this.newExpense.amount = null;
      this.newExpense.description = "";
      this.newExpense.review_status = "confirmed";
      this.editingTransactionId = null;
      this.showExpenseAdvanced = false;
      this.showSplitMemberOptions = false;
      this.prepareExpenseDefaults();
    },
    async addTripExpense() {
      if (!this.selectedTrip) return;

      const validationMessage = this.validateTripExpenseForm();
      if (validationMessage) {
        this.expenseMessage = validationMessage;
        return;
      }

      if (this.shouldConfirmExchangeRate()) {
        const result = await this.$swal.fire({
          title: "確認匯率？",
          text: `${this.newExpense.original_currency} 與 ${this.selectedTrip.base_currency} 不同，但目前匯率為 1。請確認是否仍要送出。`,
          icon: "warning",
          showCancelButton: true,
          confirmButtonText: "仍要送出",
          cancelButtonText: "返回修改",
        });
        if (!result.isConfirmed) return;
      }

      this.submittingExpense = true;
      this.expenseMessage = "";
      try {
        const payload = this.buildExpensePayload();
        const response = this.editingTransactionId
          ? await apiClient.put(`/api/transactions/${this.editingTransactionId}`, payload)
          : await apiClient.post("/api/transactions", payload);
        this.expenseMessage = response.data.message;
        this.resetExpenseForm();
        if (this.activeSection === "split") {
          await Promise.all([
            this.fetchTripTransactions(),
            this.fetchSplitState(),
            this.fetchAssets(),
          ]);
        } else {
          await Promise.all([
            this.fetchTripTransactions(),
            this.fetchSplitSummary(),
            this.fetchAssets(),
          ]);
          this.invalidateSplitDetails();
        }
        if (this.selectedTransactionDetail) {
          await this.loadTransactionDetail(this.selectedTransactionDetail.id, { force: true });
        }
        this.activeSection = "transactions";
      } catch (error) {
        this.$swal.fire(
          this.editingTransactionId ? "更新失敗" : "新增失敗",
          error.response?.data?.message || "旅行支出儲存失敗，請稍後再試。",
          "error"
        );
      } finally {
        this.submittingExpense = false;
      }
    },
    validateTripExpenseForm() {
      if (!this.newExpense.paid_by_member_id) {
        return "請選擇付款人。";
      }
      if (this.newExpense.split_mode === "equal" && this.newExpense.split_member_ids.length === 0) {
        return "請至少選擇一位分帳成員。";
      }
      if (this.newExpense.split_mode === "custom") {
        if (this.customSplitTotal <= 0) {
          return "請輸入自訂分帳金額。";
        }
        if (this.customSplitDifference !== 0) {
          return `自訂分帳合計需等於交易金額，目前差額 ${this.formatMoney(this.customSplitDifference, this.newExpense.original_currency)}。`;
        }
      }
      return "";
    },
    shouldConfirmExchangeRate() {
      return (
        this.newExpense.original_currency !== this.selectedTrip.base_currency &&
        Number(this.newExpense.exchange_rate) === 1
      );
    },
    async deleteTripTransaction(transaction) {
      try {
        const permissionResponse = await apiClient.get(`/api/transactions/${transaction.id}`);
        if (permissionResponse.data.data?.can_delete === false) {
          await this.fetchTripTransactions();
          this.$swal.fire("沒有刪除權限", "你目前只能檢視這筆交易。", "warning");
          return;
        }
      } catch (error) {
        this.$swal.fire("檢查權限失敗", error.response?.data?.message || "請稍後再試", "error");
        return;
      }

      const result = await this.$swal.fire({
        title: "刪除交易？",
        text: `${transaction.category} · ${this.formatMoney(transaction.amount, transaction.currency)}`,
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "刪除",
        cancelButtonText: "取消",
      });
      if (!result.isConfirmed) return;

      try {
        await apiClient.delete(`/api/transactions/${transaction.id}`);
        if (this.activeSection === "split") {
          await Promise.all([
            this.fetchTripTransactions(),
            this.fetchSplitState(),
            this.fetchAssets(),
          ]);
        } else {
          await Promise.all([
            this.fetchTripTransactions(),
            this.fetchSplitSummary(),
            this.fetchAssets(),
          ]);
          this.invalidateSplitDetails();
        }
      } catch (error) {
        this.$swal.fire("刪除失敗", error.response?.data?.message || "請稍後再試", "error");
      }
    },
    async confirmSettlement(suggestion) {
      const result = await this.$swal.fire({
        title: "標記為已付款？",
        html: `
          <p>${suggestion.from_display_name} 付給 ${suggestion.to_display_name}</p>
          <strong>${this.formatMoney(suggestion.amount, suggestion.currency)}</strong>
          <p style="margin-top: 8px; color: #64748b; font-size: 0.9rem;">只更新分帳狀態，不會異動任何帳戶餘額。</p>
        `,
        icon: "question",
        showCancelButton: true,
        confirmButtonText: "標記已付款",
        cancelButtonText: "取消",
      });
      if (!result.isConfirmed) return;

      try {
        await apiClient.post(`/api/trips/${this.selectedTrip.id}/settlements`, {
          from_member_id: suggestion.from_member_id,
          to_member_id: suggestion.to_member_id,
          amount: suggestion.amount,
        });
        await this.fetchSplitState();
      } catch (error) {
        this.$swal.fire("確認失敗", error.response?.data?.message || "請稍後再試", "error");
      }
    },
    async deleteSettlement(settlement) {
      const result = await this.$swal.fire({
        title: "撤銷結算？",
        text: `${settlement.from_display_name} 付給 ${settlement.to_display_name} ${this.formatMoney(settlement.amount, settlement.currency)}`,
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "撤銷",
        cancelButtonText: "取消",
      });
      if (!result.isConfirmed) return;

      try {
        await apiClient.delete(`/api/trips/${this.selectedTrip.id}/settlements/${settlement.id}`);
        await this.fetchSplitState();
      } catch (error) {
        this.$swal.fire("撤銷失敗", error.response?.data?.message || "請稍後再試", "error");
      }
    },
    buildSettlementSummaryText() {
      if (!this.selectedTrip) return "";
      const lines = [
        `${this.selectedTrip.name} 結算摘要`,
        `整團花費：${this.formatMoney(this.tripExpenseTotal, this.selectedTrip.base_currency)}`,
        `我的成本：${this.formatMoney(this.myTripShareAmount, this.selectedTrip.base_currency)}`,
        `${this.myTripNetStatus.label}：${this.formatMoney(Math.abs(this.myTripNetAmount), this.selectedTrip.base_currency)}（${this.myTripNetStatus.hint}）`,
        "",
        "建議結算：",
      ];

      if (this.settlementSuggestions.length === 0) {
        lines.push("目前已平衡或尚無需結算");
      } else {
        this.settlementSuggestions.forEach((suggestion) => {
          lines.push(
            `${suggestion.from_display_name} → ${suggestion.to_display_name}：${this.formatMoney(suggestion.amount, suggestion.currency)}`
          );
        });
      }

      return lines.join("\n");
    },
    async writeTextToClipboard(text) {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        return;
      }

      const textarea = document.createElement("textarea");
      textarea.value = text;
      textarea.setAttribute("readonly", "");
      textarea.style.position = "fixed";
      textarea.style.top = "-9999px";
      textarea.style.left = "-9999px";
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();

      const copied = document.execCommand("copy");
      document.body.removeChild(textarea);
      if (!copied) {
        throw new Error("copy command failed");
      }
    },
    async copySettlementSummary() {
      const text = this.buildSettlementSummaryText();
      if (!text) return;

      try {
        await this.writeTextToClipboard(text);
        this.$swal.fire("已複製", "結算摘要已複製到剪貼簿。", "success");
      } catch (error) {
        this.$swal.fire({
          title: "請手動複製",
          html: `<textarea class="swal-copy-textarea" readonly>${text}</textarea>`,
          icon: "info",
          confirmButtonText: "我知道了",
          didOpen: () => {
            const textarea = document.querySelector(".swal-copy-textarea");
            textarea?.focus();
            textarea?.select();
          },
        });
      }
    },
    async archiveSelectedTrip() {
      if (!this.selectedTrip) return;
      const result = await this.$swal.fire({
        title: "封存旅行帳本？",
        text: `${this.selectedTrip.name} 會保留資料，但不再作為主要操作帳本。`,
        icon: "question",
        showCancelButton: true,
        confirmButtonText: "封存帳本",
        cancelButtonText: "取消",
      });
      if (!result.isConfirmed) return;

      try {
        await apiClient.post(`/api/trips/${this.selectedTrip.id}/archive`);
        await this.fetchTrips();
        await this.fetchManagedTrips();
        this.showTripManagement = true;
        this.$swal.fire("已封存", "可在旅行管理的已封存帳本中解除封存。", "success");
      } catch (error) {
        this.$swal.fire("封存失敗", error.response?.data?.message || "請稍後再試", "error");
      }
    },
    async deleteSelectedTrip() {
      if (!this.selectedTrip) return;
      const result = await this.$swal.fire({
        title: "刪除旅行帳本？",
        html: `<p>會先保留 30 天。若要刪除，請輸入帳本名稱：</p><strong>${this.selectedTrip.name}</strong>`,
        input: "text",
        inputPlaceholder: this.selectedTrip.name,
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "刪除帳本",
        cancelButtonText: "取消",
        preConfirm: (value) => {
          if (value !== this.selectedTrip.name) {
            this.$swal.showValidationMessage("請輸入完整旅行名稱");
            return false;
          }
          return value;
        },
      });
      if (!result.isConfirmed) return;

      try {
        await apiClient.delete(`/api/trips/${this.selectedTrip.id}`);
        await this.fetchTrips();
        await this.fetchManagedTrips();
        this.showTripManagement = true;
        this.$swal.fire("已移至暫存區", "30 天內可在旅行管理的已刪除帳本中復原。", "success");
      } catch (error) {
        this.$swal.fire("刪除失敗", error.response?.data?.message || "請稍後再試", "error");
      }
    },
    async unarchiveTrip(trip) {
      const result = await this.$swal.fire({
        title: "解除封存？",
        text: `${trip.name} 會回到主要旅行帳本列表。`,
        icon: "question",
        showCancelButton: true,
        confirmButtonText: "解除封存",
        cancelButtonText: "取消",
      });
      if (!result.isConfirmed) return;

      try {
        await apiClient.post(`/api/trips/${trip.id}/unarchive`);
        await this.fetchTrips();
        await this.fetchManagedTrips();
        this.showTripManagement = true;
        this.$swal.fire("已解除封存", `${trip.name} 已回到主要旅行帳本列表。`, "success");
      } catch (error) {
        this.$swal.fire("解除封存失敗", error.response?.data?.message || "請稍後再試", "error");
      }
    },
    async restoreTrip(trip) {
      const result = await this.$swal.fire({
        title: "復原旅行帳本？",
        text: `${trip.name} 會回到原本狀態。`,
        icon: "question",
        showCancelButton: true,
        confirmButtonText: "復原",
        cancelButtonText: "取消",
      });
      if (!result.isConfirmed) return;

      try {
        await apiClient.post(`/api/trips/${trip.id}/restore`);
        await this.fetchTrips();
        await this.fetchManagedTrips();
        this.showTripManagement = true;
        this.$swal.fire("已復原", `${trip.name} 已回到旅行帳本。`, "success");
      } catch (error) {
        this.$swal.fire("復原失敗", error.response?.data?.message || "請稍後再試", "error");
      }
    },
    formatRange(trip) {
      return `${trip.start_date} - ${trip.end_date}`;
    },
    tripReportLabel(trip) {
      return trip?.include_in_monthly_report ? "計入日常統計" : "旅行獨立統計";
    },
    formatDateChip(dateString) {
      if (!dateString) return "";
      const parts = String(dateString).split("-");
      if (parts.length !== 3) return dateString;
      const month = Number(parts[1]);
      const day = Number(parts[2]);
      if (!Number.isFinite(month) || !Number.isFinite(day)) return dateString;
      return `${month}/${day}`;
    },
    formatDateTime(value) {
      if (!value) return "";
      return new Date(value).toLocaleDateString("zh-TW", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
      });
    },
    tripDays(trip) {
      const start = new Date(trip.start_date);
      const end = new Date(trip.end_date);
      const diff = end.getTime() - start.getTime();
      return Math.max(Math.round(diff / 86400000) + 1, 1);
    },
    translateRole(role) {
      const roleMap = {
        owner: "擁有者",
        editor: "編輯",
        viewer: "檢視",
      };
      return roleMap[role] || role;
    },
    translateReviewStatus(status) {
      const statusMap = {
        confirmed: "已確認",
        pending: "待確認",
      };
      return statusMap[status] || status || "未設定";
    },
    getMemberName(memberId) {
      if (!memberId || !this.selectedTrip) return "";
      const member = this.selectedTrip.members.find((item) => item.id === memberId);
      return member?.display_name || "";
    },
    escapeCsvValue(value) {
      const text = value === null || value === undefined ? "" : String(value);
      return `"${text.replace(/"/g, '""')}"`;
    },
    buildTripTransactionsCsv() {
      const headers = [
        "日期",
        "品項",
        "店家",
        "類別",
        "付款人",
        "原幣金額",
        "原幣",
        "匯率",
        "換算金額",
        "本幣",
        "付款帳戶",
        "備註",
      ];
      const rows = this.tripTransactions.map((transaction) => [
        transaction.date,
        transaction.category,
        transaction.merchant || "",
        transaction.budget_category || "",
        this.getMemberName(transaction.paid_by_member_id),
        transaction.amount,
        transaction.currency,
        transaction.exchange_rate,
        transaction.converted_amount,
        transaction.base_currency,
        transaction.account_name || "",
        transaction.description || "",
      ]);
      return [headers, ...rows]
        .map((row) => row.map((value) => this.escapeCsvValue(value)).join(","))
        .join("\n");
    },
    downloadCsv(csv) {
      const blob = new Blob([`\uFEFF${csv}`], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      const safeName = this.selectedTrip.name.replace(/[\\/:*?"<>|]/g, "_");
      link.href = url;
      link.download = `${safeName}-transactions.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    },
    async exportTripTransactionsCsv() {
      if (!this.selectedTrip || this.tripTransactions.length === 0) return;

      const csv = this.buildTripTransactionsCsv();
      this.downloadCsv(csv);

      const result = await this.$swal.fire({
        title: "CSV 已產生",
        text: "如果瀏覽器沒有跳出下載，可能是目前測試瀏覽器限制下載行為，可以改用複製 CSV 內容。",
        icon: "success",
        showCancelButton: true,
        confirmButtonText: "複製 CSV",
        cancelButtonText: "完成",
      });
      if (!result.isConfirmed) return;

      try {
        await this.writeTextToClipboard(csv);
        this.$swal.fire("已複製", "CSV 內容已複製到剪貼簿。", "success");
      } catch (error) {
        this.$swal.fire({
          title: "請手動複製",
          html: `<textarea class="swal-copy-textarea" readonly>${csv}</textarea>`,
          icon: "info",
          confirmButtonText: "我知道了",
          didOpen: () => {
            const textarea = document.querySelector(".swal-copy-textarea");
            textarea?.focus();
            textarea?.select();
          },
        });
      }
    },
    splitStatusClass(member) {
      const netAmount = Number(member.net_amount || 0);
      if (netAmount > 0) {
        return "receivable";
      }
      if (netAmount < 0) {
        return "payable";
      }
      return "balanced";
    },
    splitNetStatus(member) {
      const netAmount = Number(member.net_amount || 0);
      if (netAmount > 0) return "待收";
      if (netAmount < 0) return "待付";
      return "已平衡";
    },
    translateAccountType(type) {
      const typeMap = {
        bank: "銀行",
        cash: "現金",
        credit_card: "信用卡",
        e_wallet: "電子錢包",
        prepaid_card: "預付卡",
        external: "外部帳戶",
        investment: "投資",
        other: "其他",
      };
      return typeMap[type] || type || "其他";
    },
    formatMoney(amount, currency) {
      const minorUnit = ["TWD", "JPY", "KRW"].includes(currency) ? 0 : 2;
      return `${currency} ${Number(amount || 0).toLocaleString("zh-TW", {
        minimumFractionDigits: minorUnit,
        maximumFractionDigits: minorUnit,
      })}`;
    },
    formatMyTransactionShare(transaction) {
      const currentMemberId = this.selectedTrip?.current_member_id;
      if (!currentMemberId) return "尚未對應";
      const split = transaction.splits.find((item) => item.trip_member_id === currentMemberId);
      if (!split) return "未分攤";
      return this.formatMoney(split.converted_share_amount, split.base_currency);
    },
  },
  created() {
    this.fetchExpenseCategories();
    this.fetchAssets();
    this.fetchTrips();
  },
};
</script>

<style scoped>
.trips-page {
  max-width: 720px;
  margin: 0 auto;
  min-height: calc(100vh - 80px);
  padding: 24px 16px calc(var(--app-bottom-nav-height) + 22px);
  color: #1f2933;
}

.trips-header,
.trip-hero,
.section-title,
.metric-item,
.danger-row {
  display: flex;
  align-items: center;
}

.trips-header {
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.header-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
}

.eyebrow {
  margin: 0 0 4px;
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
}

h1,
h2,
h3 {
  margin: 0;
  letter-spacing: 0;
}

h1 {
  font-size: 2rem;
}

.icon-button,
.new-trip-button,
.primary-action,
.secondary-action,
.quiet-action,
.danger-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 42px;
  border-radius: 8px;
  box-shadow: none;
}

.icon-button {
  width: 44px;
  padding: 0;
  color: #0f766e;
  background: #ccfbf1;
}

.new-trip-button {
  padding: 0 14px;
  color: #ffffff;
  background: #0f766e;
}

.create-panel,
.trip-detail {
  background: #ffffff;
  border: 1px solid #dbe4ee;
  border-radius: 8px;
  padding: 16px;
}

.create-panel {
  margin-bottom: 16px;
}

.section-title {
  gap: 8px;
  margin-bottom: 14px;
  color: #334155;
}

.split-title-row {
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 12px;
}

.split-title-row > div {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.copy-summary-button {
  flex: 0 0 auto;
  min-height: 34px;
  padding: 0 10px;
  color: #0f766e;
  background: #ccfbf1;
  border-radius: 8px;
  box-shadow: none;
  font-size: 0.84rem;
  font-weight: 800;
}

:deep(.swal-copy-textarea) {
  width: 100%;
  min-height: 180px;
  padding: 10px 12px;
  color: #111827;
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font: inherit;
  line-height: 1.5;
  resize: vertical;
}

.section-title svg,
.metric-item svg,
.primary-action svg,
.secondary-action svg,
.icon-button svg {
  width: 18px;
  height: 18px;
}

.trip-form,
.member-form,
.expense-form {
  display: grid;
  gap: 12px;
}

.trip-form {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
  color: #475569;
  font-size: 0.9rem;
  font-weight: 700;
}

input,
select {
  box-sizing: border-box;
  min-height: 42px;
  min-width: 0;
  max-width: 100%;
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 8px 10px;
  background: #fff;
  color: #111827;
  font-size: 1rem;
}

input[type="date"] {
  appearance: none;
  -webkit-appearance: none;
  line-height: 1.2;
}

input[type="date"]::-webkit-date-and-time-value {
  min-height: 1.2em;
  text-align: left;
}

input[type="date"]::-webkit-calendar-picker-indicator {
  margin: 0;
}

select:disabled {
  cursor: not-allowed;
  color: #94a3b8;
  background: #f1f5f9;
}

.toggle-row {
  flex-direction: row;
  align-items: center;
  min-height: 42px;
}

.toggle-row input {
  width: 18px;
  min-height: 18px;
}

.field-hint {
  margin: -4px 0 0;
  color: #64748b;
  font-size: 0.84rem;
  line-height: 1.45;
}

.primary-action {
  align-self: end;
  background: #0f766e;
}

.secondary-action {
  background: #2563eb;
}

.quiet-action {
  color: #334155;
  background: #e2e8f0;
}

.danger-action {
  background: #dc2626;
}

.status-message,
.loading-state,
.empty-state {
  margin: 12px 0 0;
  color: #475569;
}

.trips-layout {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}

.trip-detail {
  display: grid;
  gap: 16px;
}

.current-trip-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 86px;
  padding: 12px;
  background: #ffffff;
  border: 1px solid #dbe4ee;
  border-radius: 8px;
}

.current-trip-card > div,
.switcher-row > div {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.current-trip-actions {
  display: flex;
  flex: 0 0 auto;
  flex-direction: column;
  gap: 8px;
}

.current-trip-card strong,
.switcher-row strong {
  color: #1f2933;
  font-size: 1rem;
}

.current-trip-card span,
.switcher-row span {
  color: #64748b;
  font-size: 0.86rem;
}

.trip-compact-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 5px;
}

.trip-compact-meta span {
  min-height: 24px;
  padding: 3px 8px;
  color: #334155;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 800;
}

.trip-state-badge {
  justify-self: start;
  min-height: 26px;
  padding: 4px 8px;
  color: #475569;
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 800;
}

.trip-state-badge.included {
  color: #0f766e;
  background: #ecfdf5;
  border-color: #99f6e4;
}

.trip-hero {
  justify-content: space-between;
  gap: 12px;
  padding: 14px;
  color: #ffffff;
  background: linear-gradient(135deg, #0f766e, #2563eb);
  border-radius: 8px;
}

.trip-hero .eyebrow {
  color: #dbeafe;
}

.trip-hero p {
  margin: 6px 0 0;
}

.currency-pill {
  flex: 0 0 auto;
  padding: 8px 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.18);
  font-weight: 800;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.metric-item {
  gap: 8px;
  min-height: 54px;
  padding: 10px;
  color: #334155;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-weight: 700;
}

.trip-tabs {
  position: sticky;
  top: 74px;
  z-index: 5;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(0, 1fr));
  gap: 6px;
  padding: 6px;
  background: #e2e8f0;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
}

.trip-tabs button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 42px;
  padding: 0 8px;
  color: #475569;
  background: transparent;
  border-radius: 6px;
  box-shadow: none;
  font-size: 0.92rem;
}

.trip-tabs button.active {
  color: #0f766e;
  background: #ffffff;
}

.trip-tabs svg {
  width: 17px;
  height: 17px;
}

.app-panel {
  display: none;
}

.app-panel.active {
  display: block;
}

.member-list {
  display: grid;
  gap: 8px;
  margin-bottom: 12px;
}

.member-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 44px;
  padding: 10px 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.member-row > div {
  flex: 1 1 auto;
  display: grid;
  gap: 2px;
  min-width: 0;
}

.member-row span {
  color: #1f2933;
  font-weight: 800;
}

.member-row small {
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 700;
}

.member-delete {
  flex: 0 0 34px;
  width: 34px;
  min-height: 34px;
  padding: 0;
  color: #dc2626;
  background: #fee2e2;
  border-radius: 8px;
  box-shadow: none;
}

.member-delete svg {
  width: 16px;
  height: 16px;
}

.member-role-select {
  flex: 0 0 96px;
  min-height: 34px;
  padding: 0 8px;
  border: 1px solid #dbe4ee;
  border-radius: 8px;
  background: #ffffff;
  font-size: 0.85rem;
}

.invite-panel {
  display: grid;
  gap: 10px;
  margin: 0 0 12px;
  padding: 12px;
  background: #f0fdfa;
  border: 1px solid #99f6e4;
  border-radius: 8px;
}

.invite-panel > div:first-child {
  display: grid;
  gap: 3px;
}

.invite-panel strong {
  color: #134e4a;
}

.invite-panel span {
  color: #475569;
  font-size: 0.86rem;
  line-height: 1.45;
}

.invite-status-row,
.invite-copy-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.invite-status-row {
  justify-content: space-between;
}

.invite-copy-row input {
  min-width: 0;
  flex: 1;
  min-height: 42px;
  border: 1px solid #dbe4ee;
  border-radius: 8px;
  padding: 0 10px;
  background: #ffffff;
}

.leave-trip-button {
  width: 100%;
}

.member-form {
  grid-template-columns: minmax(0, 1fr) 120px auto;
}

.expense-form {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.full-row {
  grid-column: 1 / -1;
}

.quick-currency-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.quick-currency-row button,
.advanced-toggle {
  min-height: 38px;
  padding: 0 12px;
  color: #475569;
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  box-shadow: none;
}

.quick-currency-row button.active {
  color: #ffffff;
  background: #0f766e;
  border-color: #0f766e;
}

.advanced-toggle {
  width: 100%;
  color: #334155;
  background: #e2e8f0;
  font-weight: 800;
}

.advanced-expense-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.split-box {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  color: #475569;
  font-weight: 700;
}

.account-link-hint {
  margin: -4px 0 0;
  padding: 10px 12px;
  color: #475569;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.88rem;
  font-weight: 700;
}

.split-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  width: 100%;
}

.split-mode-tabs {
  display: inline-grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
  padding: 4px;
  background: #e2e8f0;
  border-radius: 8px;
}

.split-mode-tabs button {
  min-height: 34px;
  padding: 0 12px;
  color: #475569;
  background: transparent;
  border-radius: 6px;
  box-shadow: none;
}

.split-mode-tabs button.active {
  color: #0f766e;
  background: #ffffff;
}

.split-member-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  width: 100%;
  min-height: 40px;
  padding: 0 12px;
  color: #334155;
  text-align: left;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  box-shadow: none;
}

.split-member-toggle span,
.split-member-toggle strong {
  font-size: 0.88rem;
  font-weight: 800;
}

.split-member-toggle strong {
  color: #0f766e;
}

.split-member-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  width: 100%;
}

.custom-split-list {
  display: grid;
  gap: 8px;
  width: 100%;
}

.custom-split-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 140px;
  align-items: center;
  min-height: 44px;
  padding: 8px 10px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
}

.custom-split-row input {
  min-height: 38px;
}

.custom-split-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  color: #0f766e;
  background: #ecfdf5;
  border: 1px solid #99f6e4;
  border-radius: 8px;
}

.custom-split-summary.invalid {
  color: #b91c1c;
  background: #fef2f2;
  border-color: #fecaca;
}

.expense-preview {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.expense-preview > div {
  display: grid;
  gap: 4px;
  min-height: 64px;
  padding: 12px;
  background: #f0fdfa;
  border: 1px solid #99f6e4;
  border-radius: 8px;
}

.expense-preview span {
  color: #0f766e;
  font-size: 0.82rem;
  font-weight: 800;
}

.expense-preview strong {
  color: #134e4a;
  font-size: 1rem;
  line-height: 1.35;
}

.split-option {
  flex-direction: row;
  align-items: center;
  width: auto;
  min-height: 34px;
  padding: 6px 10px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-weight: 600;
}

.split-option input {
  width: 16px;
  min-height: 16px;
}

.split-option:has(input:checked) {
  color: #0f766e;
  background: #ecfdf5;
  border-color: #99f6e4;
}

.trip-summary-grid {
  display: grid;
  grid-template-columns: 1.15fr 1fr 1fr;
  gap: 10px;
}

.trip-category-panel {
  display: block;
}

.trip-summary-compact {
  display: none;
}

.summary-card {
  display: grid;
  gap: 4px;
  min-height: 72px;
  padding: 12px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-left: 4px solid #cbd5e1;
  border-radius: 8px;
  color: #475569;
}

.summary-card.share {
  background: #f8feff;
  border-color: #bae6fd;
  border-left-color: #0891b2;
  color: #0e7490;
}

.summary-card.group {
  background: #f8fafc;
  border-color: #cbd5e1;
  border-left-color: #475569;
  color: #334155;
}

.summary-card.positive {
  background: #f0fdf4;
  border-color: #bbf7d0;
  border-left-color: #16a34a;
}

.summary-card.negative {
  background: #fff1f2;
  border-color: #fecdd3;
  border-left-color: #e11d48;
}

.summary-card.balanced {
  background: #f8fafc;
  border-color: #cbd5e1;
  border-left-color: #94a3b8;
}

.summary-card span {
  font-size: 0.86rem;
  font-weight: 700;
}

.summary-card strong {
  color: #111827;
  font-size: 1.08rem;
  line-height: 1.25;
}

.summary-card small {
  color: #64748b;
  font-size: 0.76rem;
  font-weight: 700;
}

.trip-closeout-panel {
  display: grid;
  gap: 10px;
  margin-bottom: 14px;
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-left: 5px solid #94a3b8;
  border-radius: 8px;
}

.trip-closeout-panel.success {
  background: #f0fdf4;
  border-color: #bbf7d0;
  border-left-color: #16a34a;
}

.trip-closeout-panel.warning {
  background: #fffbeb;
  border-color: #fde68a;
  border-left-color: #f59e0b;
}

.trip-closeout-panel.neutral {
  background: #f8fafc;
  border-color: #cbd5e1;
  border-left-color: #94a3b8;
}

.closeout-header,
.closeout-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.closeout-header span {
  color: #334155;
  font-weight: 900;
}

.closeout-header strong,
.closeout-item strong {
  font-weight: 900;
}

.closeout-header strong {
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 0.82rem;
}

.closeout-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.closeout-item {
  min-height: 40px;
  padding: 8px 10px;
  background: #ffffff;
  border: 1px solid #dbe4ee;
  border-left: 4px solid #94a3b8;
  border-radius: 8px;
}

.closeout-item span {
  color: #64748b;
  font-size: 0.82rem;
  font-weight: 800;
}

.closeout-item.success {
  background: #ffffff;
  border-color: #bbf7d0;
  border-left-color: #16a34a;
}

.closeout-item.warning {
  background: #fff7ed;
  border-color: #fed7aa;
  border-left-color: #f59e0b;
}

.closeout-item.neutral {
  background: #ffffff;
  border-color: #dbe4ee;
  border-left-color: #94a3b8;
}

.closeout-header .success,
.closeout-item.success strong {
  color: #15803d;
}

.closeout-header .success {
  background: #dcfce7;
}

.closeout-header .warning,
.closeout-item.warning strong {
  color: #b45309;
}

.closeout-header .warning {
  background: #fef3c7;
}

.closeout-header .neutral,
.closeout-item.neutral strong {
  color: #64748b;
}

.closeout-header .neutral {
  background: #e2e8f0;
}

.transaction-list {
  display: grid;
  gap: 8px;
}

.transaction-date-tabs {
  position: relative;
  z-index: 1;
  display: flex;
  gap: 8px;
  clear: both;
  margin: 4px 0 14px;
  padding: 2px 0 4px;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}

.transaction-date-tabs::-webkit-scrollbar {
  display: none;
}

.transaction-date-tabs button {
  display: grid;
  gap: 2px;
  flex: 0 0 auto;
  min-width: 68px;
  min-height: 48px;
  padding: 6px 10px;
  color: #475569;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  box-shadow: none;
}

.transaction-date-tabs button.active {
  color: #ffffff;
  background: #0f766e;
  border-color: #0f766e;
}

.transaction-date-tabs span {
  font-size: 0.86rem;
  font-weight: 900;
}

.transaction-date-tabs small {
  font-size: 0.72rem;
  font-weight: 800;
  opacity: 0.82;
}

.transaction-row,
.split-summary-row,
.settlement-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  min-height: 62px;
  padding: 10px 12px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.transaction-row {
  cursor: pointer;
}

.transaction-row.selected {
  border-color: #0f766e;
  background: #f0fdfa;
}

.transaction-row div:first-child,
.transaction-amount,
.split-summary-row div:first-child {
  display: grid;
  gap: 2px;
}

.transaction-row span,
.transaction-amount small,
.split-summary-row span {
  color: #64748b;
}

.transaction-amount {
  text-align: right;
  flex: 0 0 auto;
}

.transaction-amount span {
  color: #111827;
  font-weight: 800;
}

.transaction-delete,
.transaction-edit {
  flex: 0 0 38px;
  width: 38px;
  min-height: 38px;
  padding: 0;
  border-radius: 8px;
  box-shadow: none;
}

.transaction-delete {
  color: #dc2626;
  background: #fee2e2;
}

.transaction-edit {
  color: #0f766e;
  background: #ccfbf1;
}

.transaction-delete svg,
.transaction-edit svg {
  width: 18px;
  height: 18px;
}

.split-summary-list {
  display: grid;
  gap: 8px;
}

.split-summary-row.receivable {
  background: #ecfdf5;
  border-color: #99f6e4;
}

.split-summary-row.receivable span {
  color: #0f766e;
}

.split-summary-row.payable {
  background: #fff1f2;
  border-color: #fecdd3;
}

.split-summary-row.payable span {
  color: #be123c;
}

.split-summary-row.balanced {
  background: #f8fafc;
  border-color: #e2e8f0;
}

.split-summary-row.balanced span {
  color: #64748b;
}

.net-amount {
  display: grid;
  gap: 2px;
  min-width: 96px;
  text-align: right;
}

.net-amount small {
  color: #64748b;
  font-size: 0.76rem;
  font-weight: 800;
}

.settlement-title {
  margin-top: 18px;
}

.detail-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-height: 44px;
  padding: 10px 12px;
  color: #334155;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  box-shadow: none;
}

.detail-toggle span {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 0.96rem;
  font-weight: 800;
}

.detail-toggle svg {
  width: 18px;
  height: 18px;
  color: #0f766e;
}

.detail-toggle strong {
  color: #64748b;
  font-size: 0.82rem;
}

.settlement-list {
  display: grid;
  gap: 8px;
}

.settlement-action-row {
  align-items: stretch;
  background: #eff6ff;
  border-color: #bfdbfe;
}

.settlement-route {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.settlement-route strong {
  color: #1e40af;
  font-size: 1rem;
}

.settlement-route strong:first-child {
  text-align: left;
}

.settlement-route strong:last-child {
  text-align: right;
}

.settlement-route span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  color: #1d4ed8;
  background: #dbeafe;
  border-radius: 999px;
  font-weight: 900;
}

.settlement-row {
  background: #eff6ff;
  border-color: #bfdbfe;
}

.settlement-row.settled {
  background: #f0fdfa;
  border-color: #99f6e4;
}

.settlement-row span {
  color: #1e40af;
  font-weight: 700;
}

.settlement-row.settled span {
  color: #0f766e;
}

.settlement-row strong {
  color: #1d4ed8;
}

.settlement-row.settled strong {
  color: #0f766e;
}

.settlement-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.confirm-settlement-button,
.quiet-mini-button {
  min-height: 32px;
  padding: 0 10px;
  border: 0;
  border-radius: 8px;
  box-shadow: none;
  font-size: 0.86rem;
  font-weight: 800;
}

.confirm-settlement-button {
  color: #ffffff;
  background: #2563eb;
}

.quiet-mini-button {
  color: #475569;
  background: #e2e8f0;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}

.detail-grid > div {
  display: grid;
  gap: 2px;
  min-height: 54px;
  padding: 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.detail-grid span,
.split-detail-row span,
.split-detail-row small {
  color: #64748b;
}

.split-detail-list {
  display: grid;
  gap: 8px;
}

.split-detail-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  min-height: 48px;
  padding: 10px 12px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.split-detail-row strong {
  display: grid;
  gap: 2px;
  text-align: right;
}

.positive-net {
  color: #0f766e;
}

.negative-net {
  color: #dc2626;
}

.danger-row {
  justify-content: flex-end;
  gap: 10px;
}

.trip-management {
  display: grid;
  gap: 10px;
  padding-top: 4px;
}

.management-toggle {
  min-height: 42px;
  color: #334155;
  background: #f8fafc;
  border: 1px solid #dbe4ee;
  border-radius: 8px;
  box-shadow: none;
  font-weight: 800;
}

.management-panel {
  display: grid;
  gap: 12px;
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #dbe4ee;
  border-radius: 8px;
}

.standalone-management {
  margin-bottom: 16px;
}

.management-panel > div:first-child {
  display: grid;
  gap: 3px;
}

.management-panel span {
  color: #64748b;
  font-size: 0.88rem;
  font-weight: 700;
}

.managed-trip-group {
  display: grid;
  gap: 8px;
  padding-top: 10px;
  border-top: 1px solid #e2e8f0;
}

.managed-trip-heading,
.managed-trip-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.managed-trip-heading span {
  color: #64748b;
  font-size: 0.82rem;
}

.managed-empty {
  padding: 10px 12px;
  color: #64748b;
  background: #ffffff;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  font-weight: 700;
}

.managed-trip-list {
  display: grid;
  gap: 8px;
}

.managed-trip-row {
  min-height: 58px;
  padding: 10px 12px;
  background: #ffffff;
  border: 1px solid #dbe4ee;
  border-radius: 8px;
}

.managed-trip-row.deleted {
  background: #fff7ed;
  border-color: #fed7aa;
}

.managed-trip-row > div {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.managed-trip-row > div span {
  color: #64748b;
  font-size: 0.82rem;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: grid;
  align-items: end;
  padding: 16px;
  background: rgba(15, 23, 42, 0.42);
}

.trip-switcher {
  width: min(520px, 100%);
  max-height: 78vh;
  margin: 0 auto;
  padding: 16px;
  overflow: auto;
  background: #ffffff;
  border-radius: 10px;
}

.switcher-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.trip-switcher-list {
  display: grid;
  gap: 8px;
}

.switcher-row {
  width: 100%;
  min-height: 82px;
  padding: 12px;
  color: #1f2933;
  text-align: left;
  background: #ffffff;
  border: 1px solid #dbe4ee;
  border-left: 4px solid #94a3b8;
  border-radius: 8px;
  box-shadow: none;
}

.switcher-row.active {
  border-left-color: #0f766e;
  background: #f0fdfa;
}

@media (max-width: 820px) {
  .trips-page {
    padding: 18px 12px calc(var(--app-bottom-nav-height) + 22px);
  }

  .trip-form,
  .trips-layout,
  .metric-grid,
  .trip-summary-grid,
  .member-form,
  .expense-form,
  .advanced-expense-grid,
  .expense-preview,
  .detail-grid {
    grid-template-columns: 1fr;
  }

  .closeout-list {
    grid-template-columns: 1fr;
  }

  .trip-summary-compact {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    min-height: 46px;
    padding: 10px 12px;
    color: #334155;
    text-align: left;
    background: #ffffff;
    border: 1px solid #dbe4ee;
    border-left: 4px solid #0f766e;
    border-radius: 8px;
    box-shadow: none;
  }

  .trip-summary-compact span,
  .trip-summary-compact strong {
    overflow: hidden;
    font-size: 0.9rem;
    line-height: 1.25;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .trip-summary-compact span {
    min-width: 0;
    color: #475569;
    font-weight: 800;
  }

  .trip-summary-compact strong {
    flex: 0 0 auto;
    max-width: 46%;
  }

  .trip-summary-grid {
    display: none;
  }

  .trip-summary-grid.expanded {
    display: grid;
  }

  .trip-category-panel {
    display: none;
  }

  .trip-category-panel.expanded {
    display: block;
  }

  .trip-hero {
    align-items: flex-start;
    flex-direction: column;
  }

  .trips-header {
    align-items: flex-start;
  }

  .trips-header h1 {
    font-size: 1.6rem;
  }

  .header-actions {
    gap: 6px;
  }

  .new-trip-button {
    min-width: 72px;
    padding: 0 10px;
  }

  .current-trip-card {
    align-items: stretch;
    flex-direction: column;
    min-height: auto;
  }

  .current-trip-actions,
  .current-trip-card .quiet-action,
  .current-trip-card .secondary-action {
    width: 100%;
  }

  .trip-tabs {
    top: 0;
    margin: 0 -4px;
  }

  .trip-tabs button {
    flex-direction: column;
    gap: 2px;
    min-height: 50px;
    padding: 4px 2px;
    font-size: 0.78rem;
  }

  .member-form {
    grid-template-columns: minmax(0, 1fr) 108px;
  }

  .member-form .secondary-action {
    grid-column: 1 / -1;
  }

  .member-row {
    align-items: center;
    flex-wrap: nowrap;
    gap: 8px;
  }

  .member-role-select {
    flex: 0 0 32%;
    max-width: 128px;
    min-width: 92px;
  }

  .invite-status-row,
  .invite-copy-row {
    align-items: stretch;
    flex-direction: column;
  }

  .invite-copy-row .secondary-action {
    width: 100%;
  }

  .danger-row {
    justify-content: stretch;
  }

  .danger-row button {
    flex: 1;
  }

  .managed-trip-row {
    align-items: stretch;
    flex-direction: column;
  }

  .split-summary-row,
  .settlement-row {
    align-items: flex-start;
    flex-direction: column;
  }

  .settlement-action-row {
    gap: 10px;
  }

  .settlement-route {
    width: 100%;
  }

  .settlement-actions {
    width: 100%;
    justify-content: space-between;
    margin-left: 0;
  }

  .transaction-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto 38px;
    align-items: center;
  }

  .transaction-row div:first-child {
    min-width: 0;
  }

  .transaction-row div:first-child span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .transaction-amount {
    width: auto;
    text-align: right;
  }

  .split-header,
  .custom-split-summary {
    align-items: stretch;
    flex-direction: column;
  }

  .split-mode-tabs,
  .custom-split-row {
    width: 100%;
  }

  .custom-split-row {
    grid-template-columns: 1fr;
  }

  .transaction-delete {
    align-self: center;
  }
}
</style>
