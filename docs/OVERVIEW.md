# Overview — implementation and integration contract

## Current outcome

The full desktop Overview is implemented at `/overview`: greeting/period controls, four summary cards, quick actions, income/expense chart, category donut/legend, budgets, rule-based insight, goals and server-filtered recent transactions. It uses the existing protected application layout and expandable sidebar, not a second shell. Authentication retains its existing post-login confirmation route, with an **Open Overview** link.

The UI is composed of live React/HTML text and controls and scalable SVG charts. Original Figma icons are stored locally. No Overview screenshot is used as runtime UI.

## Figma and assets

Source: `kpEbLoKLaLiUcB8Q6xxgRl`, page `2001:5464`, frame `2001:5465`, 1440 × 2220. Individually inspected topbar, greeting, summary, quick actions, analytics, budgets, insight, goals and recent table through the connected Figma Plugin API. Exported vector-bearing icon children using supported `exportAsync({format:'SVG'})`; structurally validated XML and rejected raster/script dependencies. Original balance-toggle variants `65:111` and `65:121` supply the visible/hidden eye. `public/assets/overview/provenance.json` records all 23 exact source node IDs. Original sidebar Budgets and Financial Goals geometry is reused for matching quick actions; corrected authentication assets remain intact.

Figma components are translated into reusable React presentation, not claimed as executable imported Figma instances. Data-driven bars and donut segments are generated SVG using the inspected chart structure/colors. Figma's fixed demo chart paths are not used to misrepresent live amounts.

## Frontend structure

- `Overview.tsx`: reporting period, explicitly selected dataset, independent summary/insight resources and composition.
- `OverviewCards.tsx`: summary, section heading, error/empty state, chart, category legend, budgets, insight and goals.
- `RecentTransactions.tsx`: bounded server query, debounced search, category/type/date filters, paging and read-only detail dialog.
- `services/overviewApi.ts`, `useOverviewResource.ts`, `types.ts`: requests, typed contracts, cancellation, timeout, retries and session-expiry handling.
- Shared `ApplicationHeader`: page navigation search, actual account/settings/signout, notifications availability disclosure and privacy control.
- Shared `ApplicationPreferences`: one layout-wide privacy state and report label. Only a boolean UI preference is stored under `fincept.money.hidden`; no monetary records, tokens or credentials are stored in localStorage. Every amount, including SVG axis/accessible labels, tooltip, insight and detail dialog, passes through the privacy boundary.
- `Dialog`: native modal dialog with browser focus trapping, Escape and close button. `Icon`: local original SVG geometry through CSS alpha masks; state color follows currentColor.

Privacy masking is a presentation convenience, **not encryption or a network/data-access security boundary**. Authenticated API responses still contain authorized amounts. Sidebar state remains in its existing persistent parent.

## Canonical database and accounting

SQLite schema version 2 initializes additive tables: `financial_workspaces`, `wallets`, `transactions`, `budgets`, `financial_goals`. Existing users/sessions/rate limits are preserved. Future segments must use these canonical tables instead of introducing separate Overview copies. Back up an existing database before any update. Initialization is idempotent; no user databases are included in the ZIP.

All monetary storage uses integer minor units (paisa). Response numbers use taka. User and dataset constraints isolate records; composite foreign keys prevent cross-owner/dataset wallet references. Queries always apply authenticated ownership.

- Available Balance = sum of wallet opening positions plus signed ledger movements through the selected period end, never merely income minus expenses.
- A transfer debits its source and credits its destination once; principal is excluded from income/expenses. An explicit linked expense records a transfer fee once.
- Income/expenses/net use the selected inclusive calendar date window. Savings rate = `(income − expenses) / income × 100`; no income yields null rather than a fabricated percentage. Negative rates are allowed.
- Comparison uses previous calendar week/month/year, or the equally sized immediately preceding custom range. A zero previous amount yields no percentage comparison.
- Cash-flow bars show six historical weeks/months/years ending at the reporting period end; their date range is visibly labeled **Historical context**. Summary mini-cards remain the selected-period totals. A partial last bucket is clipped at the selected end. They are not falsely presented as the sum of all six bars.
- Category totals use the same expense records; missing categories become Other. Category legend/order follows the Figma categories, not hard-coded amounts.
- Budget spending intersects budget dates and selected dates. Percentages retain the actual value above 100; the visual bar is capped. Zero limits never divide by zero. Over-budget remaining is negative in the API, displayed as “over.” Near-limit threshold is 80%.
- Goals read persisted earmarked balances, not new income. Percentages use saved/target, bars cap at 100; whole-percent labels are floored to match Figma. Missing/zero targets and missing target dates are explicit.
- Insights are deterministic observations prioritizing over-budget, near-limit and negative cash flow. They are labeled rule-based, not a fabricated LLM response. Amounts stay structured for privacy masking.
- Recent transactions are bounded (default 6, max 25) and ordered newest date then ID. Literal, case-insensitive substring search does not interpolate SQL or treat user input as LIKE wildcards.

## API

All endpoints require the existing HttpOnly cookie session. POST additionally uses the existing origin/custom-header CSRF checks.

| Endpoint | Purpose |
|---|---|
| `GET /api/overview/summary` | Period summary, categories, chart buckets, budgets, goals |
| `GET /api/overview/insights` | Independently retryable deterministic observation |
| `GET /api/overview/recent-transactions` | Bounded search/filter/pagination |
| `POST /api/overview/demo` | Explicit development-only, isolated sample-workspace initialization |

Shared query: `period=this_month|this_week|last_month|this_year|custom`, `dataset=live|demo`, optional ISO `start/end` for custom. Summary also accepts `grouping=weekly|monthly|yearly`. Recent also accepts `search`, `category`, `kind=income|expense|transfer`, `page`, `limit`. Dates are validated, custom ranges limited to 732 days, years 1901–2100. Invalid inputs return safe 422 responses; 401 triggers session recheck. Production rejects sample creation and sample queries with 403.

## Live vs sample data

New accounts have zero/empty states, never Figma's illustrative balances as real records. “Explore sample data” explicitly creates a separate `dataset=demo` workspace for that authenticated user; it does not write live records. The UI continuously labels sample mode. Going back to live data, navigating away, or refreshing returns to live mode. Sample records remain in the isolated development dataset and initialization is idempotent.

The sample is anchored to the month in which it is first created, not continually regenerated on refresh. Six months of ledger history reconcile the displayed totals. Its illustrative opening bank overdraft is deliberate to reconcile the complete six-month ledger to the closing sample balance. Sample goals are independent earmarked progress, not assertions that their combined targets are liquid cash. No sample/test database, account or credentials are shipped.

## Honest integration boundaries

- Add transaction, create/manage budget, set goal, category drill-down, View all and edit/delete actions navigate to existing protected feature destinations, retaining non-sensitive intent/category/date/record IDs. Those future segments explicitly say their flow is not connected and **no records changed**. Overview does not implement duplicate financial CRUD.
- Overview's transaction View opens real read-only details. Edit/Delete do not pretend to mutate records.
- Ask AI opens the AI Assistant integration destination; no LLM is configured. Insights are rule-based.
- Page search navigates application pages, not unimplemented cross-record search.
- Notifications explicitly disclose that no notification delivery/storage service is connected; no fake unread badge.
- Live financial write flows are intentionally deferred to their own segments. Until then new accounts remain empty unless canonical records are populated by an authorized integration. This is not a deployed banking connection.
- Google OAuth, reset email and final legal content retain their existing Authentication limitations.

## Desktop fidelity and verification

Compared the actual 1440px rendered sample page against the original Figma screenshot. Opened the 1024px expanded-sidebar full page as well. The principal composition, orange income card, green/orange chart, donut, budgets, insight, goals and transaction table are preserved. Original Manrope and taka fallback remain local.

Intentional differences: current authenticated name/time/period rather than baked demo copy; visible sample provenance and historical-chart context; rule-based and future-integration disclosures; tooltips appear on hover/focus instead of being permanently painted; actual calculation rounding, date and row ordering. At narrower desktop workspace widths, cards wrap/stack and the table scrolls internally so the page never overflows. The 1440px sample page is slightly taller than the 2220px Figma frame due to disclosures and live layout. No mobile or tablet navigation/layout was added. Cross-platform font antialiasing is not guaranteed pixel-identical.

Automated desktop geometry tests cover 1440 × 900, 1366 × 768, 1280 × 800 and 1024 × 768 in **both** sidebar states. Captures are under `docs/overview-qa/`. Unit, backend and browser results are recorded in IMPLEMENTATION_STATUS.md.

## Run and checks

Use root START_HERE.md. Existing Node/npm and Python dependencies suffice; no new frontend packages/provider secrets are required.

```sh
# Backend (activate backend/.venv first)
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
# Frontend (second terminal, project root)
npm ci
npm run dev
# Checks
npm run build
npm test
npm run test:e2e
# Backend tests, from backend
python -m pytest -q
```

Browser checks require Playwright Chromium (`python` on PATH for its API test server); `PYTHON_BIN` and `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` may select existing binaries. Normal browser runs do not need these overrides.

## Transactions integration update

The later Transactions segment is now implemented. Overview Add Transaction and recent edit/delete links open actual backend-connected dialogs, preserving the selected sample/live dataset. Category and View all links carry context. Overview remains the existing read-side dashboard and re-queries the shared canonical ledger when revisited. Earlier statements about not-yet-connected Transactions actions describe the original Overview-only delivery; see TRANSACTIONS.md and IMPLEMENTATION_STATUS.md for current behavior.
