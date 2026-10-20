# Insights source inventory

This inventory covers the complete Insights implementation, including the backend foundations started before the provider handoff. No Git repository/baseline ZIP was present, so this is an explicit touched-file inventory, not a claim of a byte-for-byte diff against an unavailable archive.

## Added runtime source

- `src/features/insights/Insights.tsx` — route, URL filters, loading/reload/abort, dialogs and toast.
- `src/features/insights/types.ts` — API and range types.
- `src/features/insights/format.ts` — dates, comparisons, colors, chart scale and minor-unit formatting.
- `src/features/insights/api.ts` — authenticated timed reads and real CSV download.
- `src/features/insights/InsightsCharts.tsx` — bar chart and live SVG donut.
- `src/features/insights/InsightsSections.tsx` — summary/trends/sources/goals/budgets/AI and page states.
- `src/features/insights/InsightsDialogs.tsx` — date menu, native custom inputs, category list, export preview/action.
- `src/styles/insights.css` — scoped desktop layout, chart/dialog states, animation/reduced motion.
- `backend/app/finance/insights.py` — read model, shared financial evaluation and two GET endpoints.
- `backend/app/finance/csv_safety.py` — shared user-text formula injection safety helper.
- `public/assets/insights/{up,budget,wallet,home,bag,ai-sparkle}.svg` and `provenance.json`.

## Modified existing source

- `src/app/App.tsx` — real `/insights/*` route instead of placeholder.
- `src/components/layout/ApplicationHeader.tsx` — Insights subtitle only.
- `src/components/ui/Icon.tsx` — `insights` asset collection.
- `backend/app/main.py` — register Insights router with existing DB/auth/environment dependencies.
- `backend/app/finance/service.py` — shared `last_3_months` range resolution.
- `backend/app/finance/transactions.py` — reuse CSV text-safety helper; normalize blank imported expense categories to Other for drill-down reconciliation.

## Tests

- Added `src/features/insights/format.test.ts` — range/scale/comparison/format validations.
- Added `src/features/insights/InsightsCharts.test.tsx` — tooltip, privacy/aria, category access.
- Added `backend/tests/test_insights.py` — auth/isolation/reconciliation/transfers/fees/dates/budgets/CSV/production boundaries.
- Added `tests/insights.spec.ts` — real full-stack interactions, downloads, error/loading/empty states and four desktop sizes with both sidebar states.
- Updated only the default timestamp in `backend/tests/test_transactions.py`'s shared test helper from current-day noon to midnight. Noon was a future ledger event during early-morning runs and caused six existing balance/stale-review tests to fail; runtime ledger behavior was not changed.

- Updated `tests/sidebar.spec.ts`'s UI-only fake-session fixture to return an explicit unavailable response for Insights, rather than accidentally call the real authenticated endpoint with no cookie and trigger session refresh. Real Insights browser scenarios do not mock successful API data.

## Documentation and evidence

- Added this file and `docs/INSIGHTS.md`.
- Updated `README.md`, `CLAUDE.md`, `docs/DESIGN_SYSTEM.md`, `docs/ASSETS.md`, `docs/IMPLEMENTATION_STATUS.md`.
- Added original/read-only Figma references and implementation screenshots under `docs/insights-qa/` plus final verification JSON and actual command logs in its `logs/` subfolder.

No schema migration, new credentials, runtime dependency change, replacement sidebar, duplicated ledger, bank connection or AI model integration.
