#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/dist/CalendarPilot.app"
APP_ROOT="$DIST/Contents/Resources/app"
APP_BIN="$APP_ROOT/bin"
BUILD_ID="${CALENDAR_PILOT_BUILD_ID:-$(git -C "$ROOT/.." rev-parse --short=12 HEAD 2>/dev/null || echo unknown)}"
rm -rf "$DIST"
mkdir -p "$DIST/Contents/MacOS" "$APP_ROOT" "$APP_BIN"
cat > "$DIST/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>CFBundleName</key><string>CalendarPilot</string><key>CFBundleIdentifier</key><string>dev.calendarpilot.fixture</string><key>CFBundleExecutable</key><string>CalendarPilot</string><key>CFBundlePackageType</key><string>APPL</string></dict></plist>
PLIST
cp -R "$ROOT/src" "$APP_ROOT/src"
cp -R "$ROOT/data" "$APP_ROOT/data"
cp -R "$ROOT/frontend" "$APP_ROOT/frontend"
cp "$ROOT/pyproject.toml" "$APP_ROOT/pyproject.toml"
printf '%s\n' "$BUILD_ID" > "$APP_ROOT/build_id"
SWIFT_BIN_DIR="$(swift build --package-path "$ROOT/packages/CalendarPilotKernel" -c release --product CalendarPilotKernelServer --show-bin-path)"
swift build --package-path "$ROOT/packages/CalendarPilotKernel" -c release --product CalendarPilotKernelServer
cp "$SWIFT_BIN_DIR/CalendarPilotKernelServer" "$APP_BIN/CalendarPilotKernelServer"
chmod +x "$APP_BIN/CalendarPilotKernelServer"
cat > "$DIST/Contents/MacOS/CalendarPilot" <<'APP'
#!/usr/bin/env bash
APP_ROOT="$(cd "$(dirname "$0")/../Resources/app" && pwd)"
RUN_DIR="${CALENDAR_PILOT_RUN_DIR:-$HOME/Library/Application Support/CalendarPilot}"
HOST="${CALENDAR_PILOT_HOST:-127.0.0.1}"
PORT="${CALENDAR_PILOT_PORT:-8787}"
URL="http://$HOST:$PORT"
mkdir -p "$RUN_DIR"
cd "$APP_ROOT" 2>/dev/null || exit 1
if command -v python3 >/dev/null 2>&1; then
  if [ -x "$APP_ROOT/bin/CalendarPilotKernelServer" ]; then
    export CALENDAR_PILOT_SWIFT_KERNEL_SERVER="$APP_ROOT/bin/CalendarPilotKernelServer"
  fi
  if command -v open >/dev/null 2>&1 && [ "${CALENDAR_PILOT_OPEN_BROWSER:-1}" != "0" ]; then
    (sleep 1; open "$URL") >/dev/null 2>&1 &
  fi
  exec env PYTHONPATH="$APP_ROOT/src" python3 -m calendar_pilot.app frontend --serve --host "$HOST" --port "$PORT" --run-dir "$RUN_DIR"
else
  echo "python3 not found; install Python 3 or run from the repository checkout."
  exit 1
fi
APP
chmod +x "$DIST/Contents/MacOS/CalendarPilot"
echo "Created $DIST"
