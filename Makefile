.PHONY: py-test swift-test browser-e2e mac-app-build test dogfood-release

APP_DIR := calendar-pilot-frontend 2

py-test:
	$(MAKE) -C "$(APP_DIR)" py-test

swift-test:
	$(MAKE) -C "$(APP_DIR)" swift-test

browser-e2e:
	$(MAKE) -C "$(APP_DIR)" browser-e2e

mac-app-build:
	$(MAKE) -C "$(APP_DIR)" mac-app-build

test: py-test swift-test

dogfood-release:
	$(MAKE) -C "$(APP_DIR)" dogfood-release
