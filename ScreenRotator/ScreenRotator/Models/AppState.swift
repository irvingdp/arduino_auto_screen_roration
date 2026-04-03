import SwiftUI

@MainActor
class AppState: ObservableObject {
    @Published var ports: [SerialPortInfo] = []
    @Published var displays: [DisplayInfo] = []
    @Published var selectedPort: String = "" {
        didSet { UserDefaults.standard.set(selectedPort, forKey: "lastSelectedPort") }
    }
    @Published var selectedDisplayID: String = "" {
        didSet { UserDefaults.standard.set(selectedDisplayID, forKey: "lastSelectedDisplayID") }
    }
    @Published var isMonitoring: Bool = false
    @Published var connectionStatus: String = "Disconnected"
    @Published var connectionColor: Color = .gray
    @Published var receivedAngle: String = "-"
    @Published var lastAction: String = "-"
    @Published var debugEnabled: Bool = true
    @Published var debugLog: [DebugLogEntry] = []
    @Published var lastProcessedDegree: String? = nil
    @Published var showingDebugDisplays: Bool = false
    @Published var debugDisplaysOutput: String = ""

    var firstOriginValues: [String: String] = [:]

    private var serialService: SerialPortService?
    private let displayPlacerService = DisplayPlacerService()

    private var savedPort: String { UserDefaults.standard.string(forKey: "lastSelectedPort") ?? "" }
    private var savedDisplayID: String { UserDefaults.standard.string(forKey: "lastSelectedDisplayID") ?? "" }

    func refreshPorts() {
        addDebugLog("[App] refreshPorts called")
        ports = SerialPortService.listPorts()
        addDebugLog("[App] Found \(ports.count) port(s): \(ports.map { "\($0.device) (\($0.description))" }.joined(separator: ", "))")
        autoSelectPort()
    }

    func refreshDisplays() async {
        addDebugLog("[App] refreshDisplays called")
        do {
            let (parsedDisplays, rawOutput, updatedCache) = try await displayPlacerService.listDisplays(originCache: firstOriginValues)
            firstOriginValues = updatedCache
            displays = parsedDisplays
            addDebugLog("[App] Found \(parsedDisplays.count) display(s): \(parsedDisplays.map { $0.desc }.joined(separator: "; "))")
            if parsedDisplays.isEmpty {
                addDebugLog("[App] WARNING: 0 displays parsed. Raw output length=\(rawOutput.count). First 200 chars: \(String(rawOutput.prefix(200)))")
            }
            autoSelectDisplay()
        } catch {
            addDebugLog("[App] ERROR fetching displays: \(error.localizedDescription)")
        }
    }

    private func autoSelectPort() {
        guard selectedPort.isEmpty || !ports.contains(where: { $0.device == selectedPort }) else { return }

        // Restore last saved selection if still available
        if !savedPort.isEmpty, ports.contains(where: { $0.device == savedPort }) {
            selectedPort = savedPort
            addDebugLog("[App] Restored last port: \(savedPort)")
            return
        }

        // Auto-select: prefer Arduino, otherwise pick the only one
        if let arduino = ports.first(where: { $0.description.lowercased().contains("arduino") }) {
            selectedPort = arduino.device
            addDebugLog("[App] Auto-selected Arduino port: \(arduino.device)")
        } else if ports.count == 1 {
            selectedPort = ports[0].device
            addDebugLog("[App] Auto-selected only port: \(ports[0].device)")
        }
    }

    private func autoSelectDisplay() {
        guard selectedDisplayID.isEmpty || !displays.contains(where: { $0.id == selectedDisplayID }) else { return }

        // Restore last saved selection if still available
        if !savedDisplayID.isEmpty, displays.contains(where: { $0.id == savedDisplayID }) {
            selectedDisplayID = savedDisplayID
            addDebugLog("[App] Restored last display: \(savedDisplayID)")
            return
        }

        // Auto-select if only one display
        if displays.count == 1 {
            selectedDisplayID = displays[0].id
            addDebugLog("[App] Auto-selected only display: \(displays[0].desc)")
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
        } onLog: { [weak self] message in
            Task { @MainActor [weak self] in
                self?.addDebugLog(message)
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
        addDebugLog("[App] fetchDebugDisplays called")
        do {
            let output = try await displayPlacerService.rawListOutput()
            debugDisplaysOutput = output
            showingDebugDisplays = true
            addDebugLog("[App] fetchDebugDisplays OK, output length=\(output.count)")
        } catch {
            debugDisplaysOutput = "Error: \(error.localizedDescription)"
            showingDebugDisplays = true
            addDebugLog("[App] fetchDebugDisplays ERROR: \(error.localizedDescription)")
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
        addDebugLog("[Handle] Received: '\(line)' (len=\(line.count), bytes=\(Array(line.utf8)))")

        if ["0", "90", "180", "270"].contains(line) {
            addDebugLog("[Handle] Valid angle: \(line), lastProcessed=\(lastProcessedDegree ?? "nil")")
            if line != lastProcessedDegree {
                addDebugLog("[Handle] Angle changed, will rotate display \(displayID) to \(line)°")
                Task {
                    do {
                        addDebugLog("[Handle] Fetching display list...")
                        let (allDisplays, _, updatedCache) = try await displayPlacerService.listDisplays(originCache: firstOriginValues)
                        firstOriginValues = updatedCache
                        addDebugLog("[Handle] Got \(allDisplays.count) displays, calling rotateDisplay...")
                        try await displayPlacerService.rotateDisplay(
                            allDisplays: allDisplays,
                            targetID: displayID,
                            degree: line
                        )
                        lastProcessedDegree = line
                        lastAction = "Success: Display set to \(line)°"
                        addDebugLog("[Handle] Rotation SUCCESS: \(line)°")
                    } catch {
                        lastAction = "Error: \(error.localizedDescription)"
                        addDebugLog("[Handle] Rotation ERROR: \(error.localizedDescription)")
                    }
                }
            } else {
                lastAction = "Angle unchanged, skipping rotation: \(line)°"
                addDebugLog("[Handle] Angle unchanged (\(line)°), skipping")
            }
        } else if !line.isEmpty {
            addDebugLog("[Handle] Unexpected data: '\(line)' (bytes=\(Array(line.utf8)))")
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
