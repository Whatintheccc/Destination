import Foundation

public final class RewardLogger: @unchecked Sendable {
    private(set) public var events: [RewardEvent] = []

    public init() {}

    public func append(_ event: RewardEvent) {
        events.append(event)
    }

    public func totalReward() -> Double {
        events.reduce(0) { $0 + $1.totalReward }
    }

    public func undoRate() -> Double {
        guard !events.isEmpty else { return 0 }
        let undone = events.filter { $0.undone == true }.count
        return Double(undone) / Double(events.count)
    }
}
