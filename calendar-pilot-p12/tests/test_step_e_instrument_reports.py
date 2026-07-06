import json
import tempfile
import unittest
from pathlib import Path

from scripts.make_reward_head_report import build_report as build_reward_report
from scripts.make_belief_explain_report import build_report as build_belief_explain_report
from scripts.make_calibration_report import build_report as build_calibration_report
from scripts.run_p12_release import release_decision
from scripts.run_policy_ablation import build_report as build_ablation_report


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


class StepEInstrumentReportTests(unittest.TestCase):
    def test_reward_heads_hold_when_no_action_reward_rows_are_consumed(self):
        with tempfile.TemporaryDirectory() as td:
            replay = Path(td) / "empty_reward.jsonl"
            write_jsonl(replay, [
                {
                    "record_schema_version": "r1",
                    "record_type": "receipt",
                    "record_id": "receipt:1",
                    "trace_id": "trace_1",
                    "signal_stream": "action",
                    "payload": {"receipt": {"receipt_id": "receipt_1"}},
                }
            ])

            report = build_reward_report(replay_path=replay)

        self.assertEqual(report["decision"], "hold")
        self.assertEqual(report["reward_evidence"]["consumed_action_rows"], 0)
        self.assertIn("no ActionStream reward rows consumed", report["hold_reasons"][0]["reason"])

    def test_reward_heads_fail_and_name_non_action_reward_row_ids(self):
        with tempfile.TemporaryDirectory() as td:
            replay = Path(td) / "bad_reward.jsonl"
            write_jsonl(replay, [
                {
                    "record_schema_version": "r1",
                    "record_type": "semantic_signal",
                    "record_id": "sig_reward",
                    "trace_id": "trace_bad",
                    "signal_stream": "derived",
                    "payload": {
                        "candidate": {"candidate_id": "cand_bad", "intent": "create_prep_block"},
                        "reward": {"reward_event_id": "reward_bad", "total_reward": 1.0},
                    },
                }
            ])

            report = build_reward_report(replay_path=replay)

        self.assertEqual(report["decision"], "fail")
        self.assertEqual(report["reward_evidence"]["non_action_stream_reward_rows"], 1)
        self.assertEqual(report["reward_evidence"]["reward_purity_violations"][0]["record_id"], "sig_reward")

    def test_reward_heads_pass_when_action_stream_reward_evidence_exists(self):
        with tempfile.TemporaryDirectory() as td:
            replay = Path(td) / "good_reward.jsonl"
            write_jsonl(replay, [
                {
                    "record_schema_version": "r1",
                    "record_type": "reward",
                    "record_id": "reward:good",
                    "trace_id": "trace_good",
                    "signal_stream": "action",
                    "payload": {
                        "candidate": {"candidate_id": "cand_good", "intent": "create_prep_block"},
                        "reward": {
                            "reward_event_id": "reward_good",
                            "total_reward": 1.0,
                            "utility_reward": 1.0,
                            "acceptance_reward": 1.0,
                            "engagement_reward": 0.0,
                            "regret_penalty": 0.0,
                            "interruption_penalty": 0.0,
                            "social_risk_penalty": 0.0,
                        },
                    },
                }
            ])

            report = build_reward_report(replay_path=replay)

        self.assertEqual(report["decision"], "pass")
        self.assertEqual(report["reward_evidence"]["consumed_action_rows"], 1)
        self.assertEqual(report["reward_head_deltas"]["utility_delta"], 1.0)

    def test_reward_heads_can_consume_multiple_real_replay_inputs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            empty_replay = root / "empty.jsonl"
            reward_replay = root / "reward.jsonl"
            write_jsonl(empty_replay, [
                {
                    "record_schema_version": "r1",
                    "record_type": "receipt",
                    "record_id": "receipt:1",
                    "trace_id": "trace_1",
                    "signal_stream": "action",
                    "payload": {"receipt": {"receipt_id": "receipt_1"}},
                }
            ])
            write_jsonl(reward_replay, [
                {
                    "record_schema_version": "r1",
                    "record_type": "reward",
                    "record_id": "reward:multi",
                    "trace_id": "trace_multi",
                    "signal_stream": "action",
                    "payload": {
                        "reward": {
                            "reward_event_id": "reward_multi",
                            "utility_reward": 0.2,
                            "regret_penalty": 0.0,
                            "interruption_penalty": 0.0,
                            "social_risk_penalty": 0.0,
                        }
                    },
                }
            ])

            report = build_reward_report(replay_paths=[empty_replay, reward_replay])

        self.assertEqual(report["decision"], "pass")
        self.assertEqual(report["reward_evidence"]["consumed_action_rows"], 1)
        self.assertEqual(len(report["reward_evidence"]["source_replays"]), 2)

    def test_policy_ablation_holds_on_empty_inputs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            frontier = root / "frontier.json"
            scorecard = root / "scorecard.json"
            reward = root / "reward.json"
            write_json(frontier, {})
            write_json(scorecard, {})
            write_json(reward, {})

            report = build_ablation_report(
                candidate="candidate",
                current="CURRENT",
                frontier_diff_path=frontier,
                scorecard_path=scorecard,
                reward_heads_path=reward,
            )

        self.assertEqual(report["decision"], "hold")
        self.assertTrue(report["hold_reasons"])
        for row in report["ablations"].values():
            self.assertEqual(row["promotion_decision"], "hold")

    def test_policy_ablation_uses_named_frontier_scorecard_and_reward_inputs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            frontier = root / "frontier.json"
            scorecard = root / "scorecard.json"
            reward = root / "reward.json"
            write_json(frontier, {
                "avg_marginal_reward_delta": 0.05,
                "baseline_leader": "cand_a",
                "tuned_leader": "cand_b",
                "marginal_leader_changed": True,
                "tuned_frontier": [{"candidate_id": "cand_b"}],
                "per_candidate_marginal_delta": {"cand_b": {"delta": 0.05}},
            })
            write_json(scorecard, {
                "decision": "promote_candidate",
                "frontier": {"valid_candidates": 1},
                "learning": {"training_rows": 1},
                "invariants": {"violations": 0, "details": []},
            })
            write_json(reward, {
                "decision": "pass",
                "reward_head_deltas": {"utility_delta": 0.1, "regret_delta": 0.0},
            })

            report = build_ablation_report(
                candidate="candidate",
                current="CURRENT",
                frontier_diff_path=frontier,
                scorecard_path=scorecard,
                reward_heads_path=reward,
            )

        self.assertEqual(report["decision"], "pass")
        self.assertTrue(report["input_artifacts"]["frontier_diff"]["sha256"])
        self.assertEqual(report["ablations"]["no_semantic_labels"]["signal_layer_assessment"]["load_bearing"], False)
        self.assertEqual(report["ablations"]["no_derived_signals"]["promotion_decision"], "pass")

    def test_policy_ablation_writes_per_ablation_rerun_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            frontier = root / "frontier.json"
            scorecard = root / "scorecard.json"
            reward = root / "reward.json"
            evidence_dir = root / "ablation_evidence"
            write_json(frontier, {
                "avg_marginal_reward_delta": 0.0,
                "baseline_leader": "cand_a",
                "tuned_leader": "cand_a",
                "marginal_leader_changed": False,
                "tuned_frontier": [{"candidate_id": "cand_a"}],
                "per_candidate_marginal_delta": {"cand_a": {"delta": 0.0}},
            })
            write_json(scorecard, {
                "decision": "promote_candidate",
                "replay_path": "tests/fixtures/replay_golden.jsonl",
                "frontier": {"valid_candidates": 1},
                "learning": {"training_rows": 1},
                "invariants": {"violations": 0, "details": []},
            })
            write_json(reward, {
                "decision": "pass",
                "reward_head_deltas": {"utility_delta": 0.1, "regret_delta": 0.0},
            })

            report = build_ablation_report(
                candidate="candidate",
                current="CURRENT",
                frontier_diff_path=frontier,
                scorecard_path=scorecard,
                reward_heads_path=reward,
                evidence_dir=evidence_dir,
            )

        self.assertEqual(report["decision"], "pass")
        frontier_paths = {
            row["ablation_evidence"]["frontier_diff"]["path"]
            for row in report["ablations"].values()
        }
        scorecard_paths = {
            row["ablation_evidence"]["scorecard"]["path"]
            for row in report["ablations"].values()
        }
        self.assertEqual(len(frontier_paths), len(report["ablations"]))
        self.assertEqual(len(scorecard_paths), len(report["ablations"]))
        self.assertTrue(all(row["ablation_evidence"]["rerun"] for row in report["ablations"].values()))

    def test_calibration_holds_without_matched_real_feedback_examples(self):
        with tempfile.TemporaryDirectory() as td:
            replay = Path(td) / "no_feedback.jsonl"
            write_jsonl(replay, [
                {
                    "record_schema_version": "r1",
                    "record_type": "reward",
                    "record_id": "reward:no_candidate",
                    "trace_id": "trace",
                    "signal_stream": "action",
                    "payload": {
                        "reward": {
                            "reward_event_id": "reward_no_candidate",
                            "receipt_id": "receipt_no_candidate",
                            "total_reward": 0.9,
                            "explicit_useful": True,
                            "provenance": "human_ui",
                        }
                    },
                }
            ])

            report = build_calibration_report(replay_paths=[replay], family="create_prep_block")

        self.assertEqual(report["decision"], "hold")
        self.assertEqual(report["matched_examples"], 0)
        self.assertIn("insufficient matched real examples", report["known_biases"])

    def test_calibration_passes_with_real_action_feedback_and_reward_rows(self):
        with tempfile.TemporaryDirectory() as td:
            replay = Path(td) / "feedback.jsonl"
            candidate = {
                "candidate_id": "cand_feedback",
                "intent": "create_prep_block",
                "predicted_acceptance": 0.6,
                "predicted_regret": 0.1,
            }
            receipt = {"receipt_id": "receipt_feedback", "sync_status": "committed"}
            write_jsonl(replay, [
                {
                    "record_schema_version": "r1",
                    "record_type": "human_feedback_event",
                    "record_id": "feedback:reward_feedback",
                    "trace_id": "cand_feedback",
                    "signal_stream": "action",
                    "payload": {
                        "candidate": candidate,
                        "receipt": receipt,
                        "feedback_event": {
                            "feedback_event_id": "feedback:reward_feedback",
                            "receipt_id": "receipt_feedback",
                            "feedback": "useful",
                            "reward_event_id": "reward_feedback",
                            "provenance": "human_ui",
                        },
                    },
                },
                {
                    "record_schema_version": "r1",
                    "record_type": "reward",
                    "record_id": "reward:reward_feedback",
                    "trace_id": "cand_feedback",
                    "signal_stream": "action",
                    "payload": {
                        "candidate": candidate,
                        "receipt": receipt,
                        "reward": {
                            "reward_event_id": "reward_feedback",
                            "receipt_id": "receipt_feedback",
                            "total_reward": 0.9,
                            "explicit_useful": True,
                            "provenance": "human_ui",
                        },
                    },
                },
            ])

            report = build_calibration_report(replay_paths=[replay], family="create_prep_block")

        self.assertEqual(report["decision"], "pass")
        self.assertEqual(report["matched_examples"], 1)
        self.assertEqual(report["real_source"], "human_feedback")
        self.assertEqual(report["action_family_metrics"]["create_prep_block"]["acceptance_gap"], 0.4)

    def test_belief_explain_report_covers_required_object_shapes(self):
        report = build_belief_explain_report()

        self.assertEqual(report["decision"], "pass")
        for required in [
            "constructible_belief",
            "common_explain_answer_shape",
            "replay_visible_evidence_row_ids",
            "authority_denial",
            "authority_revocation",
            "candidate",
            "provider",
            "trajectory",
        ]:
            self.assertTrue(report["requirements"][required], required)

    def test_release_decision_preserves_hold_distinct_from_pass(self):
        self.assertEqual(
            release_decision(
                [{"name": "calibration", "status": "hold"}],
                [{"leg": "live-codex-e2e", "status": "ran"}],
            ),
            "hold",
        )
        self.assertEqual(
            release_decision(
                [{"name": "calibration", "status": "pass"}],
                [{"leg": "live-codex-e2e", "status": "root-listed"}],
            ),
            "hold",
        )
        self.assertEqual(
            release_decision(
                [{"name": "calibration", "status": "pass"}],
                [{"leg": "live-codex-e2e", "status": "signed-root-list"}],
            ),
            "pass",
        )
        self.assertEqual(
            release_decision(
                [{"name": "reward_heads", "status": "fail"}],
                [{"leg": "live-codex-e2e", "status": "ran"}],
            ),
            "fail",
        )


if __name__ == "__main__":
    unittest.main()
