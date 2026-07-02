.PHONY: py-test swift-test swift-ipc-test browser-e2e live-codex-e2e live-diffusiongemma-e2e live-eventkit-e2e replay-offline-tuning-loop check-invariants evidence-bundle mac-app-build desktop-shortcut test dogfood-release demo swift-demo

APP_DIR := calendar-pilot-system-framework

py-test:
	$(MAKE) -C "$(APP_DIR)" py-test

swift-test:
	$(MAKE) -C "$(APP_DIR)" swift-test

swift-ipc-test:
	$(MAKE) -C "$(APP_DIR)" swift-ipc-test

browser-e2e:
	$(MAKE) -C "$(APP_DIR)" browser-e2e

live-codex-e2e:
	$(MAKE) -C "$(APP_DIR)" live-codex-e2e

live-diffusiongemma-e2e:
	$(MAKE) -C "$(APP_DIR)" live-diffusiongemma-e2e

live-eventkit-e2e:
	$(MAKE) -C "$(APP_DIR)" live-eventkit-e2e

replay-offline-tuning-loop:
	$(MAKE) -C "$(APP_DIR)" replay-offline-tuning-loop

check-invariants:
	$(MAKE) -C "$(APP_DIR)" check-invariants

evidence-bundle:
	$(MAKE) -C "$(APP_DIR)" evidence-bundle

mac-app-build:
	$(MAKE) -C "$(APP_DIR)" mac-app-build

desktop-shortcut:
	$(MAKE) -C "$(APP_DIR)" desktop-shortcut

test: py-test swift-test check-invariants

dogfood-release:
	$(MAKE) -C "$(APP_DIR)" dogfood-release

demo:
	$(MAKE) -C "$(APP_DIR)" demo

swift-demo:
	$(MAKE) -C "$(APP_DIR)" swift-demo
