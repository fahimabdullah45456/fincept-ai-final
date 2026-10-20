# Debt & Loans — implemented v10

## Direction and accounting
`/debt-loans` contains Borrowed, Lent and EMI & Installments views. Authenticated records are scoped by owner and `live`/development-only `demo` dataset. A financed purchase is one outgoing obligation, not a second loan plus six more debts. Balances are derived from original integer minor-unit principal and the immutable payment ledger; no mutable outstanding total is stored.

**Explicit tracking-only boundary:** creating a loan, recording its down payment metadata, recording a repayment/collection or correcting it does not move wallet funds, execute a transfer or create ordinary income/expense. The payment review says this before confirmation. Initial receipts/disbursements and repayments are not linked to Wallets/Transactions in this version. Never record principal as ordinary spending to make these records reconcile. Existing wallets/transactions remain untouched. Manual history may describe payments made externally; the app does not verify external settlement.

Principal, agreed interest and actual fees are separate integer amounts. Interest terms support an **explicit fixed total** (zero means interest-free), not APR/simple/amortized accrual; no rate, charge or accrued interest is inferred. Principal cannot exceed remaining principal; interest cannot exceed agreed remaining interest. Fees are separately recorded actual fees, not invented schedule principal. Future payments and payments before the original date are rejected. Name/counterparty/notes remain editable after payments; financial terms are locked after any history exists, including reversals. Payments cannot be edited/deleted; correction adds an immutable reversal entry with a reason. Reversed original payments no longer reduce balances, and both original and correction remain visible. Only fully settled records can be archived; there is no destructive loan deletion.

## Scheduling and summaries
Weekly schedules use seven civil days. Monthly dates anchor to the original day and clamp per month (Jan 31 → Feb 28/29 → Mar 31, never drift to Mar 28). Schedule range: 1901–2100, at most 600 installments. Price minus down payment must equal financed principal. Count/regular installment must cover total principal plus fixed interest; a positive smaller final installment is supported. Proportional cumulative integer rounding preserves exact total principal and interest. FIFO allocation separately applies recorded principal and interest; partial payments are supported. Merely passing a due date never marks an installment paid. Schedule scope controls use the actual derived statuses.

Main summaries are global, independent of tab/search/status:
- Total Borrowed: unarchived borrowed and EMI **outstanding principal**, counted once.
- Total Lent: unarchived outstanding receivable principal, never wallet funds.
- Upcoming Payments: unpaid outgoing principal + agreed interest due **after today through today + 30 days**, with count. Today is shown separately as Due Today in schedules/next commitment.
- Overdue Amount: unpaid outgoing scheduled amounts due before today, with count.

Next commitment/collection/installment includes today, never relabels overdue as upcoming. Tab-level EMI metrics show monthly recurring commitment, total installment balance including interest, due-soon count and overdue count. Search covers title/counterparty/visible notes; status and sorting act on saved rows. History stays scoped to the selected direction, not search. Shared privacy conceals money, monetary progress and notes; it does not alter calculation or storage. Civil dates have no UTC conversion; Debt API accepts validated IANA `timezone` (UTC default). UI sends the browser timezone for reads and writes. No reminder service is available.

## Schema and API
Additive v10 in `backend/app/debt/schema.py` retains all v1–v9 finance, auth, assistant and Planner tables. `debt_records` owns terms/version/archive state; `debt_payments` owns immutable records and unique reversal references. All writes use SQLite IMMEDIATE transactions, existing idempotency receipts, owner/dataset checks and optimistic versions.

- `GET /api/debts`: owned enriched records, history, schedule and global summary.
- `POST /api/debts/preview`: authenticated validated schedule, no persistence.
- `POST /api/debts`: create; `PATCH /api/debts/{id}`: supported edits.
- `POST /api/debts/{id}/payments`: persist tracked payment atomically with parent version.
- `POST /api/debts/{id}/payments/{payment_id}/reverse`: append correction.
- `DELETE /api/debts/{id}`: settled-only archive, history retained.

Mutations require existing session, anti-CSRF header, stable request_key and version where applicable. Changed-payload key reuse and stale versions return 409; ownership mismatches return 404. No live finance provider credentials are required.
