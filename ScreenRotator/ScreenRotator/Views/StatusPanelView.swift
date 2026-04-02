import SwiftUI

struct StatusPanelView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        GroupBox("Status") {
            VStack(spacing: 8) {
                statusRow(label: "Connection:", value: appState.connectionStatus, color: appState.connectionColor)
                Divider()
                statusRow(label: "Received Angle:", value: appState.receivedAngle)
                Divider()
                statusRow(label: "Last Action:", value: appState.lastAction)
            }
            .padding(.vertical, 4)
        }
    }

    private func statusRow(label: String, value: String, color: Color? = nil) -> some View {
        HStack {
            Text(label)
                .fontWeight(.medium)
                .frame(width: 130, alignment: .trailing)
            if let color = color {
                Circle()
                    .fill(color)
                    .frame(width: 8, height: 8)
            }
            Text(value)
                .foregroundColor(color ?? .primary)
            Spacer()
        }
    }
}
