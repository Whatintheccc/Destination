#!/usr/bin/env python3
"""Untrusted, stdlib-only PolicyPayload proposer executed inside the OS sandbox."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


def canonical(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def denied_attempt(kind: str, operation: str, target: Path) -> dict[str, object]:
    try:
        if operation == "read":
            with target.open("rb") as handle:
                handle.read(1)
        else:
            with target.open("r+b"):
                pass
    except OSError as error:
        return {"kind": kind, "target": str(target), "operation": operation, "outcome": "denied", "errno": error.errno}
    return {"kind": kind, "target": str(target), "operation": operation, "outcome": "succeeded", "errno": None}


def main() -> int:
    request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    search_path = Path(request["search_path"])
    search_rows = [json.loads(line) for line in search_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not search_rows:
        raise ValueError("optimizer search partition is empty")
    proposal_path = Path(request["proposal_path"])
    payload = {
        "policy_payload_schema_version": "policy_payload.v1",
        "payload_id": request["payload_id"],
        "parent_payload_id": request.get("parent_payload_id"),
        "policy_parameters": request["policy_parameters"],
        "respondents": request["respondents"],
        "prompts": request["prompts"],
        "compatibility": request["compatibility"],
        "training": {
            "partition_id": request["search_partition_id"],
            "row_count": len(search_rows),
            "row_set_sha256": sha256_file(search_path),
        },
        "resources": request["resources"],
    }
    payload["content_sha256"] = sha256_bytes(canonical(payload))
    proposal_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    attempts = [
        denied_attempt(row["kind"], row["operation"], Path(row["target"]))
        for row in request["protected_attempts"]
    ]
    decision = "pass" if all(row["outcome"] == "denied" and row["errno"] in {1, 13} for row in attempts) else "fail"
    print(json.dumps({
        "proposal": {"path": str(proposal_path), "sha256": sha256_file(proposal_path), "write_succeeded": True},
        "search_artifact_sha256": sha256_file(search_path),
        "attempts": attempts,
        "decision": decision,
    }, sort_keys=True))
    return 0 if decision == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
