//
//  TransactionRow.swift
//  Nomica
//
//  Created by 郭維哲 on 2026/7/24.
//

import SwiftUI

struct TransactionRow: View {
    let transaction: Transaction

    var isIncome: Bool{
        transaction.type == "income"
    }

    var tint: Color{
        isIncome ? .green : .red
    }

    var body: some View {
        HStack(spacing: 12){
            Circle()
                .fill(tint.opacity(0.16))
                .frame(width: 38,height:38)
                .overlay{
                    Image(systemName: isIncome ? "arrow.down.left" : "arrow.up.right")
                        .font(.system(size: 15, weight: .bold))
                        .foregroundStyle(tint)
                }

            VStack(alignment: .leading, spacing: 4){
                Text(transaction.displayTitle)
                    .font(.headline)
                    .lineLimit(1)

                Text("\(transaction.displayCategory) · \(transaction.dateText)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }

            Spacer(minLength: 12)

            Text(transaction.amountText)
                .font(.headline)
                .foregroundStyle(tint)
                .monospacedDigit()
        }
        .padding(.vertical,6)
    }

}

private extension Transaction {
    var amountText: String {
        let prefix = type == "income" ? "+" : "-"
        return "\(prefix)\(amount.value.nomicaMoneyText)"
    }
}
