# FINCEPT AI — confirmed financial agent

## What changed

The existing React/TypeScript assistant, FastAPI authentication, SQLite ledger and OpenAI HTTPX adapter are reused. Native Chat Completions tool calls may retrieve owned information or propose changes. The model cannot commit records. A separate authenticated **Confirm & Save** request applies only the exact reviewed revision. Ordinary chat, including “yes” or “confirm,” grants no execution authority. Text-only responses are marked advice-only; only server receipts are presented as saved data.

Supported writes: create/update category budgets, ordinary financial goals and income/expense transactions. A combined plan may contain up to 12 operations and is all-or-nothing. Plans are bounded to 12,000 serialized UTF-8 bytes (including expanded defaults), keeping revised plans beneath the existing 16 KiB HTTP request cap. Shorten notes or split larger plans. All amounts are integer paisa, BDT only; no currency conversion is introduced.

## Tools and grounding

| Tool | Behavior |
|---|---|
| `get_financial_options` | Up to 50 active BDT wallets and 100 owned categories, total counts, goal category choices and server date |
| `get_budgets` | Owned ID or month/search; up to 50 evaluated budgets, total count and date range |
| `get_financial_goals` | Owned ID or search; up to 50 goals and total count |
| `get_transactions` | Owned ID or explicit inclusive date range; latest first, up to 50, `has_more` flag |
| `analyze_spending` | Actual canonical income/expense/net and up to 30 category aggregates over explicit dates |
| `calculate_savings_target` | Exact ceiling of remaining integer target divided by 1–1,200 months; no interest/returns |
| `propose_changes` | One validated combined create/update plan; never commits financial records |

Budget categories and allocations follow the existing conflict rules. The optional expected total must equal the sum of reviewed category limits; the backend calculates that sum regardless. A single aggregate amount does not establish category allocations: the model must clarify or propose a justified breakdown for review.

A dated new goal with no monthly allocation gets the ceiling of remaining target / calendar months (partial month rounds up; minimum one). For a target of BDT 60,000 exactly one year away, the requirement is BDT 5,000/month. No deposits, contributions or additional assets are created. The preview distinguishes configured monthly allocation from the calculated requirement on updated goals.

Agent transactions require explicit type, positive amount, owned active BDT wallet, category and ISO date. “Today” may be resolved against the supplied **server calendar date**, disclosed in context; this is not a per-user timezone engine. Date-only entries use midnight as a storage convention, not an asserted purchase time. Updating an amount on the same day preserves the original timestamp. Future completed transactions, transfers and linked transfer fees are rejected. Existing historical balance guards apply.

Retrieval is bounded, not an exhaustive report/export tool. Initial English intent context remains available, but native reads can use independently validated explicit dates (1901–2100, ordered range <= ten years). Ambiguous targets or missing essential data must be clarified. Model natural-language quality still needs live-provider review.

## Approval API

Existing `/api/assistant/conversations` and message routes remain. Successful assistant messages may carry a `proposal` containing current status/version, editable plan, server preview and optional actual saved result.

All routes use the existing HttpOnly session, server-derived user ID and `dataset=live|demo` isolation. Production rejects demo. Mutations require `X-Fincept-Request: 1` and existing Origin/CSRF checks. Extra fields are rejected; owner IDs are never accepted from a client or model.

| Route | Request / response |
|---|---|
| GET `/api/assistant/proposals/options` | Actual allowed wallets/categories and budget/goal category options for editing |
| GET `/api/assistant/proposals/{id}` | Owned current proposal, computed expired status, immutable saved receipt if executed |
| PATCH `/api/assistant/proposals/{id}` | `{version, plan:{operations, expected_budget_total_minor?}}`; revalidates and increments revision; does not execute |
| POST `/api/assistant/proposals/{id}/cancel` | `{version}`; serializes cancellation; no corresponding pending write can subsequently execute |
| POST `/api/assistant/proposals/{id}/confirm` | `{version, confirmation:"CONFIRM"}`; revalidates, atomically saves and returns actual records |

Operations use `operation` (`budget.create/update`, `goal.create/update`, `transaction.create/update`), `record_id` for updates only, and an allowlisted `data` object. Updates may supply changed fields; the backend fills current fields, binds current record version and presents a full preview. Model/client ownership IDs, optimistic versions and internal request keys are rejected. The server does not accept SQL, Python, arbitrary endpoint names or credentials.

## Security, concurrency and failure semantics

- The proposal is bound to authenticated owner, dataset, conversation and originating request. UUIDs are unguessable but never replace authorization. Another user's ID returns 404.
- Each proposed plan is run through the same canonical budget/goal/transaction services under an **always-rolled-back validation savepoint**. Temporary writes are invisible outside that transaction and no finance changes persist. Validation runs again when the proposal is stored and when approved.
- `BEGIN IMMEDIATE` serializes confirmations, edits and cancellation. Preview-only IDs on proposed creates are provisional and must never be treated as saved identifiers; actual IDs are returned by the executed receipt. The complete financial plan plus executed receipt commit together. Failures roll back everything, not partial plans.
- Pending proposals expire after 30 minutes. A successful edit increments version and refreshes expiry; an old approval is rejected. Updating a financial record after review also invalidates execution. Backend state, not the UI clock, is authoritative.
- Reconfirming an executed revision returns its durable receipt without running commands again, including after restart or a lost response. A competing cancellation cannot undo an already committed action and returns a clear conflict; a completed cancellation prevents later execution. There is no claim that cancellation wins a race already committed by confirmation.
- Existing overlapping-budget rules apply. Case-insensitive duplicate goal names are rejected on creation. Exact same date/wallet/type/amount/category/title transactions are rejected on agent creation. Legitimate repeated purchases with identical fields may require the manual Transactions interface. These guards cannot infer semantic duplicates with different names/details.
- Canonical wallet ownership, category validation, numeric limits, record versions and historical balance/earmark guards remain enforced. Planner-linked goals are intentionally not agent-editable.
- Native orchestration allows <=4 provider turns / <=8 tool calls within the existing 30-second overall deadline. No DB transaction is held across provider network calls. Only allowlisted tool names are accepted. Malformed arguments receive safe corrective feedback; excessive loops fail safely.
- Provider/database errors never expose keys, stack traces or financial payloads in logs. A lost confirmation response reloads current proposal state; saved receipts prove actual success. Database failures return a safe message and preserve safe retry. Model prose is never trusted as evidence of a write.
- Structured proposal data is removed from the DOM in global privacy mode; Confirm/Edit are disabled until review is visible. Cancellation remains available. This is display privacy, not encryption or a prohibition on backend/provider processing.

## Frontend and dashboard refresh

`ActionProposalCard` uses existing Money, privacy, buttons, tokens and escaped React rendering. It shows before/after fields, category totals, goal monthly requirements, expiry and execution status. Inline Edit uses actual wallet/category options and validated decimal conversion; saving a revision requires a new, separate confirmation. Buttons use synchronous request locks and loading/error states. Actual saved results link to the relevant application screen.

`financeChanges.ts` emits a same-tab event and a cross-tab UUID revision marker. Mounted Overview resources, Budgets, Goals, Transactions, Wallets and Insights refetch actual backend data after a saved receipt, including recovered receipts. No financial values are stored in that notification. The shared shell is retained; narrow assistant-only layout and stacked forms are verified without redesigning other pages.

## Migration and deployment

1. Back up the existing SQLite database and deploy the entire updated frontend/backend together.
2. Preserve existing authentication, database path, exact frontend origins, HTTPS and secure-cookie configuration.
3. Server-only existing variables: `AI_PROVIDER=openai`, `AI_MODEL=<enabled native-tool-capable Chat Completions model>`, `OPENAI_API_KEY=<private key>`. The model must support `tools`, `tool_choice`, `parallel_tool_calls` and `max_completion_tokens`. Do not use `VITE_` credentials. No new runtime dependency or variable is required.
4. Restart the backend. The existing lifespan runs prior migrations through Settings v11, then creates additive **v12 `assistant_proposals`**. No manual migration command or replacement user/finance table is required. Do not downgrade this database to code that only understands older migrations.
5. Build/deploy the frontend through the existing process. Missing provider configuration leaves history/manual finance screens usable but cannot generate AI plans.
6. Review expanded provider disclosures: authorized tools may send internal financial record IDs, wallet names, categories, notes/descriptions and amounts, in addition to initial summaries/completed chat history. Never external account secrets, credentials or session tokens. Configure provider terms, retention, filesystem protections and backups appropriately; SQLite is not separately encrypted at rest.
7. Verify representative natural-language prompts with the configured paid model, then separately review and confirm safe test-account changes. No live credentials were available during implementation; do not mistake protocol doubles for live model compatibility or financial advice quality certification.

## Deliberate limits

No agent deletion, category management writes, transfer/payment execution, savings contributions, Planner/debt/hub mutations, bank connections, automatic scheduling, restore or account deletion. Existing manual features are preserved. A read-only alternative adapter lacking native tools can still provide advice, but cannot prepare plans. No provider streaming/cancellation or unattended auto-approval. Settings support/notification/legal/integration limitations are unchanged. No new Figma redesign or asset replacement was required for this behavior change.

## Verification

Current commands, counts and limitations are in `agent-qa/verification.json` and the newest `IMPLEMENTATION_STATUS.md` section. Run from the repository root with installed existing dependencies:

```sh
npm test
npm run build
(cd backend && /path/to/venv/bin/python -m pytest -q)
PYTHON_BIN=/path/to/venv/bin/python PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/path/to/chromium npm run test:e2e
PYTHON_BIN=/path/to/venv/bin/python PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/path/to/chromium ./node_modules/.bin/playwright test --config playwright.actions.config.ts
```

The action browser fixture is deliberately isolated in `tests/fixtures/agent_server.py`, refuses non-test database paths, and is never imported/configured by production startup. It scripts native model responses only; real auth, proposal validation, approval writes and dashboard reads run against the actual backend. Backend native-protocol HTTP tests use mock transport; the existing paid live-provider test remains opt-in/skipped. No lint script is configured. The existing Vite >500kB bundle advisory is not a build failure.
