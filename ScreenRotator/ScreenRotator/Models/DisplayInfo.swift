import Foundation

struct DisplayInfo: Identifiable, Hashable {
    let id: String          // Persistent screen id
    let type: String
    let res: String
    let hz: String
    let colorDepth: String
    let scaling: String
    let origin: String
    let degree: String
    let enabled: String

    var desc: String {
        "\(type) (\(res)) - ID: \(id)"
    }
}
