"""Serial port enumeration and monitoring using pyserial."""

import time
import logging
import serial
import serial.tools.list_ports

logger = logging.getLogger(__name__)


class SerialService:

    def __init__(self):
        self._running = False
        self._connection = None

    @staticmethod
    def list_ports():
        """List available USB serial ports."""
        ports = []
        for p in serial.tools.list_ports.comports():
            # Filter to USB serial devices
            if p.vid is not None or "USB" in (p.description or "").upper() or "Arduino" in (p.description or ""):
                ports.append({
                    "device": p.device,
                    "description": p.description or "Serial Device",
                })
                logger.info(f"Found port: {p.device} ({p.description})")
        logger.info(f"Total USB ports: {len(ports)}")
        return ports

    def start_monitoring(self, port, on_line, on_status_change, on_log):
        """Monitor serial port in a loop. Call from a daemon thread."""
        self._running = True
        on_log(f"[Serial] Starting monitoring on {port}")

        while self._running:
            on_status_change(f"Connecting to {port}...", "orange")
            on_log(f"[Serial] Opening {port}...")

            try:
                self._connection = serial.Serial(port, 9600, timeout=2)
                on_log(f"[Serial] Opened, DTR={self._connection.dtr}")

                # Wait for Arduino reset (Leonardo USB CDC)
                on_log("[Serial] Waiting 2s for Arduino reset...")
                time.sleep(2)
                self._connection.reset_input_buffer()

                on_status_change(f"Connected to {port}", "green")
                on_log("[Serial] Connected! Starting read loop...")

                total_lines = 0
                while self._running:
                    if self._connection.in_waiting > 0:
                        try:
                            raw = self._connection.readline()
                            line = raw.decode("utf-8", errors="replace").strip()
                            total_lines += 1

                            if total_lines <= 10:
                                on_log(f"[Serial] Line #{total_lines}: '{line}'")

                            if line:
                                on_line(line)
                        except serial.SerialException:
                            on_log("[Serial] Read error — device disconnected")
                            break
                        except Exception as e:
                            on_log(f"[Serial] Read error: {e}")
                            time.sleep(0.1)
                    else:
                        time.sleep(0.05)

            except serial.SerialException as e:
                on_status_change(f"Unable to connect: {port}", "red")
                on_log(f"[Serial] Connection failed: {e}")
            except Exception as e:
                on_log(f"[Serial] Unexpected error: {e}")
            finally:
                if self._connection and self._connection.is_open:
                    self._connection.close()
                self._connection = None

            if self._running:
                on_log("[Serial] Disconnected, retrying in 3s...")
                time.sleep(3)

        on_status_change("Disconnected", "gray")
        on_log("[Serial] Monitoring stopped")

    def stop_monitoring(self):
        """Stop the monitoring loop."""
        self._running = False
        if self._connection and self._connection.is_open:
            try:
                self._connection.close()
            except Exception:
                pass
        self._connection = None
