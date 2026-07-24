//
//  MonthlySummaryCard.swift
//  Nomica
//
//  Created by 郭維哲 on 2026/7/24.
//

import SwiftUI

struct MonthlySummaryCard: View{
    let overview: DashboardOverview

    var body: some View {
        VStack(alignment: .leading, spacing: 16){
            Text("本月結餘")
                .font(.caption)
                .foregroundStyle(.secondary)

            Text(overview.monthlyBalance.nomicaMoneyText)
                .font(.system(size: 34, weight: .bold, design: .rounded))
                .foregroundStyle(overview.monthlyBalance >= 0 ? .teal : .orange)

            HStack(spacing: 12){
                SummaryMetric(
                    title: "收入",
                    value: overview.monthlyIncome,
                    tint: .green
                )

                SummaryMetric(
                    title: "支出",
                    value: overview.monthlyExpense,
                    tint: .red
                )
            }
        }
        .padding(18)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .fill(Color(.secondarySystemGroupedBackground))
        )
    }
}

private struct SummaryMetric: View {
    let title: String
    let value: Double
    let tint: Color

    var body: some View{
        VStack(alignment: .leading, spacing: 6){
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)

            Text(value.nomicaMoneyText)
                .font(.headline)
                .foregroundStyle(tint)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .fill(tint.opacity(0.12))
        )
    }
}
