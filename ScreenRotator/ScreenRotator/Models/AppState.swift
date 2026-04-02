import SwiftUI

@MainActor
class AppState: ObservableObject {
    @Published var ports: [SerialPortInfo] = []
    @Published var displays: [DisplayInfo] = []
    @Published var selectedPort: String = ""
    @Published var selectedDisplayID: String = ""
    @Published var isMonitoring: Bool = false
    @Published var connectionStatus: String = "Disconnected"
    @Published var connectionColor: Color = .gray
    @Published var receivedAngle: String = "-"
    @Published var lastAction: String = "-"
    @Published var debugEnabled: Bool = false
    @Published var debugLog: [DebugLogEntry] = []
    @Published var lastProcessedDegree: String? = nil
    @Published var showingDebugDisplays: Bool = false
    @Published var debugDisplaysOutput: String = ""

    var firstOriginValues: [String: String] = [:]

    private var serialService: SerialPortService?
    private let displayPlacerService = DisplayPlacerService()

    func refreshPorts() {
        ports = SerialPortService.listPorts()
        addDebugLog("Serial port list updated")
    }

    func refreshDisplays() async {
        do {
            let (parsedDisplays, _, updatedCache) = try await displayPlacerService.listDisplays(originCache: firstOriginValues)
            firstOriginValues = updatedCache
            displays = parsedDisplays
            addDebugLog("Display list updated")
        } catch {
            addDebugLog("Error fetching displays: \(error.localizedDescription)")
        }
    }

    func startMonitoring() {
        guard !selectedPort.isEmpty else {
            addDebugLog("Error: Please select a serial port")
            return
        }
        guard !selectedDisplayID.isEmpty else {
            addDebugLog("Error: Please select a display")
            return
        }

        isMonitoring = true
        lastProcessedDegree = nil
        connectionStatus = "Connecting to \(selectedPort)..."
        connectionColor = .orange
        addDebugLog("Started monitoring serial port: \(selectedPort)")

        let port = selectedPort
        let displayID = selectedDisplayID

        serialService = SerialPortService()
        serialService?.startMonitoring(port: port) { [weak self] line in
            Task { @MainActor [weak self] in
                guard let self = self else { return }
                self.handleSerialLine(line, displayID: displayID)
            }
        } onStatusChange: { [weak self] status, color in
            Task { @MainActor [weak self] in
                guard let self = self else { return }
                self.connectionStatus = status
                self.connectionColor = color
                self.addDebugLog("Connection status: \(status)")
            }
        }
    }

    func stopMonitoring() {
        isMonitoring = false
        serialService?.stopMonitoring()
        serialService = nil
        connectionStatus = "Disconnected"
        connectionColor = .gray
        addDebugLog("Stopped monitoring")
    }

    func fetchDebugDisplays() async {
        do {
            let output = try await displayPlacerService.rawListOutput()
            debugDisplaysOutput = output
            showingDebugDisplays = true
        } catch {
            debugDisplaysOutput = "Error: \(error.localizedDescription)"
            showingDebugDisplays = true
        }
    }

    func addDebugLog(_ message: String) {
        let entry = DebugLogEntry(timestamp: Date(), message: message)
        debugLog.append(entry)
    }

    func clearDebugLog() {
        debugLog.removeAll()
        addDebugLog("Log cleared")
    }

    private func handleSerialLine(_ line: String, displayID: String) {
        receivedAngle = line
        addDebugLog("Received angle: \(line)")

        if ["0", "90", "180", "270"].contains(line) {
            if line != lastProcessedDegree {
                Task {
                    do {
                        let (allDisplays, _, updatedCache) = try await displayPlacerService.listDisplays(originCache: firstOriginValues)
                        firstOriginValues = updatedCache
                        try await displayPlacerService.rotateDisplay(
                            allDisplays: allDisplays,
                            targetID: displayID,
                            degree: line
                        )
                        lastProcessedDegree = line
                        lastAction = "Success: Display set to \(line)°"
                        addDebugLog("Action: Rotated display to \(line)°")
                    } catch {
                        lastAction = "Error: \(error.localizedDescription)"
                        addDebugLog("Error rotating display: \(error.localizedDescription)")
                    }
                }
            } else {
                lastAction = "Angle unchanged, skipping rotation: \(line)°"
                addDebugLog("Action: Angle unchanged (\(line)°)")
            }
        } else if !line.isEmpty {
            addDebugLog("Received unexpected data: \(line)")
        }
    }
}

struct DebugLogEntry: Identifiable {
    let id = UUID()
    let timestamp: Date
    let message: String

    var formattedTime: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm:ss"
        return formatter.string(from: timestamp)
    }
}
