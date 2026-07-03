

.PHONY: test py-test swift-test swift-ipc-test browser-e2e live-codex-e2e live-diffusiongemma-e2e live-eventkit-e2e replay-offline-tuning-loop frontier-diff scorecard contract-vectors ml-ladder check-invariants evidence-bundle lab-validate-seeds lab-validate-scenarios variance-probe lab-run lab-compare lab-promote mac-app-build desktop-shortcut dogfood-release demo zip

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

lab-validate-scenarios:
	PYTHONPATH=src python3 scripts/validate_self_play_scenarios.py

variance-probe:
	PYTHONPATH=src python3 scripts/run_variance_probe.py

lab-run:
	PYTHONPATH=src python3 scripts/run_lab_experiment.py --seed $(SEED) --runtime $(RUNTIME)

lab-compare:
	PYTHONPATH=src python3 scripts/compare_lab_runs.py --reindex --out experiments/reports/comparison_latest.json

lab-promote:
	PYTHONPATH=src python3 scripts/promote_policy.py --batch $(BATCH)

mac-app-build:
	scripts/build_macos_app.sh

desktop-shortcut:
	scripts/install_desktop_shortcut.sh

dogfood-release:
	PYTHONPATH=src python3 scripts/run_dogfood_release.py

test: py-test swift-test

demo:
	PYTHONPATH=src python3 -m calendar_pilot.app demo --observation data/sample_calendar.json

swift-demo:
	swift run --package-path packages/CalendarPilotKernel CalendarPilotDemo

zip:
	cd .. && zip -r calendar-pilot.zip calendar-pilot -x 'calendar-pilot/.git/*' 'calendar-pilot/**/.build/*' 'calendar-pilot/**/__pycache__/*' 'calendar-pilot/runs/*' 'calendar-pilot/*.zip' 'calendar-pilot/*.sha256'
