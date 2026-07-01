# CalendarPilot Frontend

This is a small static frontend for the agentic calendar optimizer. It is not a chat UI. It exposes the app's machine-learning and machine-acting surfaces:

- **Calendar pressure map**: what raw calendar/task/device state the app inspected.
- **Candidate futures**: DiffusionGemma's generated action frontier, reward anatomy, right-moment estimates, regret and social risk.
- **Acting queue**: staged, committed, denied, and undoable packets with Swift receipts.
- **Authority grants**: Swift-issued grant IDs and where authority came from.
- **Self-play findings**: adversarial failure modes that should tune policy before rollout.
- **Biography repair**: learned profile claims with confidence/provenance repair hooks.

Generate a demo snapshot:

```bash
PYTHONPATH=src python3 -m calendar_pilot.app frontend --write-snapshot
```

Then open `frontend/static/index.html` or serve it:

```bash
PYTHONPATH=src python3 -m calendar_pilot.app frontend --serve
```
