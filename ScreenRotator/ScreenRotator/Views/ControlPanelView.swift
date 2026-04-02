import SwiftUI

struct ControlPanelView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        GroupBox("Control Panel") {
            VStack(alignment: .leading, spacing: 12) {
                // Serial Port Picker
                HStack {
                    Text("Serial Port:")
                        .frame(width: 100, alignment: .trailing)
                    Picker("", selection: $appState.selectedPort) {
                        Text("-- Select a serial port --").tag("")
                        ForEach(appState.ports) { port in
                            Text("\(port.device) (\(port.description))").tag(port.device)
                        }
                    }
                    .labelsHidden()
                    .disabled(appState.isMonitoring)

                    Button {
                        appState.refreshPorts()
                    } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                    .disabled(appState.isMonitoring)
                }

                // Display Picker
                HStack {
                    Text("Display:")
                        .frame(width: 100, alignment: .trailing)
                    Picker("", selection: $appState.selectedDisplayID) {
                        Text("-- Select a display --").tag("")
                        ForEach(appState.displays) { display in
                            Text(display.desc).tag(display.id)
                        }
                    }
                    .labelsHidden()
                    .disabled(appState.isMonitoring)

                    Button {
                        Task { await appState.refreshDisplays() }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                    .disabled(appState.isMonitoring)

                    Button {
                        Task { await appState.fetchDebugDisplays() }
                    } label: {
                        Image(systemName: "ant")
                    }
                    .help("Debug Displays")
                }

                // Start/Stop Button
                HStack {
                    Spacer()
                    Button {
                        if appState.isMonitoring {
                            appState.stopMonitoring()
                        } else {
                            appState.startMonitoring()
                        }
                    } label: {
                        HStack {
                            Image(systemName: appState.isMonitoring ? "stop.fill" : "play.fill")
                            Text(appState.isMonitoring ? "Stop Monitoring" : "Start Monitoring")
                        }
                        .frame(minWidth: 160)
                    }
                    .controlSize(.large)
                    .buttonStyle(.borderedProminent)
                    .tint(appState.isMonitoring ? .red : .accentColor)
                    .disabled(!appState.isMonitoring && (appState.selectedPort.isEmpty || appState.selectedDisplayID.isEmpty))
                    Spacer()
                }
            }
            .padding(.vertical, 4)
        }
    }
}
