#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "scripts/policy_optimizer_worker.py"


def _path(value: str) -> Path:
    path = Path(value)
    return (path if path.is_absolute() else ROOT / path).resolve()


def _sbpl_literal(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace('"', '\\"')


def _profile(*, sealed: list[Path], proposal_dir: Path) -> str:
    exclusions = " ".join(f'(require-not (literal "{_sbpl_literal(path)}"))' for path in sealed)
    return " ".join([
        "(version 1)",
        "(deny default)",
        "(allow process*)",
        "(allow sysctl-read)",
        "(allow mach-lookup)",
        "(allow ipc-posix-shm)",
        f"(allow file-read* (require-all {exclusions}))",
        f'(allow file-write* (subpath "{_sbpl_literal(proposal_dir)}"))',
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the P13.6 proposal-only optimizer inside a macOS deny-by-default sandbox")
    parser.add_argument("--search", required=True)
    parser.add_argument("--holdout", required=True)
    parser.add_argument("--forward-shadow", required=True)
    parser.add_argument("--evaluator", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--current", required=True)
    parser.add_argument("--effect-tcb", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--payload-id", required=True)
    parser.add_argument("--parent-payload-id", default="")
    parser.add_argument("--policy-parameters", required=True, help="JSON file containing declarative policy parameters")
    parser.add_argument("--out", default="")
    args = parser.parse_args()
    if platform.system() != "Darwin" or not Path("/usr/bin/sandbox-exec").is_file():
        print(json.dumps({"decision": "hold", "reason": "macos-sandbox-exec is unavailable"}, indent=2))
        return 3
    search = _path(args.search)
    holdout = _path(args.holdout)
    forward_shadow = _path(args.forward_shadow)
    proposal_dir = _path(args.out_dir)
    proposal_dir.mkdir(parents=True, exist_ok=True)
    proposal_path = proposal_dir / f"{args.payload_id}.json"
    report_path = _path(args.out) if args.out else proposal_dir / "optimizer_execution_report.json"
    sealed = [holdout, forward_shadow]
    protected = [
        {"kind": "holdout", "operation": "read", "target": str(holdout)},
        {"kind": "forward_shadow", "operation": "read", "target": str(forward_shadow)},
        {"kind": "evaluator", "operation": "write", "target": str(_path(args.evaluator))},
        {"kind": "manifest", "operation": "write", "target": str(_path(args.manifest))},
        {"kind": "current", "operation": "write", "target": str(_path(args.current))},
        {"kind": "effect_tcb", "operation": "write", "target": str(_path(args.effect_tcb))},
    ]
    for row in protected:
        target = Path(row["target"])
        if not target.is_file():
            raise ValueError(f"optimizer attack target must be an existing file: {target}")
        if proposal_dir == target or proposal_dir in target.parents:
            raise ValueError("protected optimizer attack target is inside the proposal write scope")
    request = {
        "search_path": str(search),
        "proposal_path": str(proposal_path),
        "payload_id": args.payload_id,
        "parent_payload_id": args.parent_payload_id or None,
        "policy_parameters": json.loads(_path(args.policy_parameters).read_text(encoding="utf-8")),
        "respondents": ["diffusiongemma.fixture.v1"],
        "prompts": ["policy-payload-proposal.v1"],
        "compatibility": {"reducer_versions": ["product_core.create_prep_block.v1"], "schema_versions": ["policy_tuning.v1"]},
        "search_partition_id": "p13.6.search",
        "resources": {"seed_set_sha256": hashlib.sha256(b"p13.6-fixed-seed-set").hexdigest(), "max_candidates": 1, "max_compute_seconds": 30},
        "protected_attempts": protected,
    }
    request_path = proposal_dir / ".optimizer_request.json"
    request_path.write_text(json.dumps(request, sort_keys=True), encoding="utf-8")
    profile = _profile(sealed=sealed, proposal_dir=proposal_dir)
    process = subprocess.run(
        ["/usr/bin/sandbox-exec", "-p", profile, sys.executable, "-B", "-S", str(WORKER), str(request_path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode != 0:
        print(json.dumps({"decision": "hold", "reason": "optimizer OS boundary did not complete", "returncode": process.returncode, "stderr": process.stderr.strip()}, indent=2))
        return 3
    worker = json.loads(process.stdout)
    proposal_ref = dict(worker["proposal"])
    proposal_ref["path"] = proposal_path.relative_to(ROOT).as_posix()
    report = {
        "optimizer_execution_report_schema_version": "optimizer_execution_report.v1",
        "executor_id": "p13.6-policy-payload-proposer",
        "platform": platform.platform(),
        "boundary": "macos-sandbox-exec",
        "profile_sha256": hashlib.sha256(profile.encode("utf-8")).hexdigest(),
        "search_artifact_sha256": worker["search_artifact_sha256"],
        "proposal": proposal_ref,
        "attempts": worker["attempts"],
        "decision": worker["decision"],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    request_path.unlink()
    print(json.dumps({"decision": report["decision"], "report": str(report_path), "proposal": str(proposal_path)}, indent=2))
    return 0 if report["decision"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
