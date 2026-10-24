# LeaverGuard — Leaver Access Review Auditor (frontend)

React + Vite + plain CSS. Works without a backend in **demo mode**, which uses clearly synthetic data.

## Run it
```
npm install
npm run dev
```
Open the address Vite prints (normally http://localhost:5173).

## Configuration
Copy `.env.example` to `.env.local` (`copy .env.example .env.local` on Windows) and edit:
- `VITE_DATA_MODE` — `demo` (default) or `live`
- `VITE_API_BASE_URL` — backend base URL; only used in live mode
- `VITE_MOCK_SCENARIO` — demo only: `normal`, `empty`, `error`, `slow` or `save-error`. The first four change how the Findings and Requests pages load; `save-error` loads them normally but makes submitting or deciding a request fail

## Structure
- `src/layouts/` app shell and navigation list
- `src/pages/` one file per screen
- `src/components/` reusable UI pieces
- `src/services/` `api.js` picks the mock or live adapter, so pages never know which one they use; `requestStore.js` keeps demo requests in the browser's localStorage (mock adapter only)
- `src/data/` synthetic demo data (nothing real)
- `src/context/` the demo role (analyst or approver) chosen in the top bar
- `src/hooks/`, `src/utils/` loading hook, formatting, classification and request metadata
- `src/styles/global.css` design tokens and styles

## Milestone status
1 Shell, navigation, design system, overview dashboard (done). 2 Findings table, filters, sorting, evidence drawer (done). 3 Requests and approvals: start a request from a finding, Requests page, approve or reject with comments, demo requests saved in the browser (built, awaiting a local test). 4 onward are built one at a time.

## Safety notes
Disable-only design: this app has no account-deletion feature. Demo data is synthetic. The demo role in the top bar is a label, not authentication or authorization. Approving a request records a decision only; no account is disabled or changed. Demo requests live in this browser's localStorage and can be reset from the Requests page.
