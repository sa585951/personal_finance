import Foundation

@MainActor
final class AppSession: ObservableObject {
    @Published var baseURLText = "http://127.0.0.1:5003"
    @Published var devUser = "local-dev-user"
    @Published var authToken = ""
    @Published var authUser: AuthUser?
    @Published var isCheckingAuth = false
    @Published var authError: String?

    var apiClient: APIClient {
        APIClient(
            baseURL: URL(string: baseURLText) ?? URL(string: "http://127.0.0.1:5003")!,
            authToken: authToken.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? nil : authToken,
            devUser: devUser
        )
    }

    func checkAuth() async {
        isCheckingAuth = true
        authError = nil
        do {
            authUser = try await apiClient.getAuthMe()
        } catch {
            authUser = nil
            authError = error.localizedDescription
        }
        isCheckingAuth = false
    }
}
