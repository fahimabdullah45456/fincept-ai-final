# Debt & Loans + Financial Hub — release verification

## Delivered scope
Existing React/FastAPI application extended, not replaced. Read-only Figma preflight and original SVG provenance are recorded in DEBT_HUB_DESIGN_MAP.md and ASSETS.md. No Figma writes. New accounts have no fabricated debt, shopping or calendar records.

Debt includes Borrowed/Lent/EMI tabs, real persisted creation/editing, reviewed schedule preview, partial/full tracked payments, immutable correction reversals, settled-only archive, derived commitments/history, filters/sort, and global monetary privacy. Hub reads canonical wallet balances, supports persisted shopping list/item CRUD and purchase tracking, routes shortcuts/wallet activity, derives upcoming actual Planner/EMI activities and provides genuine indicative FX.

## Executed checks
- `npm run build`: passed after final code/style changes. Vite main minified JS 574.70 kB, above its 500 kB advisory; no TypeScript/build errors.
- `npm test`: **103 passed**, 15 files.
- `PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests -q`: **166 passed, 1 skipped**. Existing credential-dependent live-AI test skipped; one existing Starlette/httpx deprecation warning.
- Full `npm run test:e2e` with PYTHON_BIN and PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH overrides: **108 passed** in 7.2 minutes, including all previous feature regressions and the first nine new Debt/Hub scenarios.
- After the final original-icon/CSS refinements, `npm run test:e2e -- tests/debt-hub.spec.ts`: **12 passed** in 1.1 minutes. This rerun overlaps nine cases from the full suite and adds three; it is not a separate 120-test unique total. All twelve ran against final code.
- `npm audit --omit=dev --json`: **zero reported production dependency vulnerabilities**.
- A genuine authenticated `/api/hub/rates?base=BDT` request, without mocked provider data, returned HTTP 200 and ten supported currencies. See `live-provider-check.json` for provider/fetch timestamps. No API key was required.

The browser suite used the existing FastAPI/SQLite app and isolated real accounts/records. FX success/error/cache states in deterministic browser screenshots use explicit test response fixtures (including intentionally synthetic 1:1 rates); those screenshots are not evidence of a real quoted exchange rate. Genuine live-provider evidence is separate. No fixtures are used as application fallback rates.

## Desktop visual QA
1440×900, 1366×768, 1280×800 and 1024×768, with sidebar states and dialog/overflow checks; also 1440×1320 and 1440×1620 reference-size captures. Borrowed/Lent/EMI/Hub captures are saved here alongside forms, reviewed payment, privacy and error states. Final 1440 reference captures were reopened for visual inspection. Original Figma main frame references are QA-only, never runtime UI.

Hierarchy, widths, surfaces, color, typography and original icons follow the reference. Real saved data, provider attribution/freshness and extra supported archive/error states legitimately differ from sample frame content. Browser font/rasterization and content-dependent section heights differ; pixel identity is not claimed. Screenshots include isolated test data only, not shipped live database rows.

## Boundaries and setup
- Additive SQLite schema **v10**; back up an existing database before startup migration. Existing auth, canonical ledger, Goals, Planner and Assistant data are preserved.
- Debt payments are **manual tracking only**: no wallet movements, bank transfers or income/expense records. Initial principal and down-payment metadata likewise do not move money. EMI principal is included once in borrowed totals.
- Interest supports an explicit agreed fixed total, not APR/amortization/accrual. Dates use civil dates and the browser IANA timezone; dates passing do not automatically mark payments paid.
- Shopping actual costs are entered tracking values, not verified expenses. No automatic transaction matching/linking or expense creation; Open Transactions is navigation only.
- No email/push reminders, bank connectivity or external payment execution. FX is indicative, daily-provider dependent, cached one hour, stale visibly bounded to 48 hours; outbound HTTPS is required. There is no production deployment in this delivery.
- Existing Google OAuth/password-recovery/legal/optional AI credential limits remain documented elsewhere. New Debt/Hub features need no new secrets.

## File map
Frontend: `src/features/debt/{Debts,DebtForms}.tsx`, `api.ts`; `src/features/hub/{Hub,ShoppingForms,CurrencyConverter}.tsx`, `api.ts`, `hub.test.ts`; `src/styles/debt-hub.css`; route/header wiring; minimal Wallets deep-link handling.
Backend: `backend/app/debt/{schema,routes}.py`, `backend/app/hub/{routes,fx}.py`, main startup/router wiring; `backend/tests/test_debt_hub.py`. Shared schema-version test assertions advance to v10 without changing their business assertions.
Docs: DEBT_LOANS.md, FINANCIAL_HUB.md, DEBT_HUB_DESIGN_MAP.md, assets provenance, architecture/status/setup notes and this evidence folder. No new runtime dependencies.
