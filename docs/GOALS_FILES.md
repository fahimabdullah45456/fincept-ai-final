# Financial Goals — exact change inventory

SHA-256 comparison against FINCEPT-AI-With-Budgets.zip. Complete existing project, not a new frontend or patch. No files removed or dependencies added. Private environment/database files, installed dependencies, generated build output and caches are excluded.

## Added

- `backend/app/finance/goal_service.py`
- `backend/app/finance/goals.py`
- `backend/tests/test_goals.py`
- `docs/GOALS.md`
- `docs/goals-qa/assets.json`
- `docs/goals-qa/create-1440.png`
- `docs/goals-qa/design-map.txt`
- `docs/goals-qa/details-1440.png`
- `docs/goals-qa/figma-add-savings.png`
- `docs/goals-qa/figma-create.png`
- `docs/goals-qa/figma-desktop.png`
- `docs/goals-qa/figma-inspection.json`
- `docs/goals-qa/goals-1024-expanded.png`
- `docs/goals-qa/goals-1024-minimized.png`
- `docs/goals-qa/goals-1280-expanded.png`
- `docs/goals-qa/goals-1280-minimized.png`
- `docs/goals-qa/goals-1366-expanded.png`
- `docs/goals-qa/goals-1366-minimized.png`
- `docs/goals-qa/goals-1440-expanded.png`
- `docs/goals-qa/goals-1440-minimized.png`
- `docs/goals-qa/review-1440.png`
- `docs/goals-qa/savings-1440.png`
- `docs/goals-qa/verification.json`
- `public/assets/goals/laptop.svg`
- `public/assets/goals/phone.svg`
- `public/assets/goals/plus.svg`
- `public/assets/goals/search.svg`
- `public/assets/goals/shield.svg`
- `public/assets/goals/target.svg`
- `public/assets/goals/travel.svg`
- `public/assets/goals/up.svg`
- `public/assets/goals/wallet.svg`
- `src/features/goals/GoalComponents.tsx`
- `src/features/goals/Goals.tsx`
- `src/features/goals/api.ts`
- `src/features/goals/goals.test.ts`
- `src/styles/goals.css`
- `tests/goals.spec.ts`
- `docs/GOALS_FILES.md` (this inventory)

## Modified

- `CLAUDE.md`
- `README.md`
- `START_HERE.md`
- `backend/app/finance/schema.py`
- `backend/app/finance/service.py`
- `backend/app/finance/wallets.py`
- `backend/app/main.py`
- `backend/tests/test_budgets.py`
- `backend/tests/test_transactions.py`
- `docs/ARCHITECTURE.md`
- `docs/ASSETS.md`
- `docs/IMPLEMENTATION_STATUS.md`
- `src/app/App.tsx`
- `src/components/layout/ApplicationHeader.tsx`
- `src/components/ui/Icon.tsx`
- `tests/sidebar.spec.ts`

## Integration boundaries

- Frontend: Goals.tsx, GoalComponents.tsx, api.ts, helper tests and scoped goals.css. Existing route/header/Icon register the feature. Original nine SVG assets are local; current shared Dialog/Field/AmountInput/useCommand/ChoiceDialog/calendar are reused without modification.
- Backend: goals.py exposes owner-scoped commands and queries; goal_service.py supplies shared metrics/availability; additive schema v7 extends canonical financial_goals. main registers the router, Overview service reuses the same read model. Wallets receives only a guard preventing deletion of audit-linked wallets.
- Tests: Goals helper/backend/browser coverage; narrow schema version expectations in prior transaction/budget tests; explicit UI-only sidebar fixture. No authentication, cookie, CSRF or production rate-limit change.
- Preserved byte-for-byte: all baseline files outside the listed modifications, including authentication source/assets, previous feature styles, shared AuthenticatedLayout, Sidebar, ApplicationPreferences, Dialog, existing calendar, shared wallet/budget forms, fonts and dependency manifests. Prior QA PNGs restored after full regression.
- See GOALS.md for accounting/API/migration/legacy/shortfall contracts and goals-qa/verification.json for actual checks. Original Figma inspection was read-only; reference PNGs are not runtime UI.
