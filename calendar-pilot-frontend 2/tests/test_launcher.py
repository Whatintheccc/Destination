from __future__ import annotations

import socket
import unittest
from pathlib import Path

from calendar_pilot.frontend.launcher import select_port


ROOT = Path(__file__).resolve().parents[1]


class LauncherTests(unittest.TestCase):
    def test_select_port_uses_preferred_when_free(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            free_port = int(sock.getsockname()[1])

        self.assertEqual(select_port("127.0.0.1", free_port), free_port)

    def test_select_port_falls_back_when_preferred_is_occupied(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            occupied_port = int(sock.getsockname()[1])
            selected = select_port("127.0.0.1", occupied_port)

        self.assertNotEqual(selected, occupied_port)

    def test_select_port_can_fail_strictly(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            occupied_port = int(sock.getsockname()[1])
            with self.assertRaises(RuntimeError):
                select_port("127.0.0.1", occupied_port, strict=True)

    def test_active_app_bundle_uses_native_macos_wrapper_source(self) -> None:
        wrapper = ROOT / "packages" / "CalendarPilotKernel" / "Sources" / "CalendarPilotMacApp" / "main.swift"
        package = ROOT / "packages" / "CalendarPilotKernel" / "Package.swift"
        build_script = ROOT / "scripts" / "build_macos_app.sh"

        self.assertIn("calendar_pilot.frontend.launcher", wrapper.read_text(encoding="utf-8"))
        self.assertIn("WKWebView", wrapper.read_text(encoding="utf-8"))
        self.assertIn("CalendarPilotMacApp", package.read_text(encoding="utf-8"))
        self.assertIn("--product CalendarPilotMacApp", build_script.read_text(encoding="utf-8"))
        self.assertIn("dev.calendarpilot.dogfood", build_script.read_text(encoding="utf-8"))
        self.assertNotIn("#!/usr/bin/env bash\nAPP_ROOT=", build_script.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
