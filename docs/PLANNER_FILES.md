# Planner changed-file map

- New frontend: `src/features/planner/Planner.tsx`, `PlannerComponents.tsx`, `PlannerForms.tsx`, `api.ts`, `dates.ts`, `dates.test.ts`; `src/styles/planner.css`.
- Integration: `src/App.tsx` (real route); `src/components/layout/ApplicationHeader.tsx` (Planner subtitle); `src/features/goals/GoalComponents.tsx` (optional note concealment in reused AddSavings).
- New backend: `backend/app/planner/__init__.py`, `schema.py`, `routes.py` (v9 owned tasks/occasion metadata and HTTP API).
- Integration: `backend/app/main.py` (migration/router); `backend/app/finance/goals.py` (occasion-backed target-date guard).
- Tests: `backend/tests/test_planner.py`; `tests/planner.spec.ts`; migration version assertions in `backend/tests/test_budgets.py`, `test_goals.py`, `test_transactions.py` changed from8 to9 without weakening business assertions.
- Regression fix discovered in full-suite verification: `src/features/assistant/api.ts` preserves response-body aborts instead of converting them to a successful empty object; two focused tests in `assistant.test.tsx`. No Assistant redesign or provider behavior change.
- Test harness: `playwright.config.ts` isolates screenshot output under `test-results/artifacts` so Playwright cleanup does not remove its live SQLite database.
- Assets/evidence: `public/assets/planner/occasion.svg`, `provenance.json`; `docs/planner-qa/`.
- Documentation: PLANNER.md, this map, README, START_HERE, CLAUDE, ARCHITECTURE, DESIGN_SYSTEM, ASSETS, IMPLEMENTATION_STATUS.

No Figma modifications, new project, dependency additions, authentication redesign or other feature redesign.
