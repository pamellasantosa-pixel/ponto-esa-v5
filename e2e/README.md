# E2E UI Suite

This folder contains end-to-end tests for critical UI flows using Playwright.

## Covered flows
- Login (success and invalid credentials)
- User registration (manager screen)
- Time punch registration
- Overtime approval
- Reports generation and CSV export visibility

## Install
```bash
pip install -r requirements-e2e.txt
python -m playwright install chromium
```

## Run
```bash
python -m pytest -q e2e
```

## Notes
- Tests run the Streamlit app in an isolated temp runtime directory.
- Tests force `USE_POSTGRESQL=false` to avoid external DB dependency.
- The app process is started/stopped automatically by fixtures.
