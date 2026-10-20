# Wallets — exact change inventory

SHA-256 comparison against the previously delivered FINCEPT-AI-Calendar-Category-Corrected.zip. One complete existing project; no files removed, no new stack or dependency. Excludes installed dependencies, private environment/database files, build output and caches.

## Added

- `backend/app/finance/ledger.py`
- `backend/app/finance/wallets.py`
- `backend/tests/test_wallets.py`
- `docs/WALLETS.md`
- `docs/wallets-qa/add-wallet-1440.png`
- `docs/wallets-qa/figma-add-wallet.png`
- `docs/wallets-qa/figma-desktop.png`
- `docs/wallets-qa/figma-list.png`
- `docs/wallets-qa/list-wallets-1440.png`
- `docs/wallets-qa/verification.json`
- `docs/wallets-qa/wallets-1024-expanded.png`
- `docs/wallets-qa/wallets-1024-minimized.png`
- `docs/wallets-qa/wallets-1280-expanded.png`
- `docs/wallets-qa/wallets-1280-minimized.png`
- `docs/wallets-qa/wallets-1366-expanded.png`
- `docs/wallets-qa/wallets-1366-minimized.png`
- `docs/wallets-qa/wallets-1440-expanded.png`
- `docs/wallets-qa/wallets-1440-minimized.png`
- `public/assets/wallets/bank.svg`
- `public/assets/wallets/cash.svg`
- `public/assets/wallets/dl.svg`
- `public/assets/wallets/grid.svg`
- `public/assets/wallets/info.svg`
- `public/assets/wallets/kebab.svg`
- `public/assets/wallets/list.svg`
- `public/assets/wallets/phone.svg`
- `public/assets/wallets/plus.svg`
- `public/assets/wallets/right.svg`
- `public/assets/wallets/sort.svg`
- `public/assets/wallets/swap.svg`
- `public/assets/wallets/target.svg`
- `public/assets/wallets/wallet.svg`
- `src/features/wallets/WalletForms.tsx`
- `src/features/wallets/Wallets.tsx`
- `src/features/wallets/api.ts`
- `src/features/wallets/wallets.test.ts`
- `src/styles/wallets.css`
- `tests/wallets.spec.ts`
- `docs/WALLETS_FILES.md` (this inventory)

## Modified

- `CLAUDE.md`
- `README.md`
- `START_HERE.md`
- `backend/app/finance/schema.py`
- `backend/app/finance/service.py`
- `backend/app/finance/transactions.py`
- `backend/app/main.py`
- `backend/tests/test_transactions.py`
- `docs/ARCHITECTURE.md`
- `docs/ASSETS.md`
- `docs/IMPLEMENTATION_STATUS.md`
- `src/app/App.tsx`
- `src/components/layout/ApplicationHeader.tsx`
- `src/components/ui/Icon.tsx`
- `src/features/transactions/TransactionForm.tsx`
- `src/features/transactions/types.ts`
- `tests/sidebar.spec.ts`

## Integration boundaries and preservation

- New frontend feature: Wallets.tsx, WalletForms.tsx, api.ts, feature CSS and tests; 14 original Figma wallet SVGs.
- Shared frontend changes: register real Wallets route, Wallets header subtitle, extend Icon collection. Transactions wallet options exclude inactive accounts; Wallet type accepts status. No existing auth/Overview frontend or shared Sidebar/Preferences/Dialog source changes.
- Backend additions: shared integer timeline ledger.py and wallet_router in wallets.py; schema v5 wallet_profiles/wallet_events. Main adds the router, service.py reads shared balances, transactions.py extends existing wallet creation/active/archive guards and permits complete wallet-filtered history. No second transaction model or balance cache.
- Tests: wallet unit/backend/browser additions, migration version expectations and explicit sidebar-only wallet read fixture. Wallet browser fixture clears only isolated test-DB throttling counters; production auth protections remain intact.
- Preservation: 34 protected auth/Overview source, original auth/font assets, shared layout/sidebar/preferences/Dialog/style/dependency files checked byte-for-byte. Earlier unrelated QA PNGs restored after regression tests. Existing original Figma files were not changed.

See WALLETS.md for APIs, classification, transfer/archive semantics and limits; IMPLEMENTATION_STATUS.md and wallets-qa/verification.json record actual executed checks.
