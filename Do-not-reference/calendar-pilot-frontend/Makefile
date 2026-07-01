.PHONY: test py-test swift-test browser-e2e mac-app-build demo zip

py-test:
	PYTHONPATH=src python3 -m unittest discover -s tests

swift-test:
	swift test --package-path packages/CalendarPilotKernel

browser-e2e:
	PYTHONPATH=src python3 scripts/run_browser_e2e.py

mac-app-build:
	scripts/build_macos_app.sh

test: py-test swift-test browser-e2e

demo:
	PYTHONPATH=src python3 -m calendar_pilot.app demo --observation data/sample_calendar.json

swift-demo:
	swift run --package-path packages/CalendarPilotKernel CalendarPilotDemo

zip:
	cd .. && zip -r calendar-pilot.zip calendar-pilot -x 'calendar-pilot/.git/*' 'calendar-pilot/**/.build/*' 'calendar-pilot/**/__pycache__/*' 'calendar-pilot/runs/*' 'calendar-pilot/*.zip' 'calendar-pilot/*.sha256'
