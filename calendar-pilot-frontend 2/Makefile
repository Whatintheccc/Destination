.PHONY: test py-test swift-test swift-ipc-test browser-e2e mac-app-build desktop-shortcut dogfood-release demo zip

py-test:
	PYTHONPATH=src python3 -m unittest discover -s tests

swift-test:
	swift test --package-path packages/CalendarPilotKernel

swift-ipc-test:
	CALENDAR_PILOT_RUN_SWIFT_IPC_TESTS=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_swift_ipc_runtime.py'

browser-e2e:
	PYTHONPATH=src python3 scripts/run_browser_e2e.py

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
