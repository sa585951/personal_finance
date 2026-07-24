//
//  StateViews.swift
//  Nomica
//
//  Created by 郭維哲 on 2026/7/24.
//

import SwiftUI

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
