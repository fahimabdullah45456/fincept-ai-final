# Overview correction — exact delivery file manifest

Compared with the previously shipped Authentication + sidebar combined ZIP. No manual merge is required.

## New source, assets and documentation

- `backend/app/finance/__init__.py`
- `backend/app/finance/demo.py`
- `backend/app/finance/routes.py`
- `backend/app/finance/schema.py`
- `backend/app/finance/service.py`
- `backend/tests/test_overview.py`
- `docs/OVERVIEW.md`
- `docs/OVERVIEW_FILES.md`
- `docs/SIDEBAR_FILES_CHANGED.md`
- `docs/overview-qa/TEST_RESULTS.md`
- `public/assets/overview/ai.svg`
- `public/assets/overview/bell.svg`
- `public/assets/overview/calendar.svg`
- `public/assets/overview/chevron.svg`
- `public/assets/overview/edit.svg`
- `public/assets/overview/entertainment.svg`
- `public/assets/overview/expense.svg`
- `public/assets/overview/food.svg`
- `public/assets/overview/home.svg`
- `public/assets/overview/income.svg`
- `public/assets/overview/left.svg`
- `public/assets/overview/percent.svg`
- `public/assets/overview/plus.svg`
- `public/assets/overview/privacy-hidden.svg`
- `public/assets/overview/privacy-visible.svg`
- `public/assets/overview/provenance.json`
- `public/assets/overview/right.svg`
- `public/assets/overview/search.svg`
- `public/assets/overview/shopping.svg`
- `public/assets/overview/transport.svg`
- `public/assets/overview/trash.svg`
- `public/assets/overview/view.svg`
- `public/assets/overview/wallet.svg`
- `public/assets/overview/work.svg`
- `src/components/layout/ApplicationHeader.tsx`
- `src/components/layout/ApplicationPreferences.tsx`
- `src/components/ui/Dialog.tsx`
- `src/components/ui/Icon.tsx`
- `src/features/overview/Overview.tsx`
- `src/features/overview/OverviewCards.test.tsx`
- `src/features/overview/OverviewCards.tsx`
- `src/features/overview/RecentTransactions.tsx`
- `src/features/overview/services/overviewApi.ts`
- `src/features/overview/types.ts`
- `src/features/overview/useOverviewResource.ts`
- `src/styles/overview.css`
- `tests/fixtures/overview-empty.json`
- `tests/overview.spec.ts`

## Modified existing source and documents

- `CLAUDE.md`
- `README.md`
- `START_HERE.md`
- `backend/app/main.py`
- `docs/ARCHITECTURE.md`
- `docs/ASSETS.md`
- `docs/COMBINED_PROJECT.md`
- `docs/DESIGN_SYSTEM.md`
- `docs/IMPLEMENTATION_STATUS.md`
- `src/app/App.tsx`
- `src/components/layout/AuthenticatedLayout.test.tsx`
- `src/components/layout/AuthenticatedLayout.tsx`
- `src/components/layout/SegmentPlaceholder.tsx`
- `tests/sidebar.spec.ts`

## Visual evidence

- `docs/overview-qa/1024-expanded.png`
- `docs/overview-qa/1024-minimized.png`
- `docs/overview-qa/1280-expanded.png`
- `docs/overview-qa/1280-minimized.png`
- `docs/overview-qa/1366-expanded.png`
- `docs/overview-qa/1366-minimized.png`
- `docs/overview-qa/1440-expanded.png`
- `docs/overview-qa/1440-minimized.png`
- `docs/reference-overview.png`
- `docs/rendered-protected-landing.png`
- `docs/rendered-sign-in-loading.png`
- `docs/rendered-sign-up-validation.png`
- `docs/sidebar-qa/1024-expanded.png`
- `docs/sidebar-qa/1024-minimized.png`
- `docs/sidebar-qa/1280-expanded.png`
- `docs/sidebar-qa/1280-minimized.png`
- `docs/sidebar-qa/1366-expanded.png`
- `docs/sidebar-qa/1366-minimized.png`
- `docs/sidebar-qa/1440-expanded.png`
- `docs/sidebar-qa/1440-minimized.png`

Authentication forms/provider/validation/service/asset source remain preserved. App.tsx gains the real Overview route and Open Overview confirmation link. Backend main.py gains additive finance schema initialization and router registration; no financial CRUD feature is pretended complete. See OVERVIEW.md for current scope and IMPLEMENTATION_STATUS.md for verified tests.
