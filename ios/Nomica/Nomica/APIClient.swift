import Foundation

struct APIClient {
    let baseURL: URL
    let authToken: String?
    let devUser: String

    func getAuthMe() async throws -> AuthUser {
        let envelope: APIEnvelope<AuthMeData> = try await get("/api/auth/me")
        return envelope.data.user
    }

    func getDashboardOverview() async throws -> DashboardOverview {
        let envelope: APIEnvelope<DashboardOverview> = try await get("/api/dashboard/overview")
        return envelope.data
    }

    func getAccounts() async throws -> [Account] {
        let envelope: APIEnvelope<[String: Account]> = try await get("/api/assets")
        return envelope.data.values.sorted { $0.displayName < $1.displayName }
    }

    func getTransactions() async throws -> [Transaction] {
        let envelope: APIEnvelope<[Transaction]> = try await get("/api/transactions")
        return envelope.data.sorted { $0.dateText > $1.dateText }
    }

    private func get<T: Decodable>(_ path: String) async throws -> T {
        var request = URLRequest(url: baseURL.appendingPathComponent(path))
        request.httpMethod = "GET"
        request.timeoutInterval = 8
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue(devUser, forHTTPHeaderField: "X-Dev-User")
        if let authToken, !authToken.isEmpty {
            request.setValue("Bearer \(authToken)", forHTTPHeaderField: "Authorization")
        }

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        guard (200..<300).contains(httpResponse.statusCode) else {
            throw APIError.httpStatus(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decoding(error)
        }
    }
}

enum APIError: LocalizedError {
    case invalidResponse
    case httpStatus(Int)
    case decoding(Error)

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "後端回應格式不正確。"
        case .httpStatus(let statusCode):
            return "API 回應狀態碼 \(statusCode)。"
        case .decoding(let error):
            return "資料解析失敗：\(error.localizedDescription)"
        }
    }
}
