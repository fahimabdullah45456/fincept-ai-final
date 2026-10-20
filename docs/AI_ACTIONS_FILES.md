# Action-agent source inventory

Compared byte-for-byte against `FINCEPT-AI-With-Settings.zip` (prior delivered project). This is an additive extension of that repository, not a new application. Dependencies, package manifests/lockfile and public assets are unchanged. Existing test files changed only their expected startup schema version (11 → 12); new action tests add coverage rather than weakening financial/auth assertions. Canonical finance command extraction keeps manual and approved agent operations on the same implementation.

## Modified files

- `CLAUDE.md`
- `README.md`
- `START_HERE.md`
- `backend/.env.example`
- `backend/app/assistant/__init__.py`
- `backend/app/assistant/context.py`
- `backend/app/assistant/provider.py`
- `backend/app/assistant/routes.py`
- `backend/app/finance/budgets.py`
- `backend/app/finance/goals.py`
- `backend/app/finance/transactions.py`
- `backend/app/main.py`
- `backend/tests/test_budgets.py`
- `backend/tests/test_goals.py`
- `backend/tests/test_planner.py`
- `backend/tests/test_settings.py`
- `backend/tests/test_transactions.py`
- `docs/ARCHITECTURE.md`
- `docs/ASSISTANT.md`
- `docs/IMPLEMENTATION_STATUS.md`
- `src/components/layout/AuthenticatedLayout.tsx`
- `src/features/assistant/Assistant.tsx`
- `src/features/assistant/AssistantComponents.tsx`
- `src/features/assistant/api.ts`
- `src/features/budgets/Budgets.tsx`
- `src/features/goals/Goals.tsx`
- `src/features/insights/Insights.tsx`
- `src/features/overview/useOverviewResource.ts`
- `src/features/transactions/Transactions.tsx`
- `src/features/wallets/Wallets.tsx`
- `src/styles/assistant.css`

## Added files

- `agent-tests/actions.spec.ts`
- `backend/app/assistant/action_schema.py`
- `backend/app/assistant/actions.py`
- `backend/app/assistant/tools.py`
- `backend/tests/test_assistant_actions.py`
- `docs/AI_ACTIONS.md`
- `docs/agent-qa/README.md`
- `docs/agent-qa/backend.txt`
- `docs/agent-qa/browser_actions.txt`
- `docs/agent-qa/browser_regression.txt`
- `docs/agent-qa/build.txt`
- `docs/agent-qa/proposal-1024.png`
- `docs/agent-qa/proposal-1280.png`
- `docs/agent-qa/proposal-1366.png`
- `docs/agent-qa/proposal-1440.png`
- `docs/agent-qa/proposal-390.png`
- `docs/agent-qa/unit.txt`
- `docs/agent-qa/verification.json`
- `playwright.actions.config.ts`
- `src/features/assistant/ActionProposalCard.tsx`
- `src/features/assistant/actions.test.tsx`
- `src/features/financeChanges.ts`
- `tests/fixtures/agent_server.py`
- `docs/AI_ACTIONS_FILES.md` (this inventory)

## Archive exclusions

No `node_modules`, build output, local virtualenv, local `.env`, SQLite databases, test-results, Playwright reports, Python caches or TypeScript build caches. Install existing dependencies using the project README. Preserve the deployed `.env` and database; the source archive is not a user-data backup. Original Settings functionality and documentation are retained.
