import SwiftUI

struct ContentView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        ScrollView {
            VStack(spacing: 16) {
                ControlPanelView()
                StatusPanelView()
                DebugPanelView()
            }
            .padding()
        }
        .frame(minWidth: 500, minHeight: 500)
        .onAppear {
            NSApplication.shared.setActivationPolicy(.regular)
            appState.refreshPorts()
            Task { await appState.refreshDisplays() }
        }
        .onDisappear {
            // Hide dock icon when window is closed (menu bar only)
            NSApplication.shared.setActivationPolicy(.accessory)
        }
        .sheet(isPresented: $appState.showingDebugDisplays) {
            DebugDisplaysSheet()
        }
    }
}
