# Financial Goals — implementation contract

Implemented inside the existing React/TypeScript/Vite + FastAPI/SQLite application. No new project, financial stack or dependency; no Figma writes. Read CLAUDE.md and DESIGN_SYSTEM.md before extending this feature.

## Design and reusable components

Read-only Figma file `kpEbLoKLaLiUcB8Q6xxgRl`, Financial Goals page `2001:7027`: desktop `2001:75706`, Create `2001:79265`, Details `2001:79595`, Add Savings `2001:79900`, Review `2001:80182`, delete/actions/status/category/sort/funding and handoff `2001:80375` were inspected before implementation. Supported read-only Figma node inspection/export, screenshots and variables were used. The optional design-context guidance resource was unavailable (zero resources), so no unsupported design-context call was used. Nine original SVG exports retain their geometry; provenance and SHA-256 are in goals-qa/assets.json. Reference PNGs are audit-only, never runtime UI backgrounds.

The existing AuthenticatedLayout, Sidebar, Header, ApplicationPreferences/Money, Dialog, Field, AmountInput, useCommand, DateTimePicker, ChoiceDialog and Icon are reused. The existing orange/off-white tokens, local Manrope, original vectors and scoped Goals styles preserve the design. Sidebar persistence, Settings placement and global privacy remain shared. Original source dimensions inform the desktop/card/dialog proportions; smaller desktops use contained scrollable native dialogs rather than clipped content. Controls are live semantic HTML, not screenshots. Browser font rendering is not claimed pixel-identical to Figma.

## Model and migration

Startup applies additive schema **v7**, retaining the canonical `financial_goals` table and its existing records. New `goal_metadata` stores category, description, optional monthly plan, icon, active/paused state, soft-archive flag, optimistic version and timestamps. New immutable `goal_contributions` stores owner/dataset, goal, optional wallet, integer amount, funding method, unique linked wallet event, recorded date, note and creation timestamp. Foreign keys preserve audit history. No parallel wallet balance table is introduced.

Back up your existing SQLite database and private environment before upgrading. Existing startup commands apply the migration automatically. No new service credentials or environment variables are needed. Source delivery is not production deployment.

Supported goal categories are Emergency Fund, Education, Travel, Electronics, Home, Vehicle and Other. They are goal-plan metadata, not a duplicate expense-category system. Icons can follow the category or use the original shield/laptop/travel/phone/target exports. New targets must be positive; legacy zero targets remain readable and safe. Target dates are optional; supported years 1901–2100. Monthly contribution targets are manual plans, never scheduled transfers.

## API (cookie-authenticated and owner/dataset scoped)

All routes use the existing request, validation/error, CSRF and database conventions. `dataset=live` is default. Explicit isolated development demo is supported; production rejects demo access. Monetary request fields are **integer minor units**, not floats.

| Method and route | Behavior |
|---|---|
| GET `/api/goals` | Saved plans; search, category, status, sort, scope; active-only summary |
| GET `/api/goals/options` | Supported categories/icons and live wallet balance/allocation/availability |
| GET `/api/goals/{id}` | Real details and paginated immutable contributions; deleted plans remain readable |
| POST `/api/goals` | Create a zero-saved plan |
| PATCH `/api/goals/{id}` | Versioned metadata/target update; never rewrites contributions |
| POST `/api/goals/{id}/state` | Confirmed pause/resume |
| DELETE `/api/goals/{id}` | Confirmed soft deletion; releases earmarks without deleting history |
| POST `/api/goals/{id}/contributions/preview` | Validate and return a meaningful review, **no financial write** |
| POST `/api/goals/{id}/contributions` | Atomic reviewed contribution with stable idempotency receipt |

List status: In Progress, Completed or Paused. Scope: all, active, completed, paused, archived (UI: Deleted Goals). Sorting: recent creation, target date, highest target, lowest progress. Search covers name, category and description. List summaries are active-only and independent of card filters/scope. Changing filters does not falsify the user's total. Existing `/api/overview/summary` reuses the same Goals read model; its existing widget shows the first three active plans. Wallets and Transactions retain their existing routes and accounting models.

## Financial source of truth

**Goals earmark existing funds; they are not new wallets or extra assets.** Managed saved amount is the sum of immutable contribution rows. Canonical `saved_minor` is kept synchronized for existing import compatibility, not used as a second independent managed total. Remaining = target minus saved; negative amounts are preserved when overfunded. Percentage = saved / positive target × 100, rounded to two decimal places; a legacy zero target returns null, never NaN/Infinity. Only the visual fill clamps to 0–100%. Milestones (25/50/75/100%) derive from that actual percentage.

Active summaries and Savings Journey sum **In Progress, non-deleted** goals only. Completed and paused plans are excluded from those totals, but their earmarks remain reserved until the plan is deleted. Completed is derived when a positive target is reached; completion does not create money or transfer funds. Editing the target can reopen a completed plan. Pausing/resuming persists the explicit state; contributions require In Progress. Manual completion/cancellation and automatic monthly transfers are not implemented or advertised.

Monthly plan display uses an explicit positive stored target first. Otherwise it rounds remaining minor units upward over inclusive remaining calendar months. A missing or past target date displays unavailable; a fully funded plan needs zero. This is a plan, not recurring payment execution. Creation starts saved=0 and the current saved field is read-only; starting savings require a recorded funding contribution.

### Allocate existing wallet funds

A contribution creates one linked allocation row. **Wallet balance, total funds, income and expenses stay unchanged.** Unallocated availability is canonical ledger wallet balance minus all non-deleted goal allocations attached to that wallet. Paused/completed allocations are included, preventing reuse. Allocation amount must be positive and backed by unallocated funds; ownership, active BDT wallet, wallet opening date and recorded date are validated. Internal allocations are tested against all recorded wallet/allocation points from their chosen date forward, including known future ledger events, to prevent backdated double allocation.

### New external deposit

A transfer from an external owned account is represented by **one existing `wallet_events` row classified `external` plus one linked allocation in the same SQLite transaction**. Wallet funds increase once; allocation does not add further assets. It is not income or an expense. If the funds are genuine income, record them through the existing Transactions workflow first, then allocate them; Goals does not invent an income classification. No bank connection, fees or external payment execution is claimed.

### Atomicity, review and duplication

Contribution review validates without writing money. Final recording uses BEGIN IMMEDIATE, rechecks owner/state/goal version and reviewed wallet balance/allocation snapshot, and saves financial event + allocation + canonical compatibility total + version + idempotency receipt atomically. Any late failure rolls back all sides. Stable request keys replay confirmed responses rather than repeating deposits; changed payloads with a reused key are rejected. UI guards prevent repeated submission. Success appears only after backend confirmation. Stale reviews require going back to refresh, not silently changing amounts.

Default target limiting rejects over-target contributions; explicitly unchecking it permits overfunding with an accurate negative remaining amount. Completed goals cannot receive further contributions until a supported target edit reopens them. Future-dated contributions are rejected: planned money is not saved money. Dates follow the existing local recorded-day convention; this release adds no user-timezone setting.

## History, compatibility and explicit limits

- Soft deletion releases wallet earmarks, not money. Wallet balances, deposit events and contribution history remain intact. Deleted Goals provides read-only history; no restoration or contribution reversal UI is implemented.
- Editing metadata or limits does not rewrite financial history. Wallet deletion is guarded when any goal contribution references it; archival retains its audit trail. Inactive/archived wallets cannot receive new contributions.
- Legacy/imported canonical savings with no provenance remain visible as **unlinked imported savings**, not invented wallet-backed allocations. On first write, metadata plus a single legacy audit row materialize without changing any wallet. Its materialization timestamp is known; original funding/date are not. No legacy amount is silently allocated to a wallet or counted twice.
- Earmarks are **not hard spending locks** across existing Transactions. If a later expense or adjustment makes a wallet underfunded, the existing saved history is not fabricated or erased. The funding selector displays the coverage shortfall, availability is zero, and further internal allocations are rejected until funded. There is no claim of automatic enforcement against all later spending.
- BDT only, following existing wallet currency rules. No automatic transfers, bank synchronization, income generation, contribution withdrawal/reversal, push notification or production deployment is included.

## Privacy, accessibility and feedback

The shared global privacy state masks monetary summaries, cards, live wallet availability, history, forms and reviews, without modifying stored amounts. Existing AmountInput switches to masked input while preserving entry usability. Names/categories/dates/statuses remain visible. Native dialogs trap focus, support Escape and preserve return focus. Controls have labels, visible focus and pending/error states; retry does not fake success. Buttons use approximately 150ms hover/press transitions, cards 160ms, progress fills 220ms; existing dialogs/dropdowns are reused. Reduced-motion preferences disable these transitions.

## Verification

See goals-qa/verification.json and the newest section in IMPLEMENTATION_STATUS.md for commands actually executed and final counts. Tests use real isolated FastAPI/SQLite persistence for successful writes; UI-only fixtures and deliberate failed requests are explicitly limited to tests. Four required desktop sizes and both sidebar states are checked for overflow, contained dialogs and keyboard focus. Exact changed files are documented in GOALS_FILES.md. The complete ZIP excludes private environments/databases, installed dependencies, generated build output and caches.
