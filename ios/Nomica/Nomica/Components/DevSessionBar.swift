//
//  DevSessionBar.swift
//  Nomica
//
//  Created by 郭維哲 on 2026/7/24.
//
import SwiftUI

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

