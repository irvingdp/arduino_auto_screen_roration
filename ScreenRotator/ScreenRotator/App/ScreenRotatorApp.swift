import SwiftUI

@main
struct ScreenRotatorApp: App {
    @StateObject private var appState = AppState()
    @Environment(\.openWindow) private var openWindow

    var body: some Scene {
        Window("Screen Auto-Rotation Controller", id: "main") {
            ContentView()
                .environmentObject(appState)
        }
        .defaultSize(width: 600, height: 700)

        MenuBarExtra {
            MenuBarView()
                .environmentObject(appState)
        } label: {
            Image(systemName: "rotate.right")
        }
    }
}
