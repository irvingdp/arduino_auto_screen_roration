# Screen Auto-Rotation Controller

Arduino + MPU6050 reads physical orientation and sends angles (`0`, `90`, `180`, `270`) over serial at 9600 baud. A desktop app listens on the serial port and rotates the selected display automatically.

**Recommended:** use the native apps — **ScreenRotator** on **macOS** or the **Windows** build in `windows/` (PyInstaller `ScreenRotator.exe`). A legacy **Flask web UI** in the repo root is still available for reference.

## Function Demo

![Function Demo](demo.gif)

## Hardware Setup

![Hardware Setup](setup.jpg)

## Features

- **macOS:** native SwiftUI app (`ScreenRotator/`) using `displayplacer`
- **Windows:** native-style tray app (`windows/`) using Win32 `ChangeDisplaySettingsEx` (correct `DEVMODEW` layout for reliable rotation)
- **Legacy:** web interface (`web_screen_rotator.py`) — Flask + browser, macOS + `displayplacer` only
- Serial port enumeration and display selection
- Connection status, received angle, optional debug log

## System Requirements

| Platform | App | Requirements |
|----------|-----|----------------|
| **macOS** | ScreenRotator | Xcode / built app, [displayplacer](https://github.com/jakehilborn/displayplacer) (`brew install displayplacer`) |
| **Windows** | `windows/dist/ScreenRotator.exe` (or run from source) | Python 3.12+ if building from source; no `displayplacer` |
| **macOS** (legacy web) | Flask UI | Python 3.6+, Flask, `displayplacer` |

## Installation & build

### macOS — ScreenRotator (recommended)

```bash
brew install displayplacer
open ScreenRotator/ScreenRotator.xcodeproj
```

Or from the command line:

```bash
cd ScreenRotator
xcodebuild -scheme ScreenRotator -configuration Debug build CODE_SIGN_IDENTITY="-"
```

Optional DMG: see `ScreenRotator/scripts/create-dmg.sh` and project docs in `CLAUDE.md`.

### Windows — executable

Prebuilt: use `windows/dist/ScreenRotator.exe` from a release artifact, or build locally:

```powershell
cd windows
py -3.12 -m pip install -r requirements.txt pyinstaller
py -3.12 -m PyInstaller --clean build.spec
```

Output: `windows/dist/ScreenRotator.exe`. Use **Python 3.12** for builds (matches CI; Pillow wheels and PyInstaller hooks are reliable).

### Legacy web UI (macOS + displayplacer)

```bash
pip install -r requirements.txt
brew install displayplacer
python web_screen_rotator.py
```

Open `http://localhost:8098`.

## Usage (native apps)

1. Connect the Arduino (MPU6050 firmware, 9600 baud).
2. Start **ScreenRotator** (macOS) or **ScreenRotator.exe** (Windows).
3. Choose the serial port and the display to control.
4. Start monitoring; when the device sends `0` / `90` / `180` / `270`, the selected display rotates accordingly.

## Usage (legacy web)

1. Run `python web_screen_rotator.py` and open `http://localhost:8098`.
2. Select serial port and display, then **Start Monitoring**.

## Debugging Guide

### Enabling debug mode

- **Native apps:** use the in-app debug log panel if available.
- **Web:** toggle **Debug Mode** in the Debug Log panel.

### Serial port not found

- Check USB connection and drivers (Windows: Device Manager COM ports).
- Use **Refresh** to rescan ports.

### Display not found / cannot rotate

- **macOS:** ensure `displayplacer` is installed; run `displayplacer list`; check Accessibility permissions if needed.
- **Windows:** confirm the monitor supports rotation in **Settings → System → Display**; if manual rotation fails, the GPU/driver may block programmatic rotation.

### Connection / data issues

- Confirm the Arduino sends one of `0`, `90`, `180`, `270` (or `UNDEF` where supported) and baud rate is **9600**.

### Legacy: Flask / WebSocket

See terminal output for Flask errors; use the browser devtools console if live updates fail.

## Project structure

```
├── ScreenRotator/          # macOS SwiftUI app (Xcode)
├── windows/                # Windows Python + tkinter + pystray (PyInstaller spec)
├── arduino/                # Firmware (MPU6050)
├── web_screen_rotator.py   # Legacy Flask app
├── templates/, static/     # Legacy web UI
├── requirements.txt      # Legacy web dependencies
└── CLAUDE.md               # Maintainer notes (architecture, paths)
```

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Contributions

Issues and pull requests are welcome.
