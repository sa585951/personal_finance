import Foundation

struct APIEnvelope<T: Decodable>: Decodable {
    let success: Bool
    let data: T
}

struct AuthMeData: Decodable {
    let userId: String
    let name: String?
    let provider: String?
    let sessionId: String?

    var user: AuthUser {
        AuthUser(
            id: userId,
            name: name?.isEmpty == false ? name! : "Nomica 使用者",
            provider: provider,
            sessionId: sessionId
        )
    }
}

struct AuthUser: Identifiable {
    let id: String
    let name: String
    let provider: String?
    let sessionId: String?
}

struct DashboardOverview: Decodable {
    let transactions: [Transaction]
    let monthlyReportTransactions: [Transaction]

    var currentMonthTransactions: [Transaction] {
        let prefix = Self.currentMonthPrefix
        return monthlyReportTransactions.filter { $0.dateText.hasPrefix(prefix) }
    }

    var monthlyIncome: Double {
        currentMonthTransactions
            .filter { $0.type == "income" }
            .reduce(0) { $0 + $1.amount.value }
    }

    var monthlyExpense: Double {
        currentMonthTransactions
            .filter { $0.type == "expense" }
            .reduce(0) { $0 + $1.amount.value }
    }

    var monthlyBalance: Double {
        monthlyIncome - monthlyExpense
    }

    var recentTransactions: [Transaction] {
        Array(transactions.prefix(5))
    }

    private static var currentMonthPrefix: String {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM"
        return formatter.string(from: Date())
    }
}

struct Transaction: Decodable, Identifiable {
    let id: String
    let date: String?
    let type: String
    let category: String?
    let title: String?
    let budgetCategory: String?
    let amount: FlexibleDouble
    let currency: String?
    let accountName: String?
    let accountType: String?

    var dateText: String {
        date ?? ""
    }

    var displayTitle: String {
        title ?? category ?? budgetCategory ?? "未命名紀錄"
    }

    var displayCategory: String {
        budgetCategory ?? category ?? "未分類"
    }
}

struct Account: Decodable, Identifiable {
    let id: String
    let name: String?
    let type: String?
    let currency: String?
    let balance: FlexibleDouble?
    let trackBalance: Bool?

    var displayName: String {
        name?.isEmpty == false ? name! : "未命名帳戶"
    }

    var displayType: String {
        switch type {
        case "cash":
            return "現金"
        case "bank":
            return "銀行"
        case "credit_card":
            return "信用卡"
        case "investment":
            return "投資"
        case "e_wallet":
            return "電子錢包"
        default:
            return type ?? "其他"
        }
    }
}

struct FlexibleDouble: Decodable {
    let value: Double

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let doubleValue = try? container.decode(Double.self) {
            value = doubleValue
        } else if let intValue = try? container.decode(Int.self) {
            value = Double(intValue)
        } else if let stringValue = try? container.decode(String.self),
                  let doubleValue = Double(stringValue) {
            value = doubleValue
        } else {
            value = 0
        }
    }
}

extension Double {
    var nomicaMoneyText: String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .decimal
        formatter.maximumFractionDigits = 2
        formatter.minimumFractionDigits = 0
        return formatter.string(from: NSNumber(value: self)) ?? "\(self)"
    }
}
