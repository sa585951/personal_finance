//
//  SessionGateView.swift
//  Nomica
//
//  Created by 郭維哲 on 2026/7/27.
//

import SwiftUI

struct SessionGateView: View {
    @EnvironmentObject private var session: AppSession
    
    var body: some View {
        Group{
            switch session.state{
            case .idle, .checking:
                loadingView
                
            case .authenticated:
                MainTabView()
                
            case .unauthenticated:
                SessionRecoveryView(
                    title: "尚未登入",
                    message:"目前沒有有效的登入狀態",
                    systemImage:"person.crop.circle.badge.exclamationmark"
                )
            case .failed(let message):
                SessionRecoveryView(
                    title:"無法連線",
                    message: message,
                    systemImage: "wifi.exclamationmark"
                )
            }
        }
        .task{
            guard case .idle = session.state else{
                return
            }
            
            await session.checkAuth()
        }
    }
    
    private var loadingView: some View {
        VStack(spacing: 12){
            ProgressView()
            Text("正在確認登入狀態")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
    }
}

private struct SessionRecoveryView: View {
    let title: String
    let message: String
    let systemImage: String
    
    var body: some View {
        VStack(spacing: 0){
            DevSessionBar()
            
            Spacer()
            
            VStack(spacing: 12){
                Image(systemName: systemImage)
                    .font(.system(size:38))
                    .foregroundStyle(.secondary)
                
                Text(title)
                    .font(.title)
                    .foregroundStyle(.secondary)
                
                Text(message)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }
            .padding()
            
            Spacer()
        }
    }
}
