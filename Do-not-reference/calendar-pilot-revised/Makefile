.PHONY: test py-test swift-test demo zip

py-test:
	PYTHONPATH=src python3 -m unittest discover -s tests

swift-test:
	swift test --package-path packages/CalendarPilotKernel

test: py-test swift-test

demo:
	PYTHONPATH=src python3 -m calendar_pilot.app demo --observation data/sample_calendar.json

swift-demo:
	swift run --package-path packages/CalendarPilotKernel CalendarPilotDemo

zip:
	cd .. && zip -r calendar-pilot.zip calendar-pilot -x 'calendar-pilot/.git/*' 'calendar-pilot/**/.build/*' 'calendar-pilot/**/__pycache__/*'
