APP_DIR := calendar-pilot-p12

DELEGATED_TARGETS := \
	test py-test swift-test swift-ipc-test \
	browser-e2e live-codex-e2e live-diffusiongemma-e2e live-eventkit-e2e \
	replay-offline-tuning-loop frontier-diff scorecard contract-vectors ml-ladder \
	check-invariants evidence-bundle \
	lab-validate-seeds lab-run lab-compare lab-promote \
	architecture-evals architecture-eval-test architecture-evals-v2 architecture-eval-v2-test \
	p13-ruler-test p13-attestation-scaffold-test p13-loc-report \
	p13-instrument wave-bind binding-manifest-verify cvar-report cvar-report-v2 b-migrate b-migrate-v2 wave-harness \
	p12-measurement p12-signals p12-calibration p12-provider-capabilities p12-release \
	mac-app-build desktop-shortcut dogfood-release demo swift-demo zip

.PHONY: $(DELEGATED_TARGETS)

$(DELEGATED_TARGETS):
	$(MAKE) -C "$(APP_DIR)" $@
