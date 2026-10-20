# Planner — Calendar & Tasks

## Inspected design / implementation map (before coding)
Read-only Figma source kpEbLoKLaLiUcB8Q6xxgRl, page 2001:7030, desktop 2001:89823 (1440×1080), selected date 2001:90112, completion 2001:90401, November 2001:90671. Also inspected Add Task 2001:92369, Edit Task 2001:93319, Delete Task 2001:93649, Create Occasion Plan 2001:91668, Occasion Savings Plans 2001:90911, handoff 2001:96517 and original reusable components 2001:97310. Metadata identified loading, errors and empty variants. No Figma writes were made. Figma design-to-code and figma-use skill resources were unavailable (Unknown resource); read-only Plugin API inspection, metadata, screenshots and asset download were available and used. No generated Tailwind code was used; existing React/plain CSS conventions remain authoritative.

- Shared shell, header, privacy and sidebar remain existing components.
- SummaryCard 156:9164 → PlannerSummaries: exact five meanings, live values instead of sample data.
- Calendar 156:8947 → Calendar / date utilities: Monday-first seven columns, live dates and records, selected day, today, previous/next controls, fixed Month view label (not a fake selector).
- TaskRow 156:9082 → TaskRow: actual completion control, status, metadata and editing.
- OccasionCard 156:9053 and PlanProgress 156:9090 → OccasionCard: target/saved/remaining and conservative estimates, real goal allocation data.
- FormControl 156:9160 / Modal 156:9168 → shared Dialog, existing DateTimePicker, semantic controlled fields. Task modal source 720×810; plan 760×850, scroll inside viewport.
- Exact page subtitle: “Organize your schedule and prepare financially for what matters.” Runtime action label is “+ Add Task” (Figma action layer is named TaskForm), not the layer name.
- Manrope; #F9733B orange, #F7F7F4 background, #20211F text; r16 panels/cards, r20 modals, r11/h42 actions. Main reference calendar: 900:380 split with 20px gap; date cells 84px minimum; summary cards 100px; labels11, values25, captions10; heading30/44, subtitle14/21.

## Accounting boundary / model choice
Existing repository had no tasks, occasion plans, scheduled-payment model or reminder delivery. v9 adds owner/dataset-scoped planner_tasks and planner_occasions. Each occasion references ONE canonical financial_goals record (same ID), with existing goal_metadata and goal_contributions. No duplicate saved balances or new wallet balances. Occasion goals also remain visible in Financial Goals, explicitly identified by category/description, and share the same allocation capacity checks and history. This intentional reuse means a contribution from either route immediately changes Planner totals; it must never be counted as a new asset.

## API and ownership
All routes require the existing authenticated HttpOnly session. Writes require existing CSRF/Origin checks, JSON request keys and server-side validation. IDs are not authorization: every read/write is scoped to user and `live`/`demo`. Production rejects demo workspaces. Foreign plan links return 404; archived plans cannot receive new task links. Mutations use SQLite `BEGIN IMMEDIATE`, optimistic versions and existing replay receipts; resubmitting an identical request returns its committed result instead of creating a second record. Conflicts return 409 and instruct the user to reload.

| Route | Purpose |
|---|---|
| GET `/api/planner?month=YYYY-MM&timezone=IANA` | Calendar range, filtered tasks, canonical occasion plans, global summaries |
| POST `/api/planner/tasks` | Create task |
| GET/PATCH/DELETE `/api/planner/tasks/{id}` | Read, edit/reschedule, confirmed delete |
| POST `/api/planner/tasks/{id}/status` | Complete/reopen or supported status |
| POST `/api/planner/plans` | Create canonical occasion goal + Planner metadata atomically |
| GET/PATCH `/api/planner/plans/{id}` | Read/edit occasion plan |
| Existing `/api/goals/{id}` and `/api/goals/{id}/contributions[/preview]` | History, reviewed wallet allocation/external deposit and archive |

Task fields: title, description, civil due date, optional HH:mm wall time, IANA timezone, category, priority, status, optional owned occasion ID and version. Statuses are To Do, In Progress, Completed, Cancelled. The original four UI scopes are All/Upcoming/Overdue/Completed; All includes cancelled rows with explicit status and muted calendar entries. Cancelled/completed rows never count as open tasks. Cancelled tasks can be edited/reopened or deleted, but cannot be checked complete directly.

Plan fields: name, occasion type/custom label, occasion date, saving start date, target minor units, weekly/monthly contribution preference, planned minor units and notes. “Already saved” is read-only: new plans start at zero. Real reviewed contributions establish saved amounts. Existing Goals edits update the same canonical target/name/monthly pace; a targeted validation prevents removing occasion dates or moving them before saving start. No tasks are generated automatically.

## Calendar/date semantics and filters
Dates are stored ISO `YYYY-MM-DD`, range 1901–2100; optional HH:mm and IANA zone are metadata, **not** UTC instants or scheduled alarms. All-day records never move when timezone changes. Date arithmetic uses UTC-noon civil-date helpers (not midnight UTC parsing). Weeks start Monday; grids contain complete weeks (4, 5 or 6), including adjacent-month dates. API bounds are inclusive and match the grid. Keyboard arrows and Home/End move selection, including across month boundaries; selected day shows all matching entries, while each cell shows up to two with a selectable overflow count.

The initial planning timezone is the browser IANA zone (fallback Asia/Dhaka). The editable timezone preference is stored locally, not financial data. Today/overdue refresh on window focus and every 15 seconds; server calculations use the requested zone. Task wall times do not convert when changing this preference. There is no multi-day event, recurring task or external calendar integration.

Month/tab/dataset are URL-scoped. Search matches task title/description or occasion name; category filters real saved categories. Status filters tasks; occasion entries appear only under All. The agenda task list is the selected month; adjacent dates remain available in the grid and selected-day details. Clearing filters restores records. Filters never mutate data.

Five summaries are global, deliberately independent of month/search/category/status: open tasks due today or later; active unarchived upcoming occasions; targets across active unarchived plans; canonical saved allocations across those plans; sum of each plan's clamped remaining amount. Overdue open tasks are separately disclosed in the first caption. Completed/cancelled tasks are excluded from open counts. Paused/archived plans are excluded from active monetary summaries. Goal-reached plans remain active until paused/archived and have zero remaining. There is no invented financial metric for ordinary tasks.

Estimates use `max(today, saving_start)` through the occasion date: complete weeks, complete calendar months, minimum one installment if a partial period remains, and rounding **up** to whole taka. Past-deadline recommendations pause; fully funded estimates are zero. Weekly/monthly preference does not schedule transfers. Planned payments are tasks, never confirmed expenses. Task completion/deletion cannot change wallets, budgets or transaction history. Existing-wallet allocation only earmarks money; external-deposit contribution uses the existing reviewed income flow, not an unbacked saved balance.

## Migration / configuration
The existing application startup initializes additive SQLite schema v9 after finance and assistant schemas. No manual migration command or new service is required. Back up existing databases before upgrading; existing rows are preserved. New accounts start empty. Test users/records and local test databases are excluded from the delivery archive. Existing environment examples and run commands still apply; Planner needs no API key. Reminder fields are visibly disabled: no delivery worker/provider is connected, no notification permission is requested and no alarm is claimed. Existing unrelated OAuth/reset/AI configuration gaps remain as documented in README.

## UI reuse, privacy and motion
Existing application shell/sidebar/header, Dialog focus/escape handling, DateTimePicker, monetary Money formatting/privacy, error presentation, command locking/retry and reviewed AddSavings flow are reused. Only Planner-specific composition/date logic/API modules were added. Monetary summaries, amounts, progress and plan notes/history notes respect the global privacy setting; task titles/dates/status stay readable. Shared AddSavings gained an optional Planner note-concealment prop; other callers retain their prior behavior.

160ms scoped hover/border/pressed feedback, calendar month fade, day selection, event focus/hover, pending save/complete states and existing shared dialog transitions are retained; reduced-motion disables Planner motion. Native selects/time fields use browser interaction behavior, not a custom animated dropdown. No animation library or artificial network delay was introduced. Success notices occur only after server confirmation; checkbox intent is shown pending and rolls back on error.

## Visual QA and known limits
Reference screenshot and actual desktop/form/privacy/error captures are in `docs/planner-qa/` (test accounts only). Compared the running UI against read-only Figma: five-card hierarchy, palette/type, selected-day agenda, calendar proportions/cells and forms. Tested all four required desktop sizes with collapsed and expanded sidebar, no horizontal document overflow and scrollable dialogs. At narrow desktop content widths the agenda stacks rather than clipping. Native control rendering and real record text/counts naturally differ from the sample. No pixel-identical or WCAG certification claim is made.

Core task/calendar and create/edit/archive/reviewed-contribution plan workflows are implemented. Richer Figma prototype panels for expense-breakdown editing, contribution edit/delete/release from Planner, notification delivery, recurring tasks and external calendar sync are not implemented or exposed as working controls. Goal allocation/history operations continue to use the existing Goals feature. This is a local implementation, not deployed to the user's computer or production.

## Verification
Commands and final counts are recorded in `docs/IMPLEMENTATION_STATUS.md`. New unit coverage validates every month from 1901–2100, leap years, month sizes, weekday alignment, 4/5/6-week grids, civil-date DST/year arithmetic and timezone day boundaries. Real SQLite/HTTP tests cover lifecycle, idempotency, optimistic conflicts, linking, ownership/CSRF/dataset isolation, invalid values, empty data, restart persistence, canonical allocation integrity and estimates. Real-browser tests cover task create/edit/reschedule/complete/delete, cancelled deletion confirmation, plan/create/edit/archive/funding, filters, keyboard month crossing, privacy and the four desktop sizes. Only error-transport scenarios explicitly intercept responses; persistence success tests use the real backend.
