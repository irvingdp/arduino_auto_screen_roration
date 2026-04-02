import Foundation

enum DisplayPlacerParser {

    static func parseDisplays(from output: String, originCache: inout [String: String]) -> [DisplayInfo] {
        var displays: [DisplayInfo] = []
        var current: [String: String] = [:]

        for line in output.components(separatedBy: .newlines) {
            let trimmed = line.trimmingCharacters(in: .whitespaces)

            if trimmed.contains("Persistent screen id:") {
                current["id"] = extractValue(trimmed)
            } else if trimmed.hasPrefix("Type:") {
                current["type"] = extractValue(trimmed)
            } else if trimmed.hasPrefix("Resolution:") {
                current["res"] = extractValue(trimmed)
            } else if trimmed.hasPrefix("Hertz:") {
                current["hz"] = extractValue(trimmed)
            } else if trimmed.hasPrefix("Color Depth:") {
                current["color_depth"] = extractValue(trimmed)
            } else if trimmed.hasPrefix("Scaling:") {
                current["scaling"] = extractValue(trimmed)
            } else if trimmed.hasPrefix("Origin:") {
                if let displayID = current["id"] {
                    if originCache[displayID] == nil {
                        originCache[displayID] = parseOrigin(trimmed)
                    }
                    current["origin"] = originCache[displayID]
                }
            } else if trimmed.hasPrefix("Rotation:") {
                current["degree"] = parseRotation(trimmed)
            } else if trimmed.hasPrefix("Enabled:") {
                current["enabled"] = extractValue(trimmed)
            }

            let requiredKeys = ["id", "type", "res", "hz", "color_depth", "scaling", "origin", "degree", "enabled"]
            if requiredKeys.allSatisfy({ current[$0] != nil }) {
                let display = DisplayInfo(
                    id: current["id"]!,
                    type: current["type"]!,
                    res: current["res"]!,
                    hz: current["hz"]!,
                    colorDepth: current["color_depth"]!,
                    scaling: current["scaling"]!,
                    origin: current["origin"]!,
                    degree: current["degree"]!,
                    enabled: current["enabled"]!
                )
                displays.append(display)
                current = [:]
            }
        }

        return displays
    }

    private static func extractValue(_ line: String) -> String {
        guard let colonIndex = line.lastIndex(of: ":") else { return line }
        return String(line[line.index(after: colonIndex)...]).trimmingCharacters(in: .whitespaces)
    }

    static func parseRotation(_ str: String) -> String {
        let pattern = #"Rotation:\s*(\d+)"#
        guard let regex = try? NSRegularExpression(pattern: pattern),
              let match = regex.firstMatch(in: str, range: NSRange(str.startIndex..., in: str)),
              let range = Range(match.range(at: 1), in: str) else {
            return str
        }
        return String(str[range])
    }

    static func parseOrigin(_ str: String) -> String {
        let pattern = #"\([^)]+\)"#
        guard let regex = try? NSRegularExpression(pattern: pattern),
              let match = regex.firstMatch(in: str, range: NSRange(str.startIndex..., in: str)),
              let range = Range(match.range, in: str) else {
            return str
        }
        return String(str[range])
    }
}
