import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var session: AppSession

    var body: some View {
        TabView {
            HomeScreen()
                .tabItem {
                    Label("首頁", systemImage: "house.fill")
                }

            TransactionsScreen()
                .tabItem {
                    Label("收支", systemImage: "list.bullet.rectangle")
                }

            AccountsScreen()
                .tabItem {
                    Label("帳戶", systemImage: "wallet.pass.fill")
                }
        }
        .safeAreaInset(edge: .top) {
            DevSessionBar()
                .environmentObject(session)
        }
    }
}

struct DevSessionBar: View {
    @EnvironmentObject private var session: AppSession

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Nomica iOS Prototype")
                        .font(.headline)
                    Text(session.authUser.map { "已連線：\($0.name)" } ?? "Dev API 測試模式")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Button(session.isCheckingAuth ? "測試中" : "測 API") {
                    Task {
                        await session.checkAuth()
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(session.isCheckingAuth)
            }

            TextField("API Base URL", text: $session.baseURLText)
                .textFieldStyle(.roundedBorder)
                .textInputAutocapitalization(.never)
                .keyboardType(.URL)

            Picker("測試使用者", selection: $session.devUser) {
                Text("Dev User").tag("local-dev-user")
                Text("Amy").tag("amy-dev-user")
                Text("Ben").tag("ben-dev-user")
                Text("Cara").tag("cara-dev-user")
            }
            .pickerStyle(.segmented)

            if let authError = session.authError {
                Text(authError)
                    .font(.caption)
                    .foregroundStyle(.red)
            }
        }
        .padding()
        .background(.regularMaterial)
    }
}

struct HomeScreen: View {
    @EnvironmentObject private var session: AppSession
    @State private var overview: DashboardOverview?
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            List {
                if let overview {
                    Section("本月摘要") {
                        SummaryRow(label: "收入", value: overview.monthlyIncome, tint: .green)
                        SummaryRow(label: "支出", value: overview.monthlyExpense, tint: .red)
                        SummaryRow(label: "結餘", value: overview.monthlyBalance, tint: overview.monthlyBalance >= 0 ? .teal : .orange)
                    }

                    Section("最近紀錄") {
                        if overview.recentTransactions.isEmpty {
                            EmptyStateText("目前沒有最近紀錄")
                        } else {
                            ForEach(overview.recentTransactions) { transaction in
                                TransactionRow(transaction: transaction)
                            }
                        }
                    }
                } else {
                    LoadingOrEmptyState(
                        isLoading: isLoading,
                        errorMessage: errorMessage,
                        emptyText: "點右上方「測 API」確認連線，或下拉重新整理。"
                    )
                }
            }
            .navigationTitle("首頁")
            .refreshable {
                await loadOverview()
            }
            .task {
                await loadOverview()
            }
        }
    }

    private func loadOverview() async {
        isLoading = true
        errorMessage = nil
        do {
            overview = try await session.apiClient.getDashboardOverview()
        } catch {
            overview = nil
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }
}

struct TransactionsScreen: View {
    @EnvironmentObject private var session: AppSession
    @State private var transactions: [Transaction] = []
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            List {
                if transactions.isEmpty {
                    LoadingOrEmptyState(
                        isLoading: isLoading,
                        errorMessage: errorMessage,
                        emptyText: "目前沒有收支紀錄，或尚未成功連到 API。"
                    )
                } else {
                    ForEach(transactions.prefix(30)) { transaction in
                        TransactionRow(transaction: transaction)
                    }
                }
            }
            .navigationTitle("收支")
            .refreshable {
                await loadTransactions()
            }
            .task {
                await loadTransactions()
            }
        }
    }

    private func loadTransactions() async {
        isLoading = true
        errorMessage = nil
        do {
            transactions = try await session.apiClient.getTransactions()
        } catch {
            transactions = []
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }
}

struct AccountsScreen: View {
    @EnvironmentObject private var session: AppSession
    @State private var accounts: [Account] = []
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            List {
                if accounts.isEmpty {
                    LoadingOrEmptyState(
                        isLoading: isLoading,
                        errorMessage: errorMessage,
                        emptyText: "目前沒有帳戶資料，或尚未成功連到 API。"
                    )
                } else {
                    ForEach(accounts) { account in
                        HStack {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(account.displayName)
                                    .font(.headline)
                                Text("\(account.displayType) · \(account.currency ?? "TWD")")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            Spacer()
                            if account.trackBalance != false {
                                Text(account.balance?.value.nomicaMoneyText ?? "-")
                                    .font(.headline)
                            } else {
                                Text("未追蹤")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }
                        .padding(.vertical, 4)
                    }
                }
            }
            .navigationTitle("帳戶")
            .refreshable {
                await loadAccounts()
            }
            .task {
                await loadAccounts()
            }
        }
    }

    private func loadAccounts() async {
        isLoading = true
        errorMessage = nil
        do {
            accounts = try await session.apiClient.getAccounts()
        } catch {
            accounts = []
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }
}

struct SummaryRow: View {
    let label: String
    let value: Double
    let tint: Color

    var body: some View {
        HStack {
            Text(label)
            Spacer()
            Text(value.nomicaMoneyText)
                .fontWeight(.semibold)
                .foregroundStyle(tint)
        }
    }
}

struct TransactionRow: View {
    let transaction: Transaction

    var body: some View {
        HStack(alignment: .top) {
            VStack(alignment: .leading, spacing: 4) {
                Text(transaction.displayTitle)
                    .font(.headline)
                Text("\(transaction.displayCategory) · \(transaction.dateText)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Text(transaction.amountText)
                .font(.headline)
                .foregroundStyle(transaction.type == "income" ? .green : .red)
        }
        .padding(.vertical, 4)
    }
}

struct LoadingOrEmptyState: View {
    let isLoading: Bool
    let errorMessage: String?
    let emptyText: String

    var body: some View {
        if isLoading {
            ProgressView("讀取中")
        } else if let errorMessage {
            VStack(alignment: .leading, spacing: 8) {
                Text("無法讀取資料")
                    .font(.headline)
                Text(errorMessage)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .foregroundStyle(.red)
        } else {
            EmptyStateText(emptyText)
        }
    }
}

struct EmptyStateText: View {
    let text: String

    init(_ text: String) {
        self.text = text
    }

    var body: some View {
        Text(text)
            .font(.subheadline)
            .foregroundStyle(.secondary)
            .padding(.vertical, 8)
    }
}

private extension Transaction {
    var amountText: String {
        let prefix = type == "income" ? "+" : "-"
        return "\(prefix)\(amount.value.nomicaMoneyText)"
    }
}

#Preview {
    ContentView()
        .environmentObject(AppSession())
}
