//
//  MainTabView.swift
//  Nomica
//
//  Created by 郭維哲 on 2026/7/24.
//
import SwiftUI

struct MainTabView: View {
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
        }
    }
}

#Preview {
    MainTabView()
        .environmentObject(AppSession())
}
