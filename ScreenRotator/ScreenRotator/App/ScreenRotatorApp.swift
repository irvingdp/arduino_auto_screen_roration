import SwiftUI

@main
struct ScreenRotatorApp: App {
    @StateObject private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appState)
        }
        .defaultSize(width: 600, height: 700)
    }
}
