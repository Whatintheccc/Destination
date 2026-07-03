

#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/dist/CalendarPilot.app"
SHORTCUT="$HOME/Desktop/CalendarPilot.app"
if [ ! -d "$APP" ]; then
  "$ROOT/scripts/build_macos_app.sh"
fi
if [ -L "$SHORTCUT" ] || [ -f "$SHORTCUT" ]; then
  rm -f "$SHORTCUT"
elif [ -d "$SHORTCUT" ]; then
  BACKUP="$HOME/Desktop/CalendarPilot.app.backup.$(date +%Y%m%d%H%M%S)"
  mv "$SHORTCUT" "$BACKUP"
  echo "Moved existing Desktop app to $BACKUP"
fi
ln -s "$APP" "$SHORTCUT"
echo "Created $SHORTCUT -> $APP"