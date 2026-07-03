
import Foundation

public enum StableID {
    public static func make(prefix: String, parts: [String]) -> String {
        let joined = parts.joined(separator: "|")
        let hex = String(fnv1a64(joined), radix: 16)
        return "\(prefix)_\(String(repeating: "0", count: max(0, 16 - hex.count)))\(hex)"
    }

    public static func make(prefix: String, _ parts: String...) -> String {
        make(prefix: prefix, parts: parts)
    }

    private static func fnv1a64(_ text: String) -> UInt64 {
        var hash: UInt64 = 0xcbf29ce484222325
        let prime: UInt64 = 0x100000001b3
        for byte in text.utf8 {
            hash ^= UInt64(byte)
            hash = hash &* prime
        }
        return hash
    }
}