# Wallets implementation

## Inspected Figma → React map
Read-only source page 2001:7025, desktop frame 2001:58232. Inspected node trees, text, fills, dimensions, exportable vectors and shared Balance Toggle master 65:110 (Visible/Hidden × Hover Off/On). Wallet cards/forms are editable frame compositions, not separate published masters. Manrope; original summary 310×152 radius20 and wallet cards ~420×248 radius20; existing global tokens retained.

- Shared AuthenticatedLayout/Sidebar/ApplicationHeader/ApplicationPreferences stay authoritative.
- Summary Cards 58349 → WalletSummaries; My Wallets 58399 → Wallets/WalletCard and toolbar, responsive desktop grid/list.
- Add New Wallet 58983 / Edit59906 → WalletForm.
- Add Money64662, External64695, Adjustment64728 → MoneyDialog.
- Transfer64787 + confirmation64853 → TransferDialog, existing transaction commands.
- Details65347, Archive65302, Delete65332, Adjust64901 → wallet action dialogs.
- Handoff66834 inspected: explicit money classification, idempotency, archive preservation, Savings separate, global privacy.

No Figma changes. Runtime UI is semantic React/text and local original SVGs; screenshots in wallets-qa are comparison evidence only.

## Data, migration and source of truth
The existing SQLite schema is extended **additively to v5** at application startup. Back up your database before upgrading. No extra environment variable, external financial service or migration command is required. Existing `wallets`, `wallet_metadata`, `transactions`, transaction metadata, idempotency receipts and owner/dataset keys remain authoritative. New `wallet_profiles` stores provider, optional **last four digits only**, notes, active/inactive status and optimistic metadata version. New `wallet_events` stores signed minor-unit external-fund/adjustment events with owner, dataset, wallet, reason, source and timestamps. It does not duplicate income/expense/transfer transactions.

`backend/app/finance/ledger.py` is shared by Wallets, Overview balances and transaction balance guards. Balance at a point = opening balance + canonical income − expenses − outgoing transfer principal + incoming principal + signed wallet events up to that point. Future-dated entries do not inflate today's available balance. Existing historical/future overdraft validation is retained; a legacy deficit cannot be worsened. All stored money is integer minor units; the UI parses amounts with the existing exact calculator, not floating-point arithmetic. BDT is the supported currency; no FX, bank login or live bank synchronization is implied.

### Summaries and ordering
Only active, non-archived wallets contribute to active funds and counts. Bank, Mobile Banking, Cash and Savings are mutually exclusive categories. Savings is included once in Total Funds and shown in the reconciliation footnote, not folded into Bank Accounts. Search/category/archive filters affect the collection, not the global active-funds summary. Custom order means stable saved creation order (not drag reordering); Highest Balance and Name A–Z sort real records. Grid/list preference is the only new localStorage value (`fincept.wallets.view`). Financial data is never stored there.

## API contracts
All endpoints require the existing authenticated cookie session and owner/dataset isolation. Mutations require the existing CSRF header/origin checks and a request UUID. Commands execute inside SQLite `BEGIN IMMEDIATE`, with replay receipts and rollback. Wrong ownership returns 404 or an empty filtered collection; invalid input returns 422, stale/conflicting financial operations return 409. The existing application normalizes validation/server errors.

| Operation | Endpoint | Notes |
| --- | --- | --- |
| Collection + active summaries | `GET /api/wallets?dataset=live` | Owner's real wallets, including archived metadata |
| Details + recent audit activity | `GET /api/wallets/{id}` | Latest 50 canonical transactions and external/adjustment events |
| Create | `POST /api/transactions/wallets` | Reused and extended; name, kind, opening_minor, opening_date, provider, identifier_last4, notes, status, BDT |
| Metadata edit | `PATCH /api/wallets/{id}` | Version required; cannot directly edit balance |
| External funds / adjustment | `POST /api/wallets/{id}/events` | Version, classification, amount or corrected balance, date and reason |
| Archive / restore / safe unused delete | `POST /api/wallets/{id}/{archive\|restore\|delete}` | Version and idempotency key required |
| Income / internal transfer | `POST /api/transactions` | Existing transaction validation, ownership, atomic guards and receipts reused |
| Wallet transactions | `GET /api/transactions?wallet={id}&start=...&end=...` | Existing table/search/paging; both source and destination match a transfer |

`/wallets` is the real shared-shell route. `?archived=true` selects the archived collection. View Transactions links to the **existing** Transactions page with wallet/dataset/date parameters; wallet-scoped history can span the wallet's complete supported lifetime (1901–2100), while unscoped transaction date ranges retain the ten-year limit. No duplicate transaction system was added.

### Add Money and transfers
Add Money explicitly asks for accounting classification. **Income** creates an existing income transaction and affects cash-flow summaries. **Transfer From External Account** (default) records already-owned, previously untracked funds without inventing income; do not use it for funds already tracked in another FINCEPT wallet. **Balance Adjustment** records a separate correction, requires a reason and does not affect income/expenses. Adjust Balance asks for a corrected balance and checks the previously displayed balance to reject stale corrections. Opening balances are not income and are not counted twice.

Internal transfers reuse one canonical transfer record, validate two different active owned BDT wallets, enforce sufficient historical/current/future funds and atomically debit/credit. Principal never increases global income or expenses; overall funds stay unchanged. The review step shows both resulting balances and only reports success after the backend commits. Request replays return the original operation instead of duplicating it.

**Activity boundary:** external/adjustment events are persisted audit records visible in Wallet Details. They are deliberately not forged into the income/expense/transfer-only Transactions CRUD taxonomy or cash-flow counts. View Transactions shows canonical records; Wallet Details shows the combined recent activity (latest 50, not a complete paginated audit report).

### Lifecycle
Metadata edits preserve balances and use optimistic versions. Inactive wallets remain inspectable but are excluded from active funds/selectors. Archive preserves even funded wallets and all history, excludes them from active summaries and blocks new entries/financial edits involving them. Outstanding future entries must be resolved before archive. Restore preserves metadata/status/history. Delete is available only for an unused wallet with zero opening/current balance and no transaction/event history. Existing budgets/goals have no wallet foreign key; if future features introduce dependencies, the deletion guard must be extended. No cascading financial-history deletion is used.

## Components, accessibility and motion
`src/features/wallets/Wallets.tsx` contains the collection, summary/card/list/detail/lifecycle presentation; `WalletForms.tsx` contains reusable fields, amount inputs, wallet form, Add Money and reviewed transfers; `api.ts` contains types, request/error handling and pure collection selectors. `src/styles/wallets.css` follows inspected Figma measurements and existing tokens. Shared layout, sidebar, privacy, header, Dialog, Icon, DateTimePicker and existing transaction requests are reused. Original local SVG vectors are recorded in ASSETS.md.

Shared native Dialog already provides focus trapping, Escape/close handling and ~200ms entrance/exit. Pending financial requests prevent dismissal and duplicate submission. Existing button press/hover/focus behavior is retained; wallet cards use subtle border/shadow feedback, wallet menus fade/translate ~150ms, selected view states transition, and supported customizable native select popovers have scoped transitions. No animation library or artificial request delays. Reduced motion disables decorative movement. Toast styling follows original success notification 2001:62939. All monetary cards, footnotes, details, options, review values and entered amount fields use the **one global privacy state**, with password-style amount entry when hidden.

## Verification
See IMPLEMENTATION_STATUS.md for the final run and exact counts. Wallet tests exercise actual FastAPI/SQLite requests and browser workflows. Only loading/error UI tests inject deliberate failed responses; financial-success tests use the real backend. Browser Wallets fixtures clear **only test-database rate-limit counters before that spec** because the combined feature suites register many accounts from one IP. Production authentication limits are not changed. Repeated full runs should use a fresh `test-results/auth-e2e.sqlite3` after stopping test servers; never use a live database for tests.

Screenshots under `docs/wallets-qa` are reference/QA evidence, never runtime assets. Desktop adaptation is limited to 1440×900, 1366×768, 1280×800 and 1024×768, with both shared sidebar widths. Narrow desktop uses two summary/grid columns rather than clipping controls. No mobile redesign was undertaken. Browser antialiasing/native text-field differences may remain; pixel identity is not claimed.

## Existing external limitations
Manual BDT wallet tracking is complete within the local application. Production deployment/secret configuration, Google OAuth, password-reset email, legal content and real AI/notification integrations retain the existing application's documented boundaries. They are not wallet integrations and were not fabricated or expanded here. Other unfinished financial sections remain placeholders.
