"""Screen Auto-Rotation Controller — Windows version."""

import os
import sys
import tkinter as tk
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")


def resource_path(filename):
    """Get path to bundled resource (works with PyInstaller)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, filename)


def main():
    from app_state import AppState
    from main_window import MainWindow
    from tray_icon import TrayIcon

    root = tk.Tk()

    # App icon
    icon_path = resource_path("icon.ico")
    if os.path.exists(icon_path):
        root.iconbitmap(icon_path)

    state = AppState(root=root)
    window = MainWindow(root, state)

    # System tray
    tray_path = icon_path if os.path.exists(icon_path) else None
    tray = TrayIcon(root, state, icon_path=tray_path)
    tray.start()

    # Hide to tray on window close
    def on_close():
        root.withdraw()

    root.protocol("WM_DELETE_WINDOW", on_close)

    # Initial data load
    state.refresh_ports()
    state.refresh_displays()

    root.mainloop()


if __name__ == "__main__":
    main()
