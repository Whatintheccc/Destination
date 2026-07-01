#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.request


ROOT = Path(__file__).resolve().parents[1]


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_server(url: str, timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"server did not become ready: {url}")


def main() -> int:
    if shutil.which("npx") is None:
        print("npx is required for browser E2E. Install Node.js/npm, then rerun.", file=sys.stderr)
        return 2
    port = free_port()
    run_dir = ROOT / "runs/browser_e2e/session"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "calendar_pilot.app",
            "frontend",
            "--serve",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--run-dir",
            str(run_dir),
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        base_url = f"http://127.0.0.1:{port}"
        wait_for_server(f"{base_url}/api/state")
        npm_dir = ROOT / "runs/browser_e2e/npm"
        npm_dir.mkdir(parents=True, exist_ok=True)
        package_json = npm_dir / "package.json"
        if not package_json.exists():
            package_json.write_text('{"private":true,"type":"module"}\n', encoding="utf-8")
        if not (npm_dir / "node_modules/@playwright/test").exists():
            install = subprocess.run(
                ["npm", "install", "--silent", "--prefix", str(npm_dir), "@playwright/test@1.61.1"],
                cwd=ROOT,
                text=True,
                check=False,
            )
            if install.returncode != 0:
                return install.returncode
        browser_marker = npm_dir / ".chromium-installed"
        if not browser_marker.exists():
            install_args = [str(npm_dir / "node_modules/.bin/playwright"), "install", "chromium"]
            if sys.platform.startswith("linux"):
                install_args.insert(2, "--with-deps")
            install_browser = subprocess.run(
                install_args,
                cwd=npm_dir,
                text=True,
                check=False,
            )
            if install_browser.returncode != 0:
                return install_browser.returncode
            browser_marker.write_text("ok\n", encoding="utf-8")
        spec_path = npm_dir / "browser_e2e.spec.mjs"
        spec_path.write_text((ROOT / "scripts/browser_e2e.spec.mjs").read_text(encoding="utf-8"), encoding="utf-8")
        env_for_browser = os.environ.copy()
        env_for_browser["CALENDAR_PILOT_BASE_URL"] = base_url
        result = subprocess.run(
            [str(npm_dir / "node_modules/.bin/playwright"), "test", str(spec_path), "--reporter=line"],
            cwd=npm_dir,
            env=env_for_browser,
            text=True,
            check=False,
        )
        return result.returncode
    finally:
        server.terminate()
        try:
            server.wait(timeout=3)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
