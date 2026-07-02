
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/dist/CalendarPilot.app"
APP_ROOT="$DIST/Contents/Resources/app"
APP_BIN="$APP_ROOT/bin"
EVENTKIT_BRIDGE_APP="$APP_BIN/CalendarPilotEventKitBridge.app"
BUILD_ID="${CALENDAR_PILOT_BUILD_ID:-$(git -C "$ROOT/.." rev-parse --short=12 HEAD 2>/dev/null || echo unknown)}"
rm -rf "$DIST"
mkdir -p "$DIST/Contents/MacOS" "$APP_ROOT" "$APP_BIN"
cat > "$DIST/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>CFBundleName</key><string>CalendarPilot</string><key>CFBundleIdentifier</key><string>dev.calendarpilot.dogfood</string><key>CFBundleExecutable</key><string>CalendarPilot</string><key>CFBundlePackageType</key><string>APPL</string><key>NSCalendarsUsageDescription</key><string>CalendarPilot needs Calendar access only when live Apple Calendar provider mode is enabled, so it can read, write, and undo user-approved calendar changes.</string><key>NSCalendarsFullAccessUsageDescription</key><string>CalendarPilot needs full Calendar access only in live Apple Calendar provider mode to verify conflicts, create approved events, and roll them back.</string></dict></plist>
PLIST
cp -R "$ROOT/src" "$APP_ROOT/src"
cp -R "$ROOT/data" "$APP_ROOT/data"
cp -R "$ROOT/frontend" "$APP_ROOT/frontend"
cp "$ROOT/pyproject.toml" "$APP_ROOT/pyproject.toml"
printf '%s\n' "$BUILD_ID" > "$APP_ROOT/build_id"
SWIFT_BIN_DIR="$(swift build --package-path "$ROOT/packages/CalendarPilotKernel" -c release --product CalendarPilotKernelServer --show-bin-path)"
swift build --package-path "$ROOT/packages/CalendarPilotKernel" -c release --product CalendarPilotKernelServer
swift build --package-path "$ROOT/packages/CalendarPilotKernel" -c release --product CalendarPilotEventKitBridge
swift build --package-path "$ROOT/packages/CalendarPilotKernel" -c release --product CalendarPilotMacApp
cp "$SWIFT_BIN_DIR/CalendarPilotMacApp" "$DIST/Contents/MacOS/CalendarPilot"
cp "$SWIFT_BIN_DIR/CalendarPilotKernelServer" "$APP_BIN/CalendarPilotKernelServer"
cp "$SWIFT_BIN_DIR/CalendarPilotEventKitBridge" "$APP_BIN/CalendarPilotEventKitBridge"
mkdir -p "$EVENTKIT_BRIDGE_APP/Contents/MacOS"
cp "$SWIFT_BIN_DIR/CalendarPilotEventKitBridge" "$EVENTKIT_BRIDGE_APP/Contents/MacOS/CalendarPilotEventKitBridge"
cp "$ROOT/packages/CalendarPilotKernel/Sources/CalendarPilotEventKitBridge/Info.plist" "$EVENTKIT_BRIDGE_APP/Contents/Info.plist"
chmod +x "$APP_BIN/CalendarPilotKernelServer"
chmod +x "$APP_BIN/CalendarPilotEventKitBridge"
chmod +x "$EVENTKIT_BRIDGE_APP/Contents/MacOS/CalendarPilotEventKitBridge"
chmod +x "$DIST/Contents/MacOS/CalendarPilot"
echo "Created $DIST"
