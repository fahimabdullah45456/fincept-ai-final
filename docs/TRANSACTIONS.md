# Transactions — implemented application feature

## Design and architecture

Read `CLAUDE.md` and `DESIGN_SYSTEM.md` before changing this feature. Figma is read-only source of truth: file `kpEbLoKLaLiUcB8Q6xxgRl`, canvas `2001:7024`, desktop `2001:7034`. Individual desktop, summary/filter/table, expense/income/transfer/withdraw/edit, details, advanced filters, category and confirmation frames were inspected through Figma MCP. Original component masters AmountInput, CalculatorKeypad, WalletSelector, CategorySelector, QuickAmountButtons, TransferFeeBreakdown, DateTimeSelector, ConfirmationDialog and Table informed the React translations. These are real DOM components, not imported executable Figma code or screen images. Figma was not modified.

`src/features/transactions` uses the existing React/TypeScript/plain-CSS application, persistent AuthenticatedLayout/Sidebar/ApplicationHeader, cookie authentication, global ApplicationPreferences/Money, native Dialog and original local SVGs. No dependency or stack replacement. `TransactionForm` is shared by add/edit; `TransactionTools` supplies filters, category management and minimal wallet setup. The wallet setup is necessary for an empty account to record its first transaction; a complete Wallets page is **not** implemented.

The existing read-only Overview now links to real Transactions actions. Explicit sample dataset context is carried through category, recent-record and add links; live and sample data never mix. Navigating back to Overview re-queries its canonical ledger. No authentication logic, backend provider configuration or unrelated feature design was replaced.

## Records, money and accounting

Canonical `wallets` and `transactions` rows remain unchanged (including existing IDs and legacy imports). Startup's additive schema v3 creates wallet metadata, transaction metadata (notes/version/timestamps/mode), custom categories and idempotency receipts. Existing schema initialization is reused; no external migration framework was introduced. Back up your SQLite database before upgrading. Idempotent initialization preserves v2 records and does not lower a newer schema version.

- Monetary requests/storage use bounded **integer minor units** in BDT. Amounts must be positive; fees/opening positions non-negative. Floats and booleans are rejected for integer amounts.
- Income credits its wallet; expense debits it. A transfer/withdrawal has **one principal row** with source/destination. It is excluded from income and expense aggregates. A fee is **one linked expense** under Fees & Charges. Parent create/edit/delete and fee changes commit or roll back together.
- Source/destination wallets must belong to the authenticated user and same dataset, be active and BDT; they must differ. Withdrawals require a cash destination. Records cannot predate wallet opening.
- Ledger validation checks affected wallets at the union of old/new event instants, including later/future debits. No new overdraft is allowed. Imported/sample pre-existing deficits may not be worsened; they are not silently erased or used to reject unrelated changes. This preserves the existing reconciled development dataset.
- Commands use SQLite `BEGIN IMMEDIATE`, foreign keys and rollback on failure. Edit locks the type and preserves ID/creation time, incrementing its version. Stale versions return 409. Deleting income/a received transfer is rejected if reversing it would overdraw a wallet.
- Create/edit/delete and wallet setup use persisted per-user idempotency keys plus a payload/operation fingerprint. Duplicate retries return the original result; changing the payload with a reused key returns 409. The UI retains the key for an unchanged failed/uncertain request and prevents duplicate submissions.
- Fee rows are visible expenses; row edit/delete redirects to the parent transfer, preventing orphan fee mutation.
- Custom categories are trimmed, case-insensitively unique per type, persisted and owner-scoped. Defaults/historical mappings are protected. Rename preserves transaction IDs and updates affected categories/expense budget mappings; removal requires same-type reassignment, never deletion of records.

## Date and filter model

Default period is the current calendar month; explicit date ranges are inclusive, local-date based, 1901–2100, at most ten years. Summary cards and type counts follow **date period only**. Search, kind, category, wallet (either side of a transfer), amount range and sorting are AND-combined for the table/export, not summary cards. This scope is stated in the UI. Amount range uses positive principal/expense magnitude in minor units. Search is literal, not SQL wildcard syntax, over title/description/notes. Sorting is date newest/oldest or numeric amount highest/lowest, with stable ID tie-breaks. Pagination follows filtering; controls reset it, and server clamps out-of-range pages after deletion. Page sizes: 10, 25, 50.

Previous comparisons use the prior calendar month for a full calendar-month range, otherwise the preceding equal-length range. Percentage comparison is unavailable (—) when previous income/expenses were zero; no fabricated trend. Total transaction counts include the one principal and any fee record, never a second transfer leg.

## API contracts

All routes require the existing authenticated cookie and scope records by user/dataset. Demo scope is rejected in production. Writes require `X-Fincept-Request: 1` and allowed Origin, extending existing CSRF checks/CORS to PATCH/DELETE. Errors use existing safe `{message, field_errors}` responses; request values/secrets are not echoed in validation errors.

| Method | Route | Behavior |
|---|---|---|
| GET | `/api/transactions` | Filtered paginated rows, date-scoped summary/counts |
| GET | `/api/transactions/options` | Owned wallets/current balances and default/historical/custom categories |
| GET | `/api/transactions/{id}` | Owned transaction, fee and metadata |
| POST | `/api/transactions` | Atomic create, positive integer amount |
| PATCH | `/api/transactions/{id}` | Version-checked same-type edit |
| DELETE | `/api/transactions/{id}` | Version-checked confirmed reversal |
| GET | `/api/transactions/export` | All filtered rows, not only visible page, bounded to 50,000 |
| POST | `/api/transactions/wallets` | Minimal first/additional wallet setup with explicit opening position |
| POST | `/api/transactions/categories` | Create custom category |
| PATCH | `/api/transactions/categories/{id}` | Rename custom category and reassign mappings |
| DELETE | `/api/transactions/categories/{id}` | Remove custom category with replacement |

Query keys: `dataset`, `start`, `end`, `search`, `kind`, `category`, `wallet`, `minimum`, `maximum`, `sort`, `page`, `limit`. API amount filters are integer minor units; UI accepts up to two decimal places. Existing `/api/overview/*` routes/models are reused, not duplicated. Sample opt-in remains the existing development-only Overview action; Transactions never auto-seeds or presents fixture amounts as live.

## Calculator and privacy

One reducer owns expression, evaluated amountMinor and status. Direct input, keypad and quick amounts share it. Enter evaluates only in the amount input. Pending expressions cannot submit. A bounded whitelist recursive-descent parser uses BigInt rational arithmetic, precedence, parentheses and postfix percentage (`operand / 100`), then decimal half-up rounding to two places. It never uses eval/Function. It rejects divide-by-zero, excessive nesting/precision, overflow, malformed expressions and arbitrary code. Focus formatting is a separate browser-text overlay over the unchanged editable raw value, avoiding destructive selection resets.

The global privacy preference masks known monetary amounts in cards, rows, details, fee breakdown, wallet options, quick amounts, filters, opening balance and amount/fee drafts. Per-entry reveal is explicit, local to that dialog, and does not change the global preference; closing removes consent. Masked drafts use password inputs, not financial localStorage. CSV has real unmasked amounts and requires explicit consent if privacy is on. Export uses proper CSV quoting, integer-decimal amount formatting, UTF-8 BOM and formula-prefix protection for untrusted cells. Success is reported only after a successful response and initiating the browser download, not as a claim that an OS save completed.

## Interaction and design differences

Shared authenticated buttons have 140–160ms hover/press/focus transitions; dialogs/backdrops open/close in 200ms with minimal movement, focus trapping/restoration and background scroll locking; drawers move 10px. Native select popovers progressively animate in browsers supporting `appearance: base-select`, retaining native keyboard behavior elsewhere. Reduced motion disables motion. Request actions execute immediately, without artificial latency. Search is debounced 150ms; aborted/outdated queries cannot overwrite current results. Failed saves retain values and show server errors; dirty add/edit closes require discard confirmation.

The implementation intentionally shows actual records/date periods instead of reproducing Figma's illustrative amounts, dates, wallet names, relative Today/Yesterday labels, trends or descriptions. An explicit sample banner and minimal wallet setup entry point are truthful additions. Imported categories remain available alongside Figma's expanded defaults. The existing separate title and description fields remain editable (one extra optional context input compared with the compact expense reference). Short desktop dialogs scroll internally while their footer stays accessible. Narrow desktop tables scroll **inside** the card; the document must not overflow. Font/OS date/time picker rendering and browser text antialiasing can differ from Figma; no pixel-identical claim.

Ask FINCEPT AI navigates to the existing AI Assistant integration boundary. **No LLM/chat service or notification backend is implemented by this task.** The rule-based Overview insight remains unchanged. Full Wallets/Budgets/Goals/other pages, Google OAuth, password recovery and final legal text remain outside scope.

## Run and verification

Use `START_HERE.md`. No new external service or secret is required. Start FastAPI and Vite; create/sign into an account, open Transactions, create a wallet and record a transaction. See IMPLEMENTATION_STATUS.md for final executed test counts, TRANSACTIONS_FILES.md for exact changes, and transactions-qa for original-reference and rendered desktop screenshots. Test databases, real credentials and private environment files are not shipped.

## Targeted calendar/category correction

The subsequent follow-up replaces Transactions native calendar popups with the original Figma DateTimeSelector, and inline category creation with the original centered Create custom category dialog (icon/color choices included). Presentation metadata schema v4 stores category appearance; canonical ledger rows/accounting are unchanged. Earlier statements above about native calendar rendering or schema v3 describe the first delivery. See CALENDAR_CATEGORY_CORRECTION.md for current behavior, implementation boundaries and source nodes.
