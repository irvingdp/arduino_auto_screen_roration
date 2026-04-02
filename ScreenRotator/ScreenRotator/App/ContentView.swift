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
            appState.refreshPorts()
            Task { await appState.refreshDisplays() }
        }
        .sheet(isPresented: $appState.showingDebugDisplays) {
            DebugDisplaysSheet()
        }
    }
}
