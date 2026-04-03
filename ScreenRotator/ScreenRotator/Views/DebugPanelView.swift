import SwiftUI
import AppKit

struct DebugPanelView: View {
    @EnvironmentObject var appState: AppState
    @State private var copied = false

    var body: some View {
        GroupBox {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text("Debug Log")
                        .font(.headline)
                    Spacer()
                    Toggle("Debug Mode", isOn: $appState.debugEnabled)
                        .toggleStyle(.switch)
                        .controlSize(.small)
                    Button {
                        let text = appState.debugLog
                            .map { "[\($0.formattedTime)] \($0.message)" }
                            .joined(separator: "\n")
                        NSPasteboard.general.clearContents()
                        NSPasteboard.general.setString(text, forType: .string)
                        copied = true
                        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) { copied = false }
                    } label: {
                        Image(systemName: copied ? "checkmark" : "doc.on.doc")
                        Text(copied ? "Copied!" : "Copy")
                    }
                    .controlSize(.small)
                    Button {
                        appState.clearDebugLog()
                    } label: {
                        Image(systemName: "trash")
                        Text("Clear")
                    }
                    .controlSize(.small)
                }

                if appState.debugEnabled {
                    ScrollViewReader { proxy in
                        ScrollView {
                            LazyVStack(alignment: .leading, spacing: 2) {
                                ForEach(appState.debugLog) { entry in
                                    Text("[\(entry.formattedTime)] \(entry.message)")
                                        .font(.system(.caption, design: .monospaced))
                                        .foregroundColor(.secondary)
                                        .textSelection(.enabled)
                                        .id(entry.id)
                                }
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(4)
                        }
                        .frame(minHeight: 150, maxHeight: 250)
                        .background(Color(nsColor: .textBackgroundColor))
                        .clipShape(RoundedRectangle(cornerRadius: 4))
                        .onChange(of: appState.debugLog.count) { _, _ in
                            if let last = appState.debugLog.last {
                                proxy.scrollTo(last.id, anchor: .bottom)
                            }
                        }
                    }
                }
            }
            .padding(.vertical, 4)
        }
    }
}
