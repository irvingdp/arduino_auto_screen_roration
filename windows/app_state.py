"""Central application state and orchestration."""

import json
import os
import threading
import logging
from datetime import datetime
from serial_service import SerialService
from display_service import DisplayService

logger = logging.getLogger(__name__)

CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "ScreenRotator")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


class AppState:

    def __init__(self, root=None):
        self.root = root  # tkinter root for thread marshaling

        self.ports = []
        self.displays = []
        self.selected_port = ""
        self.selected_display = ""
        self.is_monitoring = False
        self.connection_status = "Disconnected"
        self.connection_color = "gray"
        self.received_angle = "-"
        self.last_action = "-"
        self.debug_enabled = True
        self.debug_log = []
        self.last_processed_degree = None

        self._serial_service = None
        self._serial_thread = None
        self._on_state_changed = None

        self._load_config()

    def set_on_state_changed(self, callback):
        self._on_state_changed = callback

    def _notify(self):
        if self._on_state_changed and self.root:
            self.root.after(0, self._on_state_changed)

    def _load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r") as f:
                    cfg = json.load(f)
                    self._saved_port = cfg.get("selected_port", "")
                    self._saved_display = cfg.get("selected_display", "")
                    return
        except Exception:
            pass
        self._saved_port = ""
        self._saved_display = ""

    def _save_config(self):
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(CONFIG_FILE, "w") as f:
                json.dump({
                    "selected_port": self.selected_port,
                    "selected_display": self.selected_display,
                }, f)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def refresh_ports(self):
        self.add_debug_log("[App] refreshPorts called")
        self.ports = SerialService.list_ports()
        descs = ", ".join(f"{p['device']} ({p['description']})" for p in self.ports)
        self.add_debug_log(f"[App] Found {len(self.ports)} port(s): {descs}")
        self._auto_select_port()
        self._notify()

    def refresh_displays(self):
        self.add_debug_log("[App] refreshDisplays called")
        self.displays = DisplayService.list_displays()
        descs = "; ".join(d["desc"] for d in self.displays)
        self.add_debug_log(f"[App] Found {len(self.displays)} display(s): {descs}")
        self._auto_select_display()
        self._notify()

    def _auto_select_port(self):
        port_devices = [p["device"] for p in self.ports]
        if self.selected_port and self.selected_port in port_devices:
            return

        # Restore saved
        if self._saved_port and self._saved_port in port_devices:
            self.selected_port = self._saved_port
            self.add_debug_log(f"[App] Restored last port: {self._saved_port}")
            return

        # Auto-select Arduino
        for p in self.ports:
            if "arduino" in p["description"].lower():
                self.selected_port = p["device"]
                self.add_debug_log(f"[App] Auto-selected Arduino port: {p['device']}")
                return

        # Auto-select if only one
        if len(self.ports) == 1:
            self.selected_port = self.ports[0]["device"]
            self.add_debug_log(f"[App] Auto-selected only port: {self.ports[0]['device']}")

    def _auto_select_display(self):
        display_names = [d["name"] for d in self.displays]
        if self.selected_display and self.selected_display in display_names:
            return

        if self._saved_display and self._saved_display in display_names:
            self.selected_display = self._saved_display
            self.add_debug_log(f"[App] Restored last display: {self._saved_display}")
            return

        if len(self.displays) == 1:
            self.selected_display = self.displays[0]["name"]
            self.add_debug_log(f"[App] Auto-selected only display: {self.displays[0]['desc']}")

    def start_monitoring(self):
        if not self.selected_port:
            self.add_debug_log("Error: Please select a serial port")
            return
        if not self.selected_display:
            self.add_debug_log("Error: Please select a display")
            return

        self.is_monitoring = True
        self.last_processed_degree = None
        self.connection_status = f"Connecting to {self.selected_port}..."
        self.connection_color = "orange"
        self.add_debug_log(f"Started monitoring serial port: {self.selected_port}")
        self._save_config()
        self._notify()

        port = self.selected_port
        display = self.selected_display

        self._serial_service = SerialService()
        self._serial_thread = threading.Thread(
            target=self._serial_service.start_monitoring,
            args=(port, self._make_cb(self._on_line, display),
                  self._make_status_cb(), self._make_log_cb()),
            daemon=True,
        )
        self._serial_thread.start()

    def stop_monitoring(self):
        self.is_monitoring = False
        if self._serial_service:
            self._serial_service.stop_monitoring()
            self._serial_service = None
        self.connection_status = "Disconnected"
        self.connection_color = "gray"
        self.add_debug_log("Stopped monitoring")
        self._notify()

    def _make_cb(self, handler, display):
        def cb(line):
            if self.root:
                self.root.after(0, lambda: handler(line, display))
        return cb

    def _make_status_cb(self):
        def cb(status, color):
            if self.root:
                self.root.after(0, lambda: self._on_status(status, color))
        return cb

    def _make_log_cb(self):
        def cb(msg):
            if self.root:
                self.root.after(0, lambda: self.add_debug_log(msg))
        return cb

    def _on_status(self, status, color):
        self.connection_status = status
        self.connection_color = color
        self.add_debug_log(f"Connection status: {status}")
        self._notify()

    def _on_line(self, line, display_name):
        self.received_angle = line
        self.add_debug_log(f"[Handle] Received: '{line}'")

        if line in ("0", "90", "180", "270"):
            if line != self.last_processed_degree:
                self.add_debug_log(f"[Handle] Angle changed to {line}°, rotating {display_name}")
                success = DisplayService.rotate_display(display_name, line)
                if success:
                    self.last_processed_degree = line
                    self.last_action = f"Success: Display set to {line}°"
                    self.add_debug_log(f"[Handle] Rotation SUCCESS: {line}°")
                else:
                    self.last_action = f"Error: Failed to rotate to {line}°"
                    self.add_debug_log(f"[Handle] Rotation FAILED: {line}°")
            else:
                self.last_action = f"Angle unchanged: {line}°"
        elif line:
            self.add_debug_log(f"[Handle] Unexpected data: '{line}'")

        self._notify()

    def add_debug_log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self.debug_log.append(entry)
        # Keep max 1000 entries
        if len(self.debug_log) > 1000:
            self.debug_log = self.debug_log[-500:]
        self._notify()

    def clear_debug_log(self):
        self.debug_log.clear()
        self.add_debug_log("Log cleared")
