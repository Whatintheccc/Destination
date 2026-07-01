#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/dist/CalendarPilot.app"
mkdir -p "$DIST/Contents/MacOS" "$DIST/Contents/Resources/frontend/static"
cat > "$DIST/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>CFBundleName</key><string>CalendarPilot</string><key>CFBundleIdentifier</key><string>dev.calendarpilot.fixture</string><key>CFBundleExecutable</key><string>CalendarPilot</string><key>CFBundlePackageType</key><string>APPL</string></dict></plist>
PLIST
cp -R "$ROOT/frontend/static/"* "$DIST/Contents/Resources/frontend/static/"
cat > "$DIST/Contents/MacOS/CalendarPilot" <<'APP'
#!/usr/bin/env bash
DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$DIR" 2>/dev/null || true
if command -v python3 >/dev/null 2>&1; then
  PYTHONPATH=src python3 -m calendar_pilot.app frontend --serve --host 127.0.0.1 --port 8787 --run-dir runs/macos-app
else
  echo "python3 not found; open frontend/static/index.html from the repo checkout."
fi
APP
chmod +x "$DIST/Contents/MacOS/CalendarPilot"
echo "Created $DIST"
