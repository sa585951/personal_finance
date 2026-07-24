//
//  HomeScreen.swift
//  Nomica
//
//  Created by 郭維哲 on 2026/7/24.
//

import SwiftUI

struct HomeScreen: View {
    @EnvironmentObject private var session: AppSession
    @State private var overview: DashboardOverview?
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            List {
                if let overview {
                    Section{
                        MonthlySummaryCard(overview: overview)
                            .listRowInsets(EdgeInsets())
                            .listRowBackground(Color.clear)
                    } header: {
                        Text("本月摘要")
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
