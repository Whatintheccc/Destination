

# CalendarPilot frontend

The frontend is a browser product shell for the local dogfood app.

Run a static snapshot:

```bash
PYTHONPATH=src python3 -m calendar_pilot.app frontend --write-snapshot
```

Run the live fixture-backed app:

```bash
PYTHONPATH=src python3 -m calendar_pilot.app frontend --serve --host 127.0.0.1 --port 8787
```

Primary files:

- `frontend/static/index.html` — left sidebar, chat transcript, composer, inspector drawer.
- `frontend/static/js/main.js` — live `/api/*` calls, action-card controls, replay/profile/self-play inspector controls.
- `frontend/static/styles.css` — product shell styling.
- `src/calendar_pilot/frontend/session.py` — mutable dogfood session state.
- `src/calendar_pilot/frontend/server.py` — static server plus live API endpoints.

The first viewport is intentionally product-oriented: user goal, assistant response, inline candidate/action cards. The dogfood machinery remains in the inspector tabs.
