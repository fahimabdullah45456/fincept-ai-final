# Budgets — implementation and accounting contract

## Design and integration

Read-only Figma source: file `kpEbLoKLaLiUcB8Q6xxgRl`, page `2001:7026`, desktop `2001:71662` (1440×1340). The actual Create/Edit/Delete, filter, status, sorting, reset-period, threshold, action and category-detail frames were inspected, along with the implementation handoff `2001:75114`. No Figma nodes were created or changed.

The new `/budgets/*` React route reuses AuthenticatedLayout, Sidebar, ApplicationHeader, ApplicationPreferences/Money, Icon, native Dialog, the corrected DateTimePicker, and Field/AmountInput/guarded useCommand from WalletForms. Those generic form exports are reused, not a second wallet or transaction management system. Overview's budget widget retains its existing presentation; its read-side calculations now use the same budget service. The only Transactions integration is an optional validated `kind` query parameter for budget-history deep links.

Verified existing global tokens remain authoritative: `--brand` #F9733B, `--bg` #F7F7F4, `--border` #E9E8E3, `--secondary` #777873, local Manrope and the existing Taka glyph fallback. Budget-specific green/amber/status treatments follow the inspected frame. The original 11 exported budget SVGs are local. Screenshots in budgets-qa are QA references only, never runtime backgrounds.

## Persistent model and migration

The canonical `budgets` table is reused unchanged: id, user_id, dataset, name, category, limit_minor, start_date, end_date. Categories remain the existing owned/default expense-category strings; there is no new category taxonomy or guessed synonym mapping.

Schema **v6** adds only `budget_metadata`, keyed by the existing budget ID with cascading metadata cleanup:
- reset_period: weekly/monthly/custom;
- alert_threshold: 50/75/90/100, nullable for Off; legacy rows default to 75%;
- notes, optimistic version, created_at and updated_at.

Initialization uses the project's existing additive `finance/schema.py` migration tooling on backend startup. Canonical positional inserts and historical ledger rows remain compatible. Legacy budgets without metadata are treated as explicit Custom periods, version 1. Zero legacy limits remain readable, although new/edited limits must be positive. Back up your SQLite DB before upgrading; keep private environment files and the database out of source packages. No new environment variables or external services are required.

## API (all authenticated and owner/dataset scoped)

| Method | Path | Behavior |
|---|---|---|
| GET | `/api/budgets` | Saved budgets overlapping `month=YYYY-MM`; search, category, status and sort filters; period-wide summaries and alerts |
| GET | `/api/budgets/options` | Accessible existing expense categories, including owned historical mappings |
| POST | `/api/budgets` | Create canonical budget and metadata atomically |
| GET | `/api/budgets/{id}` | Owned budget metrics and eligible expense history, `month`, `page`, `limit` (1–50) |
| PATCH | `/api/budgets/{id}` | Validate/version-check, persist supported fields and increment version |
| DELETE | `/api/budgets/{id}` | Explicit UI confirmation; delete only plan/metadata, preserve transactions |

`dataset=live` is default; development demo remains isolated and is rejected in production. New budgets do not populate accounts with fictitious records. Existing demo workspaces can be inspected explicitly through `?dataset=demo`.

Create/update payload: `request_key`, `name`, `category`, integer `limit_minor`, ISO `start_date`/`end_date`, `reset_period`, optional `alert_threshold`/`notes`; updates require the current `version`. Deletion requires `request_key` and `version`. Writes use the existing CSRF header/Origin protection, BEGIN IMMEDIATE, rollback, persisted request fingerprints and receipts. Stable request keys make retrying a timed-out command safe; changed payloads receive a new key. Stale versions and overlapping periods return 409; invalid input returns 422; inaccessible IDs return 404; unauthenticated access returns 401.

Listing `status`: empty, On Track, Near Limit, Exceeded. `sort`: highest (spending descending; deterministic name/ID tie-breakers) or name (A–Z). Search covers name/category/notes. Summaries and alerts cover **all applicable budgets in the selected month**, regardless of card search/filter; counts show total and matching records. No fake prior-period trends exist.

## Allocation and financial invariants

`budget_service.evaluate` is the shared source for both Budgets and Overview:
1. Select this user's budgets overlapping the reporting dates.
2. Select this user's categorized canonical **expense** transactions inside the reporting dates.
3. Match the **exact saved category string** and the individual budget's inclusive start/end dates.
4. Assign an expense only when exactly one applicable budget qualifies.
5. Sum integer minor units; remaining = limit − spent. No wallet balances are changed.

Income, internal transfer principal, wallet opening funds, external transfers and wallet adjustment events do not count as spending. A separately recorded transfer fee is an expense and qualifies only if its actual category matches. Unassigned/uncategorized expenses are not guessed into a budget. The current transaction model has no refund/reversal type or status; none is invented here. Deleting an expense already removes its contribution through the existing transaction system.

New/updated same-category periods may not overlap (inclusive boundaries); writes serialize this check atomically. Existing imports or category reassignment may create ambiguous legacy overlap. In that case the affected expenses are **excluded from every conflicting budget**, not assigned arbitrarily or counted twice. The page reports the ambiguous count and affected cards/details flag the conflict. Correct category/date ranges to resolve it. Summaries, detail history and Overview remain consistent with that rule. Details' Manage category transactions link deliberately opens the existing Transactions page; it shows that category's records in the intersected dates, including any ambiguous records that need correction.

The full saved limit is included once for an applicable budget, while spending uses the intersection of its dates and the selected reporting period. Limits are **not prorated**. Overall spent is the sum of uniquely assigned expenses, not all household expenses. Summary remaining is not clamped. Raw utilization is spent / limit × 100 (rounded to two display decimals); only visual meter widths and aria-valuenow clamp to 0–100. aria-valuetext retains raw over-budget percentages. A zero limit has null percentage, never Infinity/NaN; positive spending against it is Exceeded.

## Status and risk (Figma handoff distinctions)

- On Track: utilization below 85%.
- Near Limit: 85% through exactly 100%.
- Exceeded: spending strictly above the limit.
- At risk / Budget Alerts: spending reaches that budget's configured threshold (default 75%), **or** it is exceeded. Off suppresses threshold alerts but never hides an exceeded plan.

Comparisons use integer cross-multiplication before display rounding. Thus the risk count intentionally differs from the Near Limit card count. Overview adapts the shared status names to its existing On track/Near limit/Over budget API labels and retains one-decimal presentation.

## Periods and honest limitations

Monthly saves start through the last day of its starting month; Weekly saves exactly seven inclusive days; Custom saves an explicit ordered range of up to 732 days. Dates must be within 1901–2100. The month selector browses saved periods; it never fabricates historical or future instances. The existing local-date transaction convention is preserved; the browser sends an explicit month and dates are not shifted through UTC.

There is **no automatic recurring-budget scheduler, rollover, historical snapshot freeze, push/email threshold notification or refund system** in the existing architecture. The reset-period field defines one persisted period, not an automatic renewal. This is stated in the form. Create a separate plan for another period. Budget Alerts are live on-page observations when data is loaded/refreshed, not notifications claimed to have been delivered. There is no new bank or AI service connection.

## Interaction and accessibility

Shared buttons retain their existing 150ms hover/press/focus treatment; native dialogs reuse the existing 200ms entry/exit animation, focus trap, Escape and restoration. Budget cards use 160ms border/shadow feedback, progress widths 220ms, and choices use the shared dialog pattern observed in Figma. No animation library or artificial network delay was added. Reduced motion disables relevant animation/transitions. Pending writes use the existing ref lock, disabled submit and immediate saving/error feedback; success is shown only after a confirmed response. Existing modal close guards prevent abandoning a pending command.

Global monetary privacy masks summary/card/detail/confirmation money and uses password-style amount entry when enabled. Percentages, counts, category names and dates remain visible. It changes presentation, not stored values or accounting. Dialogs scroll internally at shorter desktop heights and keep action footers reachable; no separate mobile redesign was introduced.

## Verification

See `budgets-qa/verification.json` and `IMPLEMENTATION_STATUS.md` for actual final command results, warnings, viewport captures, regressions and known unsupported capabilities. Tests cover backend persistence, version/idempotency/CSRF/ownership, boundary/zero/over-limit arithmetic, exact categories, transfers/income exclusion, ambiguity, concurrent overlap prevention, genuine v5 migration preservation and production demo rejection. Browser tests use real registration and SQLite writes for successful operations; only failure/loading tests and the explicitly UI-only sidebar fixture intercept responses.
