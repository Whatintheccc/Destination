

.PHONY: test py-test swift-test swift-ipc-test browser-e2e live-codex-e2e live-diffusiongemma-e2e live-eventkit-e2e replay-offline-tuning-loop frontier-diff scorecard contract-vectors ml-ladder check-invariants evidence-bundle lab-validate-seeds lab-run lab-compare lab-promote architecture-evals architecture-eval-test architecture-evals-v2 architecture-eval-v2-test p13-ruler-test p13-attestation-scaffold-test p13-no-effect-test p13-cited-read-side-test p13-deterministic-sandbox-test p13-eventkit-sandbox-test p13-deterministic-retirement-test p13-loc-report p13-instrument wave-bind binding-manifest-verify cvar-report cvar-report-v2 b-migrate b-migrate-v2 wave-harness p12-measurement p12-signals p12-calibration p12-provider-capabilities p12-release mac-app-build desktop-shortcut dogfood-release demo zip
.NOTPARALLEL: wave-harness

py-test:
	PYTHONPATH=src python3 -m unittest discover -s tests

swift-test:
	swift test --package-path packages/CalendarPilotKernel

swift-ipc-test:
	CALENDAR_PILOT_RUN_SWIFT_IPC_TESTS=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_swift_ipc_runtime.py'

browser-e2e:
	PYTHONPATH=src python3 scripts/run_browser_e2e.py

live-codex-e2e:
	PYTHONPATH=src python3 scripts/run_live_codex_e2e.py

live-diffusiongemma-e2e:
	PYTHONPATH=src python3 scripts/run_live_diffusiongemma_e2e.py

live-eventkit-e2e:
	PYTHONPATH=src python3 scripts/run_live_eventkit_e2e.py

replay-offline-tuning-loop:
	PYTHONPATH=src python3 scripts/run_replay_offline_tuning_loop.py

frontier-diff:
	PYTHONPATH=src python3 scripts/run_frontier_diff.py --out runs/frontier_diff.json

scorecard:
	PYTHONPATH=src python3 scripts/make_scorecard.py --replay tests/fixtures/replay_golden.jsonl --frontier-diff runs/frontier_diff.json --out runs/ml_scorecard.json

contract-vectors:
	PYTHONPATH=src python3 scripts/run_contract_vectors.py

ml-ladder: py-test check-invariants frontier-diff scorecard
	@echo "ML ladder artifacts written under runs/."

check-invariants:
	PYTHONPATH=src python3 scripts/check_invariants.py --replay tests/fixtures/replay_golden.jsonl

evidence-bundle:
	mkdir -p runs/ci_evidence
	PYTHONPATH=src python3 -m calendar_pilot.app frontend --write-snapshot --out runs/ci_evidence/frontend_state.json
	PYTHONPATH=src python3 scripts/check_invariants.py --replay tests/fixtures/replay_golden.jsonl --out runs/ci_evidence/invariants.json
	PYTHONPATH=src python3 scripts/run_secret_scan.py --path runs/ci_evidence

lab-validate-seeds:
	PYTHONPATH=src python3 scripts/seed_calendar_corpus.py --validate

lab-run:
	PYTHONPATH=src python3 scripts/run_lab_experiment.py --seed $(SEED) --runtime $(RUNTIME)

lab-compare:
	PYTHONPATH=src python3 scripts/compare_lab_runs.py --reindex --out experiments/reports/comparison_latest.json

lab-promote:
	PYTHONPATH=src python3 scripts/promote_policy.py --batch $(BATCH)

architecture-evals:
	CALENDAR_PILOT_ARCH_EVAL_ACCESS_POINT='make architecture-evals' PYTHONPATH=src python3 evals/architecture/run_architecture_evals.py

architecture-eval-test:
	PYTHONPATH=src:tests python3 -m unittest test_architecture_evals

architecture-eval-v2-test:
	PYTHONPATH=src:tests python3 -m unittest test_architecture_evals_v2

architecture-evals-v2:
	@test -n "$(P13_VERIFY_KEY)" || (echo "P13_VERIFY_KEY is required" >&2; exit 2)
	@test -n "$(P13_MANIFEST)" || (echo "P13_MANIFEST is required" >&2; exit 2)
	CALENDAR_PILOT_ARCH_EVAL_ACCESS_POINT='make architecture-evals-v2' PYTHONPATH=src python3 evals/architecture/run_architecture_evals.py --scenario-set evals/architecture/scenarios/p13_v2.json --binding-manifest "$(P13_MANIFEST)" --verification-key "$(P13_VERIFY_KEY)" --out runs/architecture_evals/architecture_eval_report_v2.json

p13-ruler-test:
	PYTHONPATH=src:tests python3 -m unittest test_p13_ruler

p13-attestation-scaffold-test:
	PYTHONPATH=src:tests python3 -m unittest test_p13_attestation_scaffold

p13-no-effect-test:
	PYTHONPATH=src:tests:. python3 -m unittest test_p13_no_effect_vertical

p13-cited-read-side-test:
	PYTHONPATH=src:tests:. python3 -m unittest test_p13_cited_read_side

p13-deterministic-sandbox-test:
	PYTHONPATH=src:tests:. python3 -m unittest test_p13_deterministic_sandbox

p13-eventkit-sandbox-test:
	PYTHONPATH=src:tests:. python3 -m unittest test_p13_eventkit_sandbox

p13-deterministic-retirement-test:
	PYTHONPATH=src:tests:. python3 -m unittest test_p13_deterministic_retirement

p13-loc-report:
	PYTHONPATH=src python3 scripts/run_p13_loc_report.py --out runs/p13_loc_report.json

P13_VERIFY_KEY ?=
P13_SIGNING_KEY ?=
P13_INSTRUMENT ?= runs/p13_instrument_bundle.json
P13_SCOPE ?= experiments/waves/$(WAVE).scope.json
P13_MANIFEST ?= runs/p13_manifests/$(WAVE).json
CHANGE_CLASS ?=

p13-instrument:
	@test -n "$(P13_VERIFY_KEY)" || (echo "P13_VERIFY_KEY is required" >&2; exit 2)
	PYTHONPATH=src python3 scripts/make_p13_instrument_bundle.py --verification-key "$(P13_VERIFY_KEY)" --out "$(P13_INSTRUMENT)"

wave-bind: p13-instrument
	@test -n "$(WAVE)" || (echo "WAVE is required" >&2; exit 2)
	@test -n "$(CHANGE_CLASS)" || (echo "CHANGE_CLASS is required" >&2; exit 2)
	@test -n "$(P13_SIGNING_KEY)" || (echo "P13_SIGNING_KEY is required" >&2; exit 2)
	PYTHONPATH=src python3 scripts/make_binding_manifest.py --wave "$(WAVE)" --change-class "$(CHANGE_CLASS)" --scope "$(P13_SCOPE)" --instrument-bundle "$(P13_INSTRUMENT)" --signing-key "$(P13_SIGNING_KEY)" --verification-key "$(P13_VERIFY_KEY)" --out "$(P13_MANIFEST)"

binding-manifest-verify:
	@test -n "$(P13_VERIFY_KEY)" || (echo "P13_VERIFY_KEY is required" >&2; exit 2)
	@test -n "$(P13_MANIFEST)" || (echo "P13_MANIFEST is required" >&2; exit 2)
	PYTHONPATH=src python3 scripts/verify_binding_manifest.py --manifest "$(P13_MANIFEST)" --verification-key "$(P13_VERIFY_KEY)"

cvar-report:
	PYTHONPATH=src python3 scripts/run_cvar_report.py --out runs/cvar_report.json

cvar-report-v2:
	@test -n "$(P13_MANIFEST)" || (echo "P13_MANIFEST is required" >&2; exit 2)
	@test -n "$(CVAR_BEFORE)" || (echo "CVAR_BEFORE is required" >&2; exit 2)
	@test -n "$(CVAR_AFTER)" || (echo "CVAR_AFTER is required" >&2; exit 2)
	PYTHONPATH=src:. python3 scripts/run_cvar_report_v2.py --manifest "$(P13_MANIFEST)" --before-artifact "$(CVAR_BEFORE)" --after-artifact "$(CVAR_AFTER)" --out runs/cvar_report_v2.json

b-migrate:
	PYTHONPATH=src python3 scripts/run_b_migrate_dual_run.py --out runs/b_migrate_report.json

b-migrate-v2:
	@test -n "$(P13_MANIFEST)" || (echo "P13_MANIFEST is required" >&2; exit 2)
	PYTHONPATH=src:. python3 scripts/run_b_migrate_dual_run_v2.py --manifest "$(P13_MANIFEST)" --out runs/b_migrate_report_v2.json

wave-harness:
	@test -n "$(WAVE)" || (echo "WAVE is required" >&2; exit 2)
	@test -n "$(P13_VERIFY_KEY)" || (echo "P13_VERIFY_KEY is required" >&2; exit 2)
	@test -n "$(P13_MANIFEST)" || (echo "P13_MANIFEST is required" >&2; exit 2)
	PYTHONPATH=src:. python3 scripts/run_p13_wave_gate.py --manifest "$(P13_MANIFEST)" --verification-key "$(P13_VERIFY_KEY)" $(if $(CVAR_BEFORE),--before-cvar-artifact "$(CVAR_BEFORE)",) --out runs/p13_wave_gate_report.json

mac-app-build:
	scripts/build_macos_app.sh

desktop-shortcut:
	scripts/install_desktop_shortcut.sh

dogfood-release:
	PYTHONPATH=src python3 scripts/run_dogfood_release.py

p12-signals:
	PYTHONPATH=src python3 scripts/run_signal_estimators.py --out runs/p12_signal_estimator_report.json --replay-out runs/p12_signal_estimator_replay.jsonl

p12-measurement:
	PYTHONPATH=src python3 scripts/make_measurement_report.py --out runs/p12_measurement_report.json

p12-calibration:
	PYTHONPATH=src python3 scripts/make_calibration_report.py --out runs/p12_calibration_report.json

p12-provider-capabilities:
	PYTHONPATH=src python3 scripts/make_provider_capability_report.py --out runs/p12_provider_capability_report.json

p12-release:
	PYTHONPATH=src python3 scripts/run_p12_release.py


test: py-test swift-test

demo:
	PYTHONPATH=src python3 -m calendar_pilot.app demo --observation data/sample_calendar.json

swift-demo:
	swift run --package-path packages/CalendarPilotKernel CalendarPilotDemo

zip:
	cd .. && zip -r calendar-pilot.zip calendar-pilot -x 'calendar-pilot/.git/*' 'calendar-pilot/**/.build/*' 'calendar-pilot/**/__pycache__/*' 'calendar-pilot/runs/*' 'calendar-pilot/*.zip' 'calendar-pilot/*.sha256'
