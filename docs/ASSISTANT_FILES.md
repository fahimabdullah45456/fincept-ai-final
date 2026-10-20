# AI Assistant — delivery file inventory

This extends the existing `FINCEPT-AI-With-Insights.zip` project. The inventory was checked against that source archive, not an unavailable Git history. No authentication or financial page was rebuilt. Generated browser screenshots from existing regression suites can change without corresponding product-source changes.

## New production frontend

| File | Responsibility |
|---|---|
| `src/features/assistant/Assistant.tsx` | Real page, composer, durable send/retry lifecycle, conversation selection/search/pagination, receipt polling and auth/privacy integration |
| `src/features/assistant/AssistantComponents.tsx` | Welcome suggestions, escaped role messages, deterministic summary card, typing and safe retry/error components |
| `src/features/assistant/api.ts` | Typed authenticated API client, timeout/error receipts, original suggestion text, message deduplication and conservative privacy presentation |
| `src/styles/assistant.css` | Figma-based layout, typography, surfaces, responsive desktop history/workspace, focus/hover/press/message animations and reduced motion |
| `public/assets/assistant/sparkle.svg` | Original read-only Figma assistant sparkle geometry |
| `public/assets/assistant/suggestion.svg` | Original read-only Figma suggested-question geometry |
| `public/assets/assistant/provenance.json` | Original node IDs, source and extraction details |

### Small shared integration changes

- `src/app/App.tsx`: mounts `/ai-assistant/*` in the existing authenticated shell; removes that route from placeholders.
- `src/components/layout/ApplicationHeader.tsx`: assistant-specific subtitle, unchanged shared controls.
- `src/components/ui/Icon.tsx`: adds the assistant asset collection to the existing mask renderer.

## New backend

| File | Responsibility |
|---|---|
| `backend/app/assistant/__init__.py` | Assistant module |
| `backend/app/assistant/schema.py` | Additive v8 conversations, requests and messages; integrity/owner/dataset references and indexes |
| `backend/app/assistant/provider.py` | Async provider protocol and actual server-side OpenAI HTTP adapter; bounded response, private configuration, safe failures |
| `backend/app/assistant/context.py` | Focused owner/dataset-scoped financial read model using existing ledger/budget/goal/Insights calculations; explicit periods and exact decimal amounts |
| `backend/app/assistant/routes.py` | Status, owned conversation create/list/detail and message endpoints; persistence, pagination, rate limits, deadlines, lease fencing and idempotency |

### Existing backend integration changes

- `backend/app/main.py`: initializes assistant schema after existing finance migrations; mounts router and supports explicit provider injection for tests.
- `backend/requirements.txt`: moves pinned HTTPX capability into runtime requirements for real provider requests.
- `backend/.env.example`: empty private server-side AI configuration placeholders and optional live-test flag. No real key is included.

## Tests

- New `src/features/assistant/assistant.test.tsx`: seven component/transport/privacy/safe-rendering/suggestion tests.
- New `backend/tests/test_assistant.py`: provider contract, missing configuration, failure/retry, auth/ownership/dataset, financial grounding, pagination/persistence, concurrency/idempotency, rate limits and deadlines; one separately gated live-provider test.
- New `tests/assistant.spec.ts`: eleven browser cases, including real missing-provider persistence and all four desktop viewports/sidebar states. Successful model output is an explicitly labeled UI test fixture, not live-provider evidence.
- `backend/tests/test_transactions.py`, `test_budgets.py`, `test_goals.py`: app-startup migration expectations now v8; direct finance-initializer expectation remains v7.
- `tests/sidebar.spec.ts`: existing UI-only fake-session fixture explicitly returns assistant-unavailable instead of reaching a real endpoint with no cookie.
- `tests/ui-corrections.spec.ts`: existing date-picker keyboard test waits for its requestAnimationFrame focus movement before the next arrow key; no production calendar change.

## Documentation and verification

New: `docs/ASSISTANT.md`, this inventory and `docs/assistant-qa/` (Figma/implementation screenshots, final command logs and machine-readable `verification.json`).

Updated: `README.md`, `START_HERE.md`, `CLAUDE.md`, `docs/ARCHITECTURE.md`, `docs/ASSETS.md`, `docs/DESIGN_SYSTEM.md`, `docs/IMPLEMENTATION_STATUS.md`, and the backend environment example above.

The screenshots and logs are verification artifacts, never runtime UI. Existing authentication/finance regression suites also refresh their historical screenshot paths. Their source implementations are unchanged.

## Source package exclusions

The delivered ZIP omits installed `node_modules`, backend `.venv`, build output, caches, test-runtime state, private `.env` values and SQLite databases/journals. It retains source, lockfiles, safe environment examples, original assets, setup instructions and verification evidence. Install dependencies and configure a private backend provider before requesting actual model replies. No deployment, live provider success or encrypted database storage is claimed.
