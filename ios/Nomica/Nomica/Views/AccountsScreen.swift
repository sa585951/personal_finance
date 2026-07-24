//
//  AccountsScreen.swift
//  Nomica
//
//  Created by 郭維哲 on 2026/7/24.
//

import SwiftUI

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
