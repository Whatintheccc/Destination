#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/dist/CalendarPilot.app"
SHORTCUT="$HOME/Desktop/CalendarPilot.app"
if [ ! -d "$APP" ]; then
  "$ROOT/scripts/build_macos_app.sh"
fi
rm -f "$SHORTCUT"
ln -s "$APP" "$SHORTCUT"
echo "Created $SHORTCUT -> $APP"
