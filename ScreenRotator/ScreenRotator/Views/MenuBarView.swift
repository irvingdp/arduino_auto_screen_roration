import SwiftUI

struct MenuBarView: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.openWindow) private var openWindow

    var body: some View {
        // Serial Port picker
        Menu("Port: \(portLabel)") {
            ForEach(appState.ports) { port in
                Button {
                    appState.selectedPort = port.device
                } label: {
                    HStack {
                        Text("\(port.device) (\(port.description))")
                        if appState.selectedPort == port.device {
                            Image(systemName: "checkmark")
                        }
                    }
                }
            }
            if appState.ports.isEmpty {
                Text("No ports found").foregroundColor(.secondary)
            }
            Divider()
            Button("Refresh Ports") {
                appState.refreshPorts()
            }
        }
        .disabled(appState.isMonitoring)

        // Display picker
        Menu("Display: \(displayLabel)") {
            ForEach(appState.displays) { display in
                Button {
                    appState.selectedDisplayID = display.id
                } label: {
                    HStack {
                        Text(display.desc)
                        if appState.selectedDisplayID == display.id {
                            Image(systemName: "checkmark")
                        }
                    }
                }
            }
            if appState.displays.isEmpty {
                Text("No displays found").foregroundColor(.secondary)
            }
            Divider()
            Button("Refresh Displays") {
                Task { await appState.refreshDisplays() }
            }
        }
        .disabled(appState.isMonitoring)

        Divider()

        // Status
        if appState.isMonitoring {
            Text("Angle: \(appState.receivedAngle)")
            Text(appState.connectionStatus)
        }

        // Start / Stop
        Button(appState.isMonitoring ? "Stop Monitoring" : "Start Monitoring") {
            if appState.isMonitoring {
                appState.stopMonitoring()
            } else {
                appState.startMonitoring()
            }
        }
        .disabled(!appState.isMonitoring && (appState.selectedPort.isEmpty || appState.selectedDisplayID.isEmpty))

        Divider()

        Button("Open Window") {
            NSApplication.shared.setActivationPolicy(.regular)
            openWindow(id: "main")
            NSApplication.shared.activate(ignoringOtherApps: true)
        }

        Button("Quit") {
            NSApplication.shared.terminate(nil)
        }
        .keyboardShortcut("q")
    }

    private var portLabel: String {
        if let port = appState.ports.first(where: { $0.device == appState.selectedPort }) {
            return port.description
        }
        return appState.selectedPort.isEmpty ? "None" : appState.selectedPort
    }

    private var displayLabel: String {
        if let display = appState.displays.first(where: { $0.id == appState.selectedDisplayID }) {
            return display.type
        }
        return appState.selectedDisplayID.isEmpty ? "None" : "..."
    }
}
