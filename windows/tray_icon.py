"""System tray icon using pystray."""

import threading
import pystray
from PIL import Image


class TrayIcon:

    def __init__(self, root, app_state, icon_path=None):
        self.root = root
        self.state = app_state
        self._icon = None
        self._thread = None

        if icon_path:
            self._image = Image.open(icon_path)
        else:
            # Fallback: simple white square icon
            self._image = Image.new("RGB", (64, 64), "white")

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        if self._icon:
            self._icon.stop()

    def _run(self):
        self._icon = pystray.Icon(
            "ScreenRotator",
            self._image,
            "Screen Rotator",
            menu=pystray.Menu(self._menu_factory),
        )
        self._icon.run()

    def _menu_factory(self):
        items = []

        # Port submenu
        port_items = []
        for p in self.state.ports:
            checked = p["device"] == self.state.selected_port
            port_items.append(pystray.MenuItem(
                f"{p['device']} ({p['description']})",
                self._make_port_cb(p["device"]),
                checked=lambda item, dev=p["device"]: dev == self.state.selected_port,
                enabled=not self.state.is_monitoring,
            ))
        if not port_items:
            port_items.append(pystray.MenuItem("No ports found", None, enabled=False))
        port_items.append(pystray.Menu.SEPARATOR)
        port_items.append(pystray.MenuItem("Refresh Ports", self._refresh_ports))

        port_label = self._get_port_label()
        items.append(pystray.MenuItem(f"Port: {port_label}", pystray.Menu(*port_items)))

        # Display submenu
        disp_items = []
        for d in self.state.displays:
            checked = d["name"] == self.state.selected_display
            disp_items.append(pystray.MenuItem(
                d["desc"],
                self._make_display_cb(d["name"]),
                checked=lambda item, name=d["name"]: name == self.state.selected_display,
                enabled=not self.state.is_monitoring,
            ))
        if not disp_items:
            disp_items.append(pystray.MenuItem("No displays found", None, enabled=False))
        disp_items.append(pystray.Menu.SEPARATOR)
        disp_items.append(pystray.MenuItem("Refresh Displays", self._refresh_displays))

        disp_label = self._get_display_label()
        items.append(pystray.MenuItem(f"Display: {disp_label}", pystray.Menu(*disp_items)))

        items.append(pystray.Menu.SEPARATOR)

        # Status (shown when monitoring)
        if self.state.is_monitoring:
            items.append(pystray.MenuItem(f"Angle: {self.state.received_angle}", None, enabled=False))
            items.append(pystray.MenuItem(self.state.connection_status, None, enabled=False))
            items.append(pystray.Menu.SEPARATOR)

        # Start/Stop
        label = "Stop Monitoring" if self.state.is_monitoring else "Start Monitoring"
        can_start = self.state.is_monitoring or (self.state.selected_port and self.state.selected_display)
        items.append(pystray.MenuItem(label, self._toggle_monitoring, enabled=can_start))

        items.append(pystray.Menu.SEPARATOR)
        items.append(pystray.MenuItem("Open Window", self._show_window))
        items.append(pystray.MenuItem("Quit", self._quit))

        return items

    def _get_port_label(self):
        for p in self.state.ports:
            if p["device"] == self.state.selected_port:
                return p["description"]
        return "None"

    def _get_display_label(self):
        for d in self.state.displays:
            if d["name"] == self.state.selected_display:
                return d["name"].replace("\\\\.\\", "")
        return "None"

    def _make_port_cb(self, device):
        def cb(icon, item):
            self.root.after(0, lambda: self._set_port(device))
        return cb

    def _make_display_cb(self, name):
        def cb(icon, item):
            self.root.after(0, lambda: self._set_display(name))
        return cb

    def _set_port(self, device):
        self.state.selected_port = device
        self.state._notify()

    def _set_display(self, name):
        self.state.selected_display = name
        self.state._notify()

    def _refresh_ports(self, icon=None, item=None):
        self.root.after(0, self.state.refresh_ports)

    def _refresh_displays(self, icon=None, item=None):
        self.root.after(0, self.state.refresh_displays)

    def _toggle_monitoring(self, icon=None, item=None):
        if self.state.is_monitoring:
            self.root.after(0, self.state.stop_monitoring)
        else:
            self.root.after(0, self.state.start_monitoring)

    def _show_window(self, icon=None, item=None):
        self.root.after(0, self.root.deiconify)

    def _quit(self, icon=None, item=None):
        self.root.after(0, self._do_quit)

    def _do_quit(self):
        self.state.stop_monitoring()
        self.stop()
        self.root.destroy()
