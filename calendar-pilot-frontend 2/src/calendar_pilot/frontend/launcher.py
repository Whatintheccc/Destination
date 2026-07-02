from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.request import urlopen


ALLOWED_SECRET_ENV_KEYS = {
    "CALENDAR_PILOT_NIM_API_KEY",
    "NVIDIA_API_KEY",
    "NIM_API_KEY",
    "CALENDAR_PILOT_NIM_BASE_URL",
    "CALENDAR_PILOT_NIM_MODEL",
    "CALENDAR_PILOT_NIM_CA_FILE",
    "CALENDAR_PILOT_NIM_TIMEOUT",
    "CALENDAR_PILOT_CODEX_BIN",
    "CALENDAR_PILOT_CODEX_MODEL",
    "CALENDAR_PILOT_CODEX_TIMEOUT",
    "CODEX_ACCESS_TOKEN",
}


def select_port(host: str, preferred_port: int, *, strict: bool = False) -> int:
    if _port_available(host, preferred_port):
        return preferred_port
    if strict:
        raise RuntimeError(f"requested port {preferred_port} is already in use")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="calendar-pilot-launcher")
    parser.add_argument("--host", default=os.environ.get("CALENDAR_PILOT_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("CALENDAR_PILOT_PORT", "8787")))
    parser.add_argument("--run-dir", default=os.environ.get("CALENDAR_PILOT_RUN_DIR", str(Path.home() / "Library" / "Application Support" / "CalendarPilot")))
    parser.add_argument("--app-root", default=os.environ.get("CALENDAR_PILOT_APP_ROOT", str(Path.cwd())))
    args = parser.parse_args(argv)

    run_dir = Path(args.run_dir).expanduser()
    app_root = Path(args.app_root).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    launch_id = os.environ.get("CALENDAR_PILOT_LAUNCH_ID") or f"launch_{uuid.uuid4().hex[:12]}"
    strict_port = os.environ.get("CALENDAR_PILOT_STRICT_PORT") == "1"
    port = select_port(args.host, int(args.port), strict=strict_port)
    base_url = f"http://{args.host}:{port}"
    state_path = run_dir / "launch_state.json"
    log_path = run_dir / "CalendarPilot.log"

    env = os.environ.copy()
    _load_env_files(env, run_dir=run_dir, app_root=app_root)
    env["CALENDAR_PILOT_LAUNCH_ID"] = launch_id
    env["CALENDAR_PILOT_LAUNCH_PORT"] = str(port)
    env["CALENDAR_PILOT_LAUNCH_REQUESTED_PORT"] = str(args.port)
    env["PYTHONPATH"] = str(app_root / "src")
    def write_state(status: str, *, server_pid: int | None, reason: str = "", health: dict[str, Any] | None = None) -> None:
        payload: dict[str, Any] = {
            "status": status,
            "launch_id": launch_id,
            "requested_port": int(args.port),
            "port": port,
            "base_url": base_url,
            "launcher_pid": os.getpid(),
            "server_pid": server_pid,
            "reason": reason,
        }
        if health is not None:
            payload["health"] = health
        _write_launch_state(state_path, **payload)

    write_state("starting", server_pid=None)

    command = [
        sys.executable,
        "-m",
        "calendar_pilot.app",
        "frontend",
        "--serve",
        "--host",
        args.host,
        "--port",
        str(port),
        "--run-dir",
        str(run_dir),
    ]
    with log_path.open("a", encoding="utf-8") as log:
        proc = subprocess.Popen(command, cwd=app_root, env=env, stdout=log, stderr=subprocess.STDOUT, text=True)
        _install_signal_forwarders(proc, lambda signum: write_state("stopped", server_pid=proc.pid, reason=f"signal {signum}"))
        try:
            health = _wait_for_owned_health(base_url, proc, launch_id)
            write_state("running", server_pid=proc.pid, health=health)
            if os.environ.get("CALENDAR_PILOT_OPEN_BROWSER", "1") != "0" and shutil.which("open"):
                subprocess.Popen(["open", base_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            exit_code = proc.wait()
            if exit_code == 0:
                write_state("stopped", server_pid=proc.pid, reason="server exited 0", health=health)
            else:
                write_state("failed", server_pid=proc.pid, reason=f"server exited {exit_code}", health=health)
            return exit_code
        except Exception as exc:
            write_state("failed", server_pid=proc.pid, reason=str(exc))
            _terminate(proc)
            print(f"CalendarPilot launch failed: {exc}", file=sys.stderr)
            return 1


def _wait_for_owned_health(base_url: str, proc: subprocess.Popen[str], launch_id: str) -> dict[str, Any]:
    deadline = time.time() + 20
    last_error: Exception | None = None
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"server exited with code {proc.returncode}")
        try:
            health = _api_get(base_url, "/api/health")
            process = health.get("process", {}) if isinstance(health, dict) else {}
            if process.get("pid") != proc.pid:
                raise RuntimeError(f"health pid {process.get('pid')} did not match launched server pid {proc.pid}")
            if process.get("launch_id") != launch_id:
                raise RuntimeError("health launch id did not match launched app")
            return health
        except Exception as exc:
            last_error = exc
            time.sleep(0.1)
    raise RuntimeError(f"server did not become ready: {last_error}")


def _api_get(base_url: str, path: str) -> dict[str, Any]:
    with urlopen(f"{base_url}{path}", timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def _write_launch_state(path: Path, **payload: Any) -> None:
    payload["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _load_env_files(env: dict[str, str], *, run_dir: Path, app_root: Path) -> list[Path]:
    configured = env.get("CALENDAR_PILOT_SECRETS_FILE", "")
    paths = [Path(configured).expanduser()] if configured else [
        run_dir / "secrets.env",
        run_dir / ".env",
        app_root / ".env",
    ]
    loaded: list[Path] = []
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            parsed = _parse_env_line(raw_line)
            if parsed is None:
                continue
            key, value = parsed
            if key in ALLOWED_SECRET_ENV_KEYS and key not in env:
                env[key] = value
        loaded.append(path)
    return loaded


def _parse_env_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    key = key.strip()
    if not key or not key.replace("_", "").isalnum():
        return None
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return key, value


def _port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
        return True


def _install_signal_forwarders(proc: subprocess.Popen[str], on_signal) -> None:
    def forward(_signum: int, _frame: object) -> None:
        _terminate(proc)
        on_signal(_signum)
        raise SystemExit(0)

    try:
        signal.signal(signal.SIGTERM, forward)
        signal.signal(signal.SIGINT, forward)
    except ValueError:
        pass


def _terminate(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)


if __name__ == "__main__":
    raise SystemExit(main())
