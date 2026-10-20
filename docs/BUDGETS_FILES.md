# Budgets — exact change inventory

SHA-256 comparison against FINCEPT-AI-With-Wallets.zip. Complete existing project, not a new frontend or patch. No files removed; no new dependency or stack. Excludes private environment/database files, installed dependencies, build output and caches.

## Added

- `backend/app/finance/budget_service.py`
- `backend/app/finance/budgets.py`
- `backend/tests/test_budgets.py`
- `docs/BUDGETS.md`
- `docs/budgets-qa/assets.json`
- `docs/budgets-qa/budget-details-1440.png`
- `docs/budgets-qa/budgets-1024-expanded.png`
- `docs/budgets-qa/budgets-1024-minimized.png`
- `docs/budgets-qa/budgets-1280-expanded.png`
- `docs/budgets-qa/budgets-1280-minimized.png`
- `docs/budgets-qa/budgets-1366-expanded.png`
- `docs/budgets-qa/budgets-1366-minimized.png`
- `docs/budgets-qa/budgets-1440-expanded.png`
- `docs/budgets-qa/budgets-1440-minimized.png`
- `docs/budgets-qa/create-budget-1440.png`
- `docs/budgets-qa/create-geometry.json`
- `docs/budgets-qa/figma-create.png`
- `docs/budgets-qa/figma-desktop.png`
- `docs/budgets-qa/figma-details.png`
- `docs/budgets-qa/verification.json`
- `public/assets/budgets/bag.svg`
- `public/assets/budgets/budget.svg`
- `public/assets/budgets/car.svg`
- `public/assets/budgets/film.svg`
- `public/assets/budgets/food.svg`
- `public/assets/budgets/health.svg`
- `public/assets/budgets/home.svg`
- `public/assets/budgets/plus.svg`
- `public/assets/budgets/search.svg`
- `public/assets/budgets/up.svg`
- `public/assets/budgets/wallet.svg`
- `src/features/budgets/BudgetComponents.tsx`
- `src/features/budgets/Budgets.tsx`
- `src/features/budgets/api.ts`
- `src/features/budgets/budgets.test.ts`
- `src/styles/budgets.css`
- `tests/budgets.spec.ts`
- `docs/BUDGETS_FILES.md` (this inventory)

## Modified

- `CLAUDE.md`
- `README.md`
- `START_HERE.md`
- `backend/app/finance/schema.py`
- `backend/app/finance/service.py`
- `backend/app/main.py`
- `backend/tests/test_transactions.py`
- `docs/ARCHITECTURE.md`
- `docs/ASSETS.md`
- `docs/IMPLEMENTATION_STATUS.md`
- `src/app/App.tsx`
- `src/components/layout/ApplicationHeader.tsx`
- `src/components/ui/Icon.tsx`
- `src/features/overview/OverviewCards.tsx`
- `src/features/transactions/Transactions.tsx`
- `src/features/wallets/WalletForms.tsx`
- `tests/sidebar.spec.ts`
- `tests/ui-corrections.spec.ts`

## Integration boundaries

- Frontend: Budgets.tsx, BudgetComponents.tsx, api.ts, budget styles and helper tests. Existing route/header/Icon register the feature and original assets. WalletForms exports the existing command guard and makes Field associate labels with buttons. OverviewCards changes only obsolete empty-state wording; Transactions accepts a validated kind query parameter for existing history navigation. No previous page redesign.
- Backend: budgets.py routes, budget_service.py shared integer allocation, schema v6 metadata, main router registration and Overview service adaptation. Canonical budgets/transactions/wallet models remain intact. No wallet balance changes.
- Tests: budget unit/backend/browser coverage, narrow schema version expectations and explicitly test-only fixtures. Production auth and rate limiting are unchanged.
- Preserved byte-for-byte: authentication source/assets; all original font assets; shared AuthenticatedLayout, Sidebar, ApplicationPreferences, Dialog; existing shared/Overview/Transactions/Wallets styles and dependency manifests. Prior QA PNGs restored after regression tests.
- See BUDGETS.md for exact endpoint, allocation, risk and period contracts; IMPLEMENTATION_STATUS.md and budgets-qa/verification.json for executed checks and limitations. Source Figma was read-only.
