"""tkinter main window GUI."""

import tkinter as tk
from tkinter import ttk


class MainWindow:

    def __init__(self, root, app_state):
        self.root = root
        self.state = app_state

        root.title("Screen Auto-Rotation Controller")
        root.geometry("620x680")
        root.minsize(520, 500)

        self._build_ui()
        self.state.set_on_state_changed(self.update_from_state)

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        # --- Control Panel ---
        ctrl = ttk.LabelFrame(main, text="Control Panel", padding=10)
        ctrl.pack(fill=tk.X, pady=(0, 8))

        # Port row
        row1 = ttk.Frame(ctrl)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="Serial Port:", width=12, anchor="e").pack(side=tk.LEFT)
        self.port_combo = ttk.Combobox(row1, state="readonly", width=35)
        self.port_combo.pack(side=tk.LEFT, padx=(5, 5), fill=tk.X, expand=True)
        self.port_combo.bind("<<ComboboxSelected>>", self._on_port_selected)
        ttk.Button(row1, text="Refresh", width=8, command=self._refresh_ports).pack(side=tk.LEFT)

        # Display row
        row2 = ttk.Frame(ctrl)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="Display:", width=12, anchor="e").pack(side=tk.LEFT)
        self.display_combo = ttk.Combobox(row2, state="readonly", width=35)
        self.display_combo.pack(side=tk.LEFT, padx=(5, 5), fill=tk.X, expand=True)
        self.display_combo.bind("<<ComboboxSelected>>", self._on_display_selected)
        ttk.Button(row2, text="Refresh", width=8, command=self._refresh_displays).pack(side=tk.LEFT)

        # Start/Stop button
        btn_frame = ttk.Frame(ctrl)
        btn_frame.pack(pady=(8, 0))
        self.toggle_btn = ttk.Button(btn_frame, text="Start Monitoring", command=self._toggle_monitoring)
        self.toggle_btn.pack()

        # --- Status Panel ---
        status = ttk.LabelFrame(main, text="Status", padding=10)
        status.pack(fill=tk.X, pady=(0, 8))

        self.status_labels = {}
        for label_text, key in [("Connection:", "connection"), ("Received Angle:", "angle"), ("Last Action:", "action")]:
            row = ttk.Frame(status)
            row.pack(fill=tk.X, pady=1)
            ttk.Label(row, text=label_text, width=16, anchor="e", font=("", 10, "bold")).pack(side=tk.LEFT)
            lbl = ttk.Label(row, text="-", anchor="w")
            lbl.pack(side=tk.LEFT, padx=5)
            self.status_labels[key] = lbl

        # --- Debug Panel ---
        debug = ttk.LabelFrame(main, text="Debug Log", padding=10)
        debug.pack(fill=tk.BOTH, expand=True)

        # Debug controls
        dbg_ctrl = ttk.Frame(debug)
        dbg_ctrl.pack(fill=tk.X, pady=(0, 5))

        self.debug_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(dbg_ctrl, text="Debug Mode", variable=self.debug_var,
                         command=self._toggle_debug).pack(side=tk.LEFT)
        ttk.Button(dbg_ctrl, text="Copy", width=6, command=self._copy_log).pack(side=tk.RIGHT, padx=2)
        ttk.Button(dbg_ctrl, text="Clear", width=6, command=self._clear_log).pack(side=tk.RIGHT, padx=2)

        # Log text area
        log_frame = ttk.Frame(debug)
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_text = tk.Text(log_frame, height=10, font=("Consolas", 9), state=tk.DISABLED,
                                 bg="#1e1e1e", fg="#cccccc", wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._last_log_count = 0

    def _on_port_selected(self, event=None):
        idx = self.port_combo.current()
        if 0 <= idx < len(self.state.ports):
            self.state.selected_port = self.state.ports[idx]["device"]

    def _on_display_selected(self, event=None):
        idx = self.display_combo.current()
        if 0 <= idx < len(self.state.displays):
            self.state.selected_display = self.state.displays[idx]["name"]

    def _refresh_ports(self):
        self.state.refresh_ports()

    def _refresh_displays(self):
        self.state.refresh_displays()

    def _toggle_monitoring(self):
        if self.state.is_monitoring:
            self.state.stop_monitoring()
        else:
            self.state.start_monitoring()

    def _toggle_debug(self):
        self.state.debug_enabled = self.debug_var.get()

    def _copy_log(self):
        text = "\n".join(self.state.debug_log)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

    def _clear_log(self):
        self.state.clear_debug_log()

    def update_from_state(self):
        """Refresh all UI from current state."""
        s = self.state

        # Port combobox
        port_values = [f"{p['device']} ({p['description']})" for p in s.ports]
        self.port_combo["values"] = port_values
        port_idx = next((i for i, p in enumerate(s.ports) if p["device"] == s.selected_port), -1)
        if port_idx >= 0:
            self.port_combo.current(port_idx)

        # Display combobox
        display_values = [d["desc"] for d in s.displays]
        self.display_combo["values"] = display_values
        disp_idx = next((i for i, d in enumerate(s.displays) if d["name"] == s.selected_display), -1)
        if disp_idx >= 0:
            self.display_combo.current(disp_idx)

        # Enable/disable during monitoring
        combo_state = "disabled" if s.is_monitoring else "readonly"
        self.port_combo["state"] = combo_state
        self.display_combo["state"] = combo_state

        # Toggle button
        if s.is_monitoring:
            self.toggle_btn.configure(text="Stop Monitoring")
        else:
            self.toggle_btn.configure(text="Start Monitoring")

        # Status
        self.status_labels["connection"].configure(text=s.connection_status)
        self.status_labels["angle"].configure(text=s.received_angle)
        self.status_labels["action"].configure(text=s.last_action)

        # Debug log
        if s.debug_enabled and len(s.debug_log) != self._last_log_count:
            self.log_text.configure(state=tk.NORMAL)
            self.log_text.delete("1.0", tk.END)
            self.log_text.insert(tk.END, "\n".join(s.debug_log))
            self.log_text.see(tk.END)
            self.log_text.configure(state=tk.DISABLED)
            self._last_log_count = len(s.debug_log)
