# Transactions delivery — exact file inventory

Compared by SHA-256 with the prior `FINCEPT-AI-Authentication-Overview.zip`, not the older sidebar-only package. Runtime dependencies, build outputs, private environments, databases and caches are excluded. This inventory file is itself new. Regenerated earlier QA captures are listed when their bytes changed.

## Added (42)

- `backend/app/finance/transactions.py`
- `backend/tests/test_transactions.py`
- `docs/TRANSACTIONS.md`
- `docs/transactions-qa/1024-expanded-modal.png`
- `docs/transactions-qa/1024-expanded.png`
- `docs/transactions-qa/1024-minimized-modal.png`
- `docs/transactions-qa/1024-minimized.png`
- `docs/transactions-qa/1280-expanded-modal.png`
- `docs/transactions-qa/1280-expanded.png`
- `docs/transactions-qa/1280-minimized-modal.png`
- `docs/transactions-qa/1280-minimized.png`
- `docs/transactions-qa/1366-expanded-modal.png`
- `docs/transactions-qa/1366-expanded.png`
- `docs/transactions-qa/1366-minimized-modal.png`
- `docs/transactions-qa/1366-minimized.png`
- `docs/transactions-qa/1440-expanded-modal.png`
- `docs/transactions-qa/1440-expanded.png`
- `docs/transactions-qa/1440-minimized-modal.png`
- `docs/transactions-qa/1440-minimized.png`
- `docs/transactions-qa/figma-add.png`
- `docs/transactions-qa/figma-desktop.png`
- `docs/transactions-qa/verification.txt`
- `public/assets/transactions/backspace.svg`
- `public/assets/transactions/calculator.svg`
- `public/assets/transactions/cart.svg`
- `public/assets/transactions/clock.svg`
- `public/assets/transactions/download.svg`
- `public/assets/transactions/list.svg`
- `public/assets/transactions/more.svg`
- `public/assets/transactions/provenance.json`
- `public/assets/transactions/sort.svg`
- `public/assets/transactions/swap.svg`
- `public/assets/transactions/transfer.svg`
- `src/features/transactions/TransactionForm.tsx`
- `src/features/transactions/TransactionTools.tsx`
- `src/features/transactions/Transactions.tsx`
- `src/features/transactions/api.ts`
- `src/features/transactions/calculator.test.ts`
- `src/features/transactions/calculator.ts`
- `src/features/transactions/types.ts`
- `src/styles/transactions.css`
- `tests/transactions.spec.ts`

## Modified (23)

- `CLAUDE.md`
- `README.md`
- `START_HERE.md`
- `backend/app/finance/schema.py`
- `backend/app/main.py`
- `docs/ARCHITECTURE.md`
- `docs/ASSETS.md`
- `docs/COMBINED_PROJECT.md`
- `docs/DESIGN_SYSTEM.md`
- `docs/IMPLEMENTATION_STATUS.md`
- `docs/OVERVIEW.md`
- `docs/overview-qa/1280-minimized.png`
- `docs/rendered-sign-in-loading.png`
- `docs/rendered-sign-up-validation.png`
- `src/app/App.tsx`
- `src/components/layout/ApplicationHeader.tsx`
- `src/components/ui/Dialog.tsx`
- `src/components/ui/Icon.tsx`
- `src/features/overview/Overview.tsx`
- `src/features/overview/OverviewCards.tsx`
- `src/features/overview/RecentTransactions.tsx`
- `tests/overview.spec.ts`
- `tests/sidebar.spec.ts`

## Removed

None.

## Preservation

Authentication feature source, authentication styling and original auth SVGs are preserved. The shared main application routes, Dialog/Icon/header and Overview action links are the targeted integration changes. Canonical financial table columns and IDs are retained; metadata schema v3 extends them. See TRANSACTIONS.md and IMPLEMENTATION_STATUS.md for implementation and verification.
