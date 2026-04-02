import Foundation
import IOKit
import IOKit.serial
import SwiftUI

class SerialPortService {
    private var fileDescriptor: Int32 = -1
    private var isRunning = false
    private var monitorTask: Task<Void, Never>?

    static func listPorts() -> [SerialPortInfo] {
        var ports: [SerialPortInfo] = []

        guard let matchingDict = IOServiceMatching(kIOSerialBSDServiceValue) as? [String: Any] else {
            return ports
        }

        var iterator: io_iterator_t = 0
        let result = IOServiceGetMatchingServices(kIOMainPortDefault, matchingDict as CFDictionary, &iterator)
        guard result == KERN_SUCCESS else { return ports }

        var service: io_object_t = IOIteratorNext(iterator)
        while service != 0 {
            defer {
                IOObjectRelease(service)
                service = IOIteratorNext(iterator)
            }

            guard let devicePath = IORegistryEntryCreateCFProperty(
                service, kIOCalloutDeviceKey as CFString, kCFAllocatorDefault, 0
            )?.takeRetainedValue() as? String else {
                continue
            }

            // Filter to USB serial devices
            if devicePath.contains("usbmodem") || devicePath.contains("usbserial") || devicePath.contains("wchusbserial") {
                let description = IORegistryEntryCreateCFProperty(
                    service, "USB Product Name" as CFString, kCFAllocatorDefault, 0
                )?.takeRetainedValue() as? String ?? "Serial Device"

                ports.append(SerialPortInfo(device: devicePath, description: description))
            }
        }
        IOObjectRelease(iterator)

        return ports
    }

    func startMonitoring(
        port: String,
        onLine: @escaping (String) -> Void,
        onStatusChange: @escaping (String, Color) -> Void
    ) {
        isRunning = true

        monitorTask = Task.detached { [weak self] in
            guard let self = self else { return }

            while self.isRunning {
                onStatusChange("Connecting to \(port)...", .orange)

                let fd = open(port, O_RDWR | O_NOCTTY | O_NONBLOCK)
                guard fd >= 0 else {
                    onStatusChange("Unable to connect: \(port)", .red)
                    if self.isRunning {
                        try? await Task.sleep(for: .seconds(3))
                    }
                    continue
                }

                // Clear non-blocking flag after open
                let flags = fcntl(fd, F_GETFL)
                _ = fcntl(fd, F_SETFL, flags & ~O_NONBLOCK)

                // Configure termios: 9600 baud, 8N1, raw mode
                var options = termios()
                tcgetattr(fd, &options)
                cfsetispeed(&options, speed_t(B9600))
                cfsetospeed(&options, speed_t(B9600))

                // Raw mode
                cfmakeraw(&options)

                // 8N1
                options.c_cflag |= UInt(CS8)
                options.c_cflag |= UInt(CLOCAL | CREAD)

                // Read timeout: VMIN=0, VTIME=2 (200ms)
                options.c_cc.16 = 0  // VMIN
                options.c_cc.17 = 2  // VTIME

                tcsetattr(fd, TCSANOW, &options)
                tcflush(fd, TCIOFLUSH)

                self.fileDescriptor = fd
                onStatusChange("Connected to \(port)", .green)

                var lineBuffer = ""
                var readBuffer = [UInt8](repeating: 0, count: 256)

                while self.isRunning {
                    let bytesRead = read(fd, &readBuffer, readBuffer.count)

                    if bytesRead > 0 {
                        let chunk = String(bytes: readBuffer[0..<bytesRead], encoding: .utf8) ?? ""
                        lineBuffer += chunk

                        while let newlineIndex = lineBuffer.firstIndex(of: "\n") {
                            let line = String(lineBuffer[lineBuffer.startIndex..<newlineIndex])
                                .trimmingCharacters(in: .whitespacesAndNewlines)
                            lineBuffer = String(lineBuffer[lineBuffer.index(after: newlineIndex)...])

                            if !line.isEmpty {
                                onLine(line)
                            }
                        }
                    } else if bytesRead < 0 {
                        // Error reading - device likely disconnected
                        break
                    }
                    // bytesRead == 0 means timeout, just continue
                }

                close(fd)
                self.fileDescriptor = -1

                if self.isRunning {
                    onStatusChange("Disconnected from \(port)", .red)
                    try? await Task.sleep(for: .seconds(3))
                }
            }

            onStatusChange("Disconnected", .gray)
        }
    }

    func stopMonitoring() {
        isRunning = false
        if fileDescriptor >= 0 {
            close(fileDescriptor)
            fileDescriptor = -1
        }
        monitorTask?.cancel()
        monitorTask = nil
    }
}
