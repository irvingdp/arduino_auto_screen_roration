import Foundation
import IOKit
import IOKit.serial
import SwiftUI
import os.log

private let logger = Logger(subsystem: "com.ivan.ScreenRotator", category: "Serial")

class SerialPortService {
    private var fileDescriptor: Int32 = -1
    private var isRunning = false
    private var monitorTask: Task<Void, Never>?

    static func listPorts() -> [SerialPortInfo] {
        var ports: [SerialPortInfo] = []

        logger.info("listPorts: creating IOKit matching dictionary")
        guard let matchingDict = IOServiceMatching(kIOSerialBSDServiceValue) as? [String: Any] else {
            logger.error("listPorts: failed to create matching dictionary")
            return ports
        }

        var iterator: io_iterator_t = 0
        let result = IOServiceGetMatchingServices(kIOMainPortDefault, matchingDict as CFDictionary, &iterator)
        logger.info("listPorts: IOServiceGetMatchingServices returned \(result) (0=success)")
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

            logger.info("listPorts: found device \(devicePath)")

            // Filter to USB serial devices
            if devicePath.contains("usbmodem") || devicePath.contains("usbserial") || devicePath.contains("wchusbserial") {
                let description = findUSBProductName(for: service) ?? "Serial Device"
                logger.info("listPorts: USB device matched: \(devicePath) (\(description))")
                ports.append(SerialPortInfo(device: devicePath, description: description))
            }
        }
        IOObjectRelease(iterator)

        logger.info("listPorts: returning \(ports.count) USB port(s)")
        return ports
    }

    private static func findUSBProductName(for service: io_object_t) -> String? {
        var parent: io_object_t = 0
        var current = service
        IOObjectRetain(current)

        while IORegistryEntryGetParentEntry(current, kIOServicePlane, &parent) == KERN_SUCCESS {
            IOObjectRelease(current)
            current = parent

            if let name = IORegistryEntryCreateCFProperty(
                current, "USB Product Name" as CFString, kCFAllocatorDefault, 0
            )?.takeRetainedValue() as? String {
                IOObjectRelease(current)
                return name
            }
        }
        IOObjectRelease(current)
        return nil
    }

    func startMonitoring(
        port: String,
        onLine: @escaping (String) -> Void,
        onStatusChange: @escaping (String, Color) -> Void,
        onLog: @escaping (String) -> Void
    ) {
        isRunning = true
        logger.info("startMonitoring: port=\(port)")
        onLog("[Serial] Starting monitoring on \(port)")

        monitorTask = Task.detached { [weak self] in
            guard let self = self else { return }

            while self.isRunning {
                onStatusChange("Connecting to \(port)...", .orange)
                onLog("[Serial] Opening \(port)...")

                let fd = open(port, O_RDWR | O_NOCTTY | O_NONBLOCK)
                if fd < 0 {
                    let err = String(cString: strerror(errno))
                    logger.error("open() failed: errno=\(errno) \(err)")
                    onStatusChange("Unable to connect: \(port)", .red)
                    onLog("[Serial] open() FAILED: errno=\(errno) (\(err))")
                    if self.isRunning {
                        try? await Task.sleep(for: .seconds(3))
                    }
                    continue
                }
                onLog("[Serial] open() OK, fd=\(fd)")

                // Clear non-blocking flag after open
                let flags = fcntl(fd, F_GETFL)
                _ = fcntl(fd, F_SETFL, flags & ~O_NONBLOCK)
                onLog("[Serial] Cleared O_NONBLOCK")

                // Configure termios to match pyserial behavior
                var options = termios()
                tcgetattr(fd, &options)

                cfsetispeed(&options, speed_t(B9600))
                cfsetospeed(&options, speed_t(B9600))

                options.c_iflag &= ~UInt(ISTRIP | INLCR | IGNCR | ICRNL | IXON | IXOFF | IXANY | PARMRK)
                options.c_iflag |= UInt(IGNBRK)
                options.c_oflag &= ~UInt(OPOST)
                options.c_cflag &= ~UInt(CSIZE | CSTOPB | PARENB | PARODD)
                options.c_cflag |= UInt(CS8 | CLOCAL | CREAD | HUPCL)
                options.c_lflag &= ~UInt(ICANON | ECHO | ECHOE | ECHOK | ECHONL | ISIG | IEXTEN)

                options.c_cc.16 = 1  // VMIN
                options.c_cc.17 = 0  // VTIME

                let tcResult = tcsetattr(fd, TCSANOW, &options)
                onLog("[Serial] tcsetattr returned \(tcResult) (0=success)")

                // Set DTR line — required for Arduino Leonardo (USB CDC)
                let dtrResult = ioctl(fd, TIOCSDTR)
                onLog("[Serial] ioctl TIOCSDTR returned \(dtrResult) (0=success)")

                tcflush(fd, TCIOFLUSH)

                onLog("[Serial] Waiting 2s for Arduino reset...")
                try? await Task.sleep(for: .seconds(2))
                tcflush(fd, TCIOFLUSH)

                self.fileDescriptor = fd
                onStatusChange("Connected to \(port)", .green)
                onLog("[Serial] Connected! Starting read loop...")

                var lineBuffer = ""
                var readBuffer = [UInt8](repeating: 0, count: 256)
                var totalBytesRead = 0
                var totalLines = 0

                while self.isRunning {
                    let bytesRead = read(fd, &readBuffer, readBuffer.count)

                    if bytesRead > 0 {
                        totalBytesRead += bytesRead
                        let rawBytes = Array(readBuffer[0..<bytesRead])

                        // Convert bytes to string
                        guard let chunk = String(bytes: readBuffer[0..<bytesRead], encoding: .utf8) else {
                            onLog("[Serial] WARNING: failed to decode \(bytesRead) bytes as UTF-8: \(rawBytes)")
                            continue
                        }

                        if totalLines < 10 {
                            onLog("[Serial] read(): \(bytesRead) bytes, raw=\(rawBytes), str=\(chunk.debugDescription)")
                        }

                        // Normalize \r\n → \n (Swift treats \r\n as a single Character/grapheme cluster,
                        // which makes firstIndex(of: "\n") fail to match)
                        lineBuffer += chunk.replacingOccurrences(of: "\r\n", with: "\n").replacingOccurrences(of: "\r", with: "\n")

                        if totalLines < 10 {
                            let hasNewline = lineBuffer.contains("\n")
                            let bufLen = lineBuffer.count
                            let bufBytes = Array(lineBuffer.utf8)
                            onLog("[Serial] buffer: len=\(bufLen), hasLF=\(hasNewline), bytes=\(bufBytes)")
                        }

                        while let newlineIndex = lineBuffer.firstIndex(of: "\n") {
                            let line = String(lineBuffer[lineBuffer.startIndex..<newlineIndex])
                                .trimmingCharacters(in: .whitespacesAndNewlines)
                            lineBuffer = String(lineBuffer[lineBuffer.index(after: newlineIndex)...])

                            totalLines += 1
                            onLog("[Serial] Line #\(totalLines): '\(line)' (empty=\(line.isEmpty))")
                            if !line.isEmpty {
                                logger.info("Serial line: \(line)")
                                onLine(line)
                            }
                        }
                    } else if bytesRead < 0 {
                        let err = String(cString: strerror(errno))
                        logger.error("read() failed: errno=\(errno) \(err)")
                        onLog("[Serial] read() FAILED: errno=\(errno) (\(err)) — device likely disconnected")
                        break
                    } else {
                        onLog("[Serial] read() returned 0 (timeout)")
                    }
                }

                onLog("[Serial] Read loop exited. totalBytes=\(totalBytesRead), totalLines=\(totalLines)")
                close(fd)
                self.fileDescriptor = -1

                if self.isRunning {
                    onStatusChange("Disconnected from \(port)", .red)
                    onLog("[Serial] Disconnected, will retry in 3s...")
                    try? await Task.sleep(for: .seconds(3))
                }
            }

            onStatusChange("Disconnected", .gray)
            onLog("[Serial] Monitoring stopped")
        }
    }

    func stopMonitoring() {
        logger.info("stopMonitoring called")
        isRunning = false
        if fileDescriptor >= 0 {
            close(fileDescriptor)
            fileDescriptor = -1
        }
        monitorTask?.cancel()
        monitorTask = nil
    }
}
