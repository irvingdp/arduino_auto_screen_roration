import Foundation

struct SerialPortInfo: Identifiable, Hashable {
    var id: String { device }
    let device: String
    let description: String
}
