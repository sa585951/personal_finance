//
//  KeychainStore.swift
//  Nomica
//
//  Created by 郭維哲 on 2026/7/27.
//

import Foundation
import Security

enum KeychainStoreError: LocalizedError {
    case invalidString
    case unexpectedStatus(OSStatus)

    var errorDescription: String? {
        switch self {
        case .invalidString:
            return "無法轉換 Keychain 字串資料"

        case .unexpectedStatus(let status):
            return "Keychain 操作失敗，狀態碼：\(status)"
        }
    }
}

struct KeychainStore {
    private let service: String

    init(
        service: String = Bundle.main.bundleIdentifier
            ?? "app.nomica.prototype"
    ) {
        self.service = service
    }

    func save(_ value: String, for account: String) throws {
        guard let data = value.data(using: .utf8) else {
            throw KeychainStoreError.invalidString
        }

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]

        let attributes: [String: Any] = [
            kSecValueData as String: data,
            // Token 只能在此裝置解鎖時存取，也不會同步到其他裝置。
            kSecAttrAccessible as String:
                kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        ]

        let updateStatus = SecItemUpdate(
            query as CFDictionary,
            attributes as CFDictionary
        )

        if updateStatus == errSecSuccess {
            return
        }

        guard updateStatus == errSecItemNotFound else {
            throw KeychainStoreError.unexpectedStatus(updateStatus)
        }

        var newItem = query
        newItem.merge(attributes) { _, newValue in newValue }

        let addStatus = SecItemAdd(
            newItem as CFDictionary,
            nil
        )

        guard addStatus == errSecSuccess else {
            throw KeychainStoreError.unexpectedStatus(addStatus)
        }
    }

    func read(for account: String) throws -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]

        var result: CFTypeRef?

        let status = SecItemCopyMatching(
            query as CFDictionary,
            &result
        )

        if status == errSecItemNotFound {
            return nil
        }

        guard status == errSecSuccess else {
            throw KeychainStoreError.unexpectedStatus(status)
        }

        guard
            let data = result as? Data,
            let value = String(data: data, encoding: .utf8)
        else {
            throw KeychainStoreError.invalidString
        }

        return value
    }

    func delete(for account: String) throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]

        let status = SecItemDelete(query as CFDictionary)

        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw KeychainStoreError.unexpectedStatus(status)
        }
    }
}
