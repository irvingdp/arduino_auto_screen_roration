#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/build"

echo "==> Cleaning build directory..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

echo "==> Building ScreenRotator (Release)..."
xcodebuild -project "$PROJECT_DIR/ScreenRotator.xcodeproj" \
  -scheme ScreenRotator \
  -configuration Release \
  -derivedDataPath "$BUILD_DIR/derived" \
  CONFIGURATION_BUILD_DIR="$BUILD_DIR/app" \
  CODE_SIGN_IDENTITY="-" \
  build

APP_PATH="$BUILD_DIR/app/ScreenRotator.app"

if [ ! -d "$APP_PATH" ]; then
  echo "Error: Build failed - ScreenRotator.app not found"
  exit 1
fi

echo "==> Creating DMG..."
if command -v create-dmg &> /dev/null; then
  create-dmg \
    --volname "Screen Rotator" \
    --window-pos 200 120 \
    --window-size 600 400 \
    --icon-size 100 \
    --icon "ScreenRotator.app" 175 190 \
    --app-drop-link 425 190 \
    "$BUILD_DIR/ScreenRotator.dmg" \
    "$BUILD_DIR/app/"
else
  # Fallback: create a simple DMG without create-dmg tool
  echo "  (create-dmg not found, using hdiutil directly)"
  STAGING="$BUILD_DIR/dmg-staging"
  mkdir -p "$STAGING"
  cp -R "$APP_PATH" "$STAGING/"
  ln -s /Applications "$STAGING/Applications"
  hdiutil create -volname "Screen Rotator" \
    -srcfolder "$STAGING" \
    -ov -format UDZO \
    "$BUILD_DIR/ScreenRotator.dmg"
  rm -rf "$STAGING"
fi

echo ""
echo "==> Done! DMG created at: $BUILD_DIR/ScreenRotator.dmg"
