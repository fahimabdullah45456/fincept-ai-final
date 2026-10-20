# Settings change inventory

## Changed existing files

- `CLAUDE.md`
- `README.md`
- `START_HERE.md`
- `backend/app/main.py`
- `backend/tests/test_budgets.py`
- `backend/tests/test_goals.py`
- `backend/tests/test_planner.py`
- `backend/tests/test_transactions.py`
- `docs/ARCHITECTURE.md`
- `docs/ASSETS.md`
- `docs/DESIGN_SYSTEM.md`
- `docs/IMPLEMENTATION_STATUS.md`
- `src/app/App.tsx`
- `src/components/layout/ApplicationHeader.tsx`
- `src/components/layout/ApplicationPreferences.tsx`
- `src/components/layout/AuthenticatedLayout.tsx`
- `src/components/ui/Dialog.tsx`
- `src/features/auth/AuthProvider.tsx`
- `src/features/insights/InsightsCharts.tsx`
- `src/features/overview/OverviewCards.tsx`
- `src/features/transactions/TransactionForm.tsx`
- `src/features/wallets/WalletForms.tsx`

## New source, tests and documentation

- `backend/app/settings/__init__.py`
- `backend/app/settings/routes.py`
- `backend/app/settings/schema.py`
- `backend/tests/test_settings.py`
- `docs/SETTINGS.md`
- `docs/SETTINGS_FILES.md`
- `src/features/settings/Settings.tsx`
- `src/features/settings/api.ts`
- `src/features/settings/components.tsx`
- `src/features/settings/settings.test.tsx`
- `src/styles/settings.css`
- `tests/settings.spec.ts`

## QA evidence

- `docs/settings-qa/`: forty screenshots, executed-check logs, npm audit reports, verification README and `verification.json`.

Original local assets, financial accounting models, authentication flows, package manifests and lockfile remain unchanged, except for documented shared integration hooks. Existing migration tests change only their startup schema-version expectation from 10 to 11. Unrelated regenerated pre-existing QA images were restored from the supplied archive.
