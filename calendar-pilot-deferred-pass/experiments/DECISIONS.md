# Lab Decisions

Append-only record for deviations or implementation choices not fully specified by `thin-lab.md`.

## 2026-07-03 — Base Seed Materialization Helper

The v0 spec says base seeds are authored by hand and variants are generated. To make this Codex implementation reproducible inside the current workspace, `scripts/seed_calendar_corpus.py` includes `--write-base-seeds`, a deterministic materialization helper for the locked 20-seed roster. The committed JSON files remain the source of truth and should still receive product review.

## 2026-07-03 — Starter Fixture Hit Rate

The starter fixture batch completed with `expected_intent_hit_rate = 0.60`: `seed_ea_dense_double_bookings` and `seed_burnout_notification_saturation` keep `create_prep_block` as the untuned top-3 behavior while those flagged seeds mark that intent as expected-bad for the D11 leader-change gate. This is retained as model signal rather than silently weakening the flagged-seed expectations. Promotion correctly holds until D11/D12 evidence exists.
