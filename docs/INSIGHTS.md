# Financial Insights & Analytics

## Integration and design

`/insights/*` is a real authenticated page in the existing React/FastAPI/SQLite project. It reuses the persistent application shell, sidebar active state, header, global privacy preference, `Money`, `Icon`, and the native modal `Dialog`. No parallel financial records or new database migration are introduced.

The read-only Figma source is file `kpEbLoKLaLiUcB8Q6xxgRl`, Insights page `2001:7028`. Inspected desktop/state references are retained in `insights-qa/figma-*.png`. Shared typography is local Manrope; cards use the original 20px radius, #E9E8E3 borders, #F9733B primary, peach income, muted #777873 and green/amber/red financial statuses. Runtime charts are live HTML/SVG, never screenshot substitutions. Original six 18×18 vectors are local under `public/assets/insights/` with validated provenance.

### Figma-to-code map

| Design section | Component |
|---|---|
| Heading, date selector, export action, page states | `Insights.tsx`, `DateRangeMenu`, `LoadingState`, `FailedState` |
| Four summary cards | `SummaryCards` |
| Income vs Expenses (2001:81316) | `IncomeExpenseChart`: grouped HTML bars, live axes, hover/focus tooltip |
| Where Your Money Goes (2001:81372) | `CategoryDonut`: live SVG ring + native category buttons |
| Spending Trends | `SpendingTrends`: calculated largest category, shopping, cash flow |
| Income Sources / Savings Progress | `IncomeSources`, `SavingsProgress` |
| Budget Performance | `BudgetPerformance` |
| AI unavailable | `AiInsights` (no simulated AI findings) |
| Custom dates, category details, CSV export | `InsightsDialogs.tsx` |

Wide desktop uses four summary cards, a 760:520 proportional primary chart split, three trend/budget cards and a two-column secondary section. Scoped container rules stack primary charts below 1180px of available content and secondary sections below 900px. These preserve desktop usability with the existing 76px/252px sidebar; no mobile-specific redesign is introduced.

## Data and accounting

All financial calculations are server-side integer **minor units (paisa)**. The frontend converts to BDT only for presentation. Only canonical `income` and `expense` transactions count. Internal transfer principal is excluded; a transfer fee already stored as an expense counts exactly once. Wallet opening balances, external wallet events, adjustments and goal allocations are not new income or expenses.

The same owned, dataset-scoped transaction ledger powers Overview and Transactions. Insights adds a read model, not duplicated mutable totals. Summary totals reconcile with categories and sources. Category/source shares are independently rounded to one decimal; their displayed sum may differ slightly from 100%. Largest category is calculated from real expense groups; Shopping uses the exact case-insensitive saved name. No previous income/expense means no invented percentage comparison. A zero income produces an unavailable savings rate; expenses can legitimately produce negative net cash flow or a negative savings rate when income is nonzero.

Income sources are grouped by the transaction's saved **income category**. Existing demo records use the category `Income`; they are not relabeled as fictitious Salary/Freelance sources to match the illustrative design. Likewise, real demo housing, goal, budget, trend and comparison values supersede Figma's independent sample snapshots.

### Goals and budgets have distinct scopes

- Savings Progress uses `goal_service.goals/summary`, active goals only, explicitly dated **current snapshot**, not a selected-period inflow or an additional asset.
- Budgets use shared `budget_service.evaluate` for plans overlapping the selected range. Spending uses the intersection of the report range and each plan's saved dates. The full saved limit is included once and is **not prorated**. Scope copy explicitly says selected-range spending versus full limits.
- Budget status follows the existing shared evaluator (Near Limit 85%–100%; Exceeded strictly above 100%). Ambiguous legacy category overlaps are excluded and flagged, not double-counted. The first three saved plans are displayed with a count/link when more exist.
- Goal snapshots and budget metrics are excluded from the CSV because it is a transaction-analytics report.

## Endpoints

| Method | Path | Contract |
|---|---|---|
| GET | `/api/insights` | Authenticated summary, buckets, categories, sources, trends, dated savings, budget metrics, explicit AI-unavailable state |
| GET | `/api/insights/export` | Same filters, real server-generated UTF-8 BOM CSV attachment; `masked=true` masks monetary columns |
| GET | `/api/transactions` | Existing category detail list, `kind=expense`, exact `category` (blank/null imported expense categories join Other), inclusive `start/end`, oldest first, first 50 matching records |

Common query: `period=this_month|last_month|last_3_months|this_year|custom`, `dataset=live|demo`, and `start/end=YYYY-MM-DD` for custom. Invalid period/date/range returns 422. Reads/exports require a valid authenticated session and owner-scoped SQL; production rejects demo data. Shared middleware sets `Cache-Control: no-store`. The page refreshes authentication on 401; failed reads/exports have actionable messages without successful-looking toasts.

## Date semantics

- **This Month / Last Month:** complete calendar month, inclusive first/last day.
- **Last 3 Months:** current calendar month and its preceding two months, through the current month's last day.
- **This Year:** January 1–December 31 of the server's current year. Recorded future-dated transactions inside a selected period remain recorded analytics; this is not a cash-balance-as-of-now query.
- **Custom Range:** both valid dates, ordered, years 1901–2100, at most 732 inclusive days. Frontend and backend enforce the same bounds. Invalid deep-link dates display a failure state; changing the range recovers.
- A full calendar month shows up to six context months with only the selected month highlighted. Other ranges use monthly buckets, or quarterly buckets beyond 12 months. Partial edge buckets respect the exact dates. Leading periods with no records are omitted and disclosed when relevant; unrecorded future months in This Year are not a fabricated trend.
- Date comparisons use stored calendar-date substrings, consistent with Transactions/Overview, not a new timezone conversion policy. The server's local date resolves presets. Preset/custom/dataset selections persist in the URL and survive refresh.

## Interactions, accessibility and privacy

Date dropdown: native button/menu radio options, Arrow Up/Down, Home/End, Escape, close on focus leaving the control, outside dismissal and focus return. Custom dates use actual browser-native date inputs. Dialogs reuse native `showModal`, focus trap/return, Escape and 200ms exit. Category list buttons are keyboard accessible and open real category/range-filtered transactions. View Transactions preserves dataset, category, expense kind and inclusive dates through the existing route.

Chart groups provide hover/focus tooltips, Arrow Left/Right navigation, Escape and textual accessible labels. Donut categories have matching accessible native list buttons. Zero/empty/no-income/no-budget/no-goal/unavailable-AI/loading/network-failure states are explicit. On range changes, old data is dimmed and inert until the current response resolves; aborted/stale responses cannot replace newer data.

Global privacy masks monetary summaries, cards, axes, tooltips, category rows/details, accessible labels and export preview immediately. Insights also hides percentage text and comparison copy in its own UI. Shared `Money` uses `••••`, rather than Figma's `৳ ****`; the existing app convention is preserved. Privacy is display protection, not permission filtering: authorized amounts remain in API responses. Export privacy uses `****` for every monetary CSV column; percentages, counts and dates remain available and are disclosed as monetary-column masking.

Buttons hover/press in 160ms and press scale .98; dropdowns 150ms; dialogs enter/exit 200ms; chart interactions 160ms. `prefers-reduced-motion` disables animations, transitions and press transforms. Layout/financial state remains unchanged.

## CSV export

Export opens a preview; Prepare Report performs a real authenticated download using the exact selected period/dataset. A success toast appears only after a nonempty CSV blob has been received and handed to the browser for download; it is not a claim that the OS persisted the file. The filename contains inclusive start/end dates. Failure leaves the dialog open with retryable text and no success toast. Busy state blocks duplicate submission/early dismissal.

CSV includes period/start/end/generation timestamp/dataset/privacy metadata, summaries, valid comparisons, context/range chart buckets with explicit selected-range/context-only markers, expense categories, income sources and accounting notes. Python `csv.writer` escapes commas, quotes and embedded newlines. `csv_safe` neutralizes leading spreadsheet-formula markers in user-controlled text (including whitespace-prefix variants); numeric negative amounts stay numeric. Monetary precision is two decimal places, derived from integers. Transaction exports also reuse the safety helper.

## Verification and limits

See `IMPLEMENTATION_STATUS.md` and `insights-qa/verification.json` for actual run results, repeated-test handling, warnings, desktop evidence and exceptions. Successful browser data flows reach FastAPI/SQLite; only deliberate loading/failure cases intercept requests. No bank sync, AI provider, scheduled analysis, PDF export, production deployment or mobile layout is claimed. Existing OAuth/reset/notification and placeholder-page boundaries are unchanged. The report is BDT/manual-record analytics, not financial advice.
