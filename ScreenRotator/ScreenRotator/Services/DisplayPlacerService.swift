import Foundation
import os.log

private let logger = Logger(subsystem: "com.ivan.ScreenRotator", category: "DisplayPlacer")

enum DisplayPlacerError: LocalizedError {
    case notFound
    case executionFailed(String)
    case timeout

    var errorDescription: String? {
        switch self {
        case .notFound:
            return "displayplacer not found. Please install it with: brew install displayplacer"
        case .executionFailed(let msg):
            return "displayplacer failed: \(msg)"
        case .timeout:
            return "displayplacer command timed out"
        }
    }
}

class DisplayPlacerService {

    private func findDisplayPlacer() -> String? {
        let candidates = [
            "/opt/homebrew/bin/displayplacer",
            "/usr/local/bin/displayplacer"
        ]
        for path in candidates {
            let exists = FileManager.default.isExecutableFile(atPath: path)
            logger.info("findDisplayPlacer: \(path) exists=\(exists)")
            if exists {
                return path
            }
        }
        logger.error("findDisplayPlacer: NOT FOUND in any candidate path")
        return nil
    }

    func rawListOutput() async throws -> String {
        guard let binary = findDisplayPlacer() else {
            throw DisplayPlacerError.notFound
        }
        return try await runProcess(binary, arguments: ["list"])
    }

    func listDisplays(originCache: [String: String]) async throws -> ([DisplayInfo], String, [String: String]) {
        logger.info("listDisplays: fetching...")
        let output = try await rawListOutput()
        logger.info("listDisplays: raw output length=\(output.count)")
        var cache = originCache
        let displays = DisplayPlacerParser.parseDisplays(from: output, originCache: &cache)
        logger.info("listDisplays: parsed \(displays.count) display(s)")
        for d in displays {
            logger.info("  display: id=\(d.id) type=\(d.type) res=\(d.res) degree=\(d.degree) origin=\(d.origin)")
        }
        return (displays, output, cache)
    }

    func rotateDisplay(allDisplays: [DisplayInfo], targetID: String, degree: String) async throws {
        guard let binary = findDisplayPlacer() else {
            throw DisplayPlacerError.notFound
        }

        var args: [String] = []
        for display in allDisplays {
            var param = "id:\(display.id)"
            let rotationDegree = (display.id == targetID) ? degree : display.degree
            param += " degree:\(rotationDegree)"
            param += " res:\(display.res)"
            param += " hz:\(display.hz)"
            param += " color_depth:\(display.colorDepth)"
            param += " enabled:\(display.enabled.lowercased())"
            param += " scaling:\(display.scaling)"
            param += " origin:\(display.origin)"
            args.append(param)
        }

        logger.info("rotateDisplay: target=\(targetID) degree=\(degree)")
        logger.info("rotateDisplay: args=\(args)")
        _ = try await runProcess(binary, arguments: args)
        logger.info("rotateDisplay: success")
    }

    private func runProcess(_ path: String, arguments: [String]) async throws -> String {
        try await withCheckedThrowingContinuation { continuation in
            let process = Process()
            process.executableURL = URL(fileURLWithPath: path)
            process.arguments = arguments

            let stdout = Pipe()
            let stderr = Pipe()
            process.standardOutput = stdout
            process.standardError = stderr

            do {
                try process.run()
            } catch {
                continuation.resume(throwing: DisplayPlacerError.executionFailed(error.localizedDescription))
                return
            }

            // Timeout after 5 seconds
            let workItem = DispatchWorkItem {
                if process.isRunning {
                    process.terminate()
                }
            }
            DispatchQueue.global().asyncAfter(deadline: .now() + 5, execute: workItem)

            process.waitUntilExit()
            workItem.cancel()

            let outData = stdout.fileHandleForReading.readDataToEndOfFile()
            let errData = stderr.fileHandleForReading.readDataToEndOfFile()
            let outStr = String(data: outData, encoding: .utf8) ?? ""
            let errStr = String(data: errData, encoding: .utf8) ?? ""

            if process.terminationStatus == 0 {
                continuation.resume(returning: outStr)
            } else {
                continuation.resume(throwing: DisplayPlacerError.executionFailed(errStr.isEmpty ? "Exit code \(process.terminationStatus)" : errStr))
            }
        }
    }
}
