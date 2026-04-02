# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

An Arduino-powered screen rotation controller for macOS. An MPU6050 accelerometer on an Arduino Leonardo detects physical device orientation and sends rotation angles over serial, which a native macOS app reads to automatically rotate Mac displays via `displayplacer`.

## Native macOS App (ScreenRotator)

The primary UI is a SwiftUI macOS app in `ScreenRotator/`.

### Build & Run

```bash
# Prerequisites
brew install displayplacer

# Build and run via Xcode
open ScreenRotator/ScreenRotator.xcodeproj

# Or build from command line
cd ScreenRotator
xcodebuild -scheme ScreenRotator -configuration Debug build CODE_SIGN_IDENTITY="-"

# Create distributable DMG
bash ScreenRotator/scripts/create-dmg.sh
```

### Regenerating the Xcode project

The `.xcodeproj` is generated from `ScreenRotator/project.yml` via xcodegen:

```bash
cd ScreenRotator
brew install xcodegen  # if needed
xcodegen generate
```

### App Architecture

**Arduino** (`arduino/mpu6050_angle_detion.h`) → serial at 9600 baud → **SwiftUI app** → `displayplacer` CLI → macOS display

Key source files in `ScreenRotator/ScreenRotator/`:

- `Models/AppState.swift` — `@MainActor ObservableObject` holding all app state, orchestrates serial monitoring and display rotation
- `Services/SerialPortService.swift` — IOKit port enumeration + POSIX termios serial reading in a background Task
- `Services/DisplayPlacerService.swift` — Runs `displayplacer` via Foundation `Process`, searches both `/opt/homebrew/bin/` and `/usr/local/bin/`
- `Services/DisplayPlacerParser.swift` — Parses `displayplacer list` output, caches first-seen display origins
- `Views/` — SwiftUI views: ControlPanel (port/display pickers), StatusPanel (connection/angle/action), DebugPanel (toggleable log), DebugDisplaysSheet

The app is not sandboxed (needs `/dev/cu.*` access and subprocess execution). Entitlements in `Resources/ScreenRotator.entitlements`.

## Arduino Firmware

`arduino/mpu6050_angle_detion.h`:
- Reads MPU6050 accelerometer over I2C
- Outputs `"0"`, `"90"`, `"180"`, or `"270"` every 300ms; `"UNDEF"` if ambiguous
- Ignores signals below 0.3g magnitude to filter noise
- Angle boundaries may need adjustment based on sensor mounting orientation (see calibration comments)

## Legacy Web UI

The original Flask + HTML/JS web UI is still in the repo root (`web_screen_rotator.py`, `templates/`, `static/`). It is superseded by the native app but kept for reference.

## Platform Constraint

macOS only — `displayplacer` is a Mac-specific CLI tool, and serial port handling uses IOKit/POSIX APIs.
