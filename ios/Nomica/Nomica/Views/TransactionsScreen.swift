//
//  TransactionsScreen.swift
//  Nomica
//
//  Created by 郭維哲 on 2026/7/24.
//

import SwiftUI

struct TransactionsScreen: View {
    @EnvironmentObject private var session: AppSession
    @State private var transactions: [Transaction] = []
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            List {
                Section {
                    HStack {
                        Text("目前 \(transactions.count) 筆")
                            .font(.caption)
                            .foregroundStyle(.secondary)

                        Spacer()

                        Button(isLoading ? "讀取中" : "重新讀取") {
                            Task {
                                await loadTransactions()
                            }
                        }
                        .font(.caption)
                        .disabled(isLoading)
                    }

                    Text("API：\(session.baseURLText)")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }

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
            .onChange(of: session.baseURLText) { _, _ in
                Task {
                    await loadTransactions()
                }
            }
            .onChange(of: session.devUser) { _, _ in
                Task {
                    await loadTransactions()
                }
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
