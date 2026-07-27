import Foundation

enum AppSessionState {
    case idle
    case checking
    case authenticated(AuthUser)
    case unauthenticated
    case failed(String)
}

@MainActor
final class AppSession: ObservableObject {
    @Published var baseURLText = "http://127.0.0.1:5001"
    @Published var devUser = "local-dev-user"
    @Published var authToken = ""
    @Published private(set) var state: AppSessionState = .idle
    
    var authUser: AuthUser? {
        guard case let .authenticated(user) = state else{
            return nil
        }
        
        return user
    }
    
    var isCheckingAuth: Bool {
        if case .checking = state{
            return true
        }
        
        return false
    }
    
    var authError: String?{
        switch state {
        case .unauthenticated:
            return "尚未登入或登入已失效"
            
        case .failed(let message):
            return message
            
        default:
            return nil
        }
    }
    var apiClient: APIClient {
        APIClient(
            baseURL: URL(string: baseURLText) ?? URL(string: "http://127.0.0.1:5001")!,
            authToken: authToken.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? nil : authToken,
            devUser: devUser
        )
    }

    func checkAuth() async {
        state = .checking
        
        do {
           let user = try await apiClient.getAuthMe()
            state = .authenticated(user)
        }catch APIError.httpStatus(let statusCode) where statusCode == 401{
            state = .unauthenticated
        } catch{
            state = .failed(error.localizedDescription)
        }
    }
}
