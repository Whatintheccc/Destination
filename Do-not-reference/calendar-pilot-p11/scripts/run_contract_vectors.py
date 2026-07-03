#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from calendar_pilot.replay import observation_fingerprint
from calendar_pilot.swift_bridge import SwiftKernelStub
from calendar_pilot.swift_bridge.ipc import SwiftKernelIPCClient
from calendar_pilot.types import AuthorityGrant, CandidateCalendarAction, RawCalendarObservation


def run_vector(path: Path, *, swift: bool = False) -> dict:
    vec = json.loads(path.read_text(encoding="utf-8"))
    obs = RawCalendarObservation.from_dict(vec["observation"])
    cand = CandidateCalendarAction.from_dict(vec["candidate"])
    grant = AuthorityGrant.from_dict(vec["grant"])
    kernel = SwiftKernelIPCClient() if swift else SwiftKernelStub()
    try:
        if swift:
            kernel.start()
        restored = getattr(kernel, "restore_authority_grant", None)
        if callable(restored):
            restored(grant)
        else:
            kernel.authority_grants[grant.grant_id] = grant
        receipt = kernel.authorize_and_materialize(cand, obs, authority_grant=grant.grant_id, requested_authority_tier=int(vec.get("requested_authority_tier", cand.required_authority_tier)), correlation_id=vec["vector_id"])
        expect = vec.get("expect", {})
        checks = {
            "sync_status": receipt.sync_status == expect.get("sync_status"),
            "stage_state": receipt.stage_state.value == expect.get("stage_state"),
            "actuation_mode": receipt.actuation_mode.value == expect.get("actuation_mode"),
            "denied_reason": receipt.denied_reason == expect.get("denied_reason"),
            "observation_fingerprint": bool(observation_fingerprint(obs)),
        }
        return {"vector_id": vec["vector_id"], "backend": "swift_ipc" if swift else "python_stub", "ok": all(checks.values()), "checks": checks, "receipt": receipt.to_dict()}
    finally:
        close = getattr(kernel, "close", None)
        if callable(close):
            close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vectors", default="contracts/testdata/kernel_vectors")
    parser.add_argument("--swift", action="store_true")
    parser.add_argument("--out", default="")
    args = parser.parse_args()
    results = [run_vector(path, swift=args.swift) for path in sorted(Path(args.vectors).glob("*.json"))]
    payload = {"ok": all(r["ok"] for r in results), "results": results}
    text = json.dumps(payload, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    raise SystemExit(0 if payload["ok"] else 1)

if __name__ == "__main__":
    main()