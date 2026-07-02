from __future__ import annotations

import socket
import unittest

from calendar_pilot.frontend.launcher import select_port


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


if __name__ == "__main__":
    unittest.main()
