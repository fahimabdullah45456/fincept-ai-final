# Settings verification

Executed on 2026-10-20 against disposable local test databases/accounts. No existing personal database, provider account, or production user data was accessed. The user-requested implementation was made directly in the supplied repository; no Codex executable/integration was available.

## Executed commands and results

| Command | Result |
| --- | --- |
| `npm ci` | Installed the supplied lockfile dependencies; no package versions changed |
| `python -m venv /data/fincept-venv` then `/data/fincept-venv/bin/pip install -r backend/requirements-dev.txt` | Isolated backend environment installed |
| `npm run build` | Passed: TypeScript project build and Vite production build; >500 kB chunk warning remains |
| `npm test` | **110 passed**, 16 files, including 7 new Settings unit tests |
| From `backend`: `/data/fincept-venv/bin/python -m pytest -q` | **179 passed, 1 skipped**; the existing paid live-AI-provider opt-in test was skipped because credentials/opt-in were absent |
| From `backend`: `/data/fincept-venv/bin/python -m pytest -q tests/test_settings.py` | **13 passed** |
| `PYTHON_BIN=/data/fincept-venv/bin/python PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=$(command -v chromium) npm run test:e2e` | **125 passed** across the whole application (before final Settings-only compact-navigation and additional tests) |
| Same environment, `npm run test:e2e -- tests/settings.spec.ts` | Final Settings rerun: **17 passed**, including all final compact-navigation changes and additional conflict/profile-error/expired-session cases |
| `npm audit --json` | Existing dev-tool findings: **1 moderate, 2 critical** across `@vitest/mocker`, `tinypool`, and `vitest`. Audit is not a passing security check; a major toolchain update is suggested by npm and was not applied as an unrelated scope change |
| `npm audit --omit=dev --json` | **0 reported production-dependency vulnerabilities** in npm's audit; this is not a comprehensive application-security certification |

There is no configured lint command/framework in the supplied package. No separate lint pass is claimed. Python tests retain existing Starlette/httpx and Pydantic warnings. Full logs and both npm audit JSON files are included in this directory.

## Coverage

- Real authenticated profile loading, validation, cancel, backend save/failure, refresh, ownership, and immediate shared-header/summary updates.
- Versioned account preferences, strict server validation, cross-account isolation, stale-save rejection/reload, retry, busy/duplicate-submit guards and retained drafts on errors.
- Shared browser-local monetary privacy across Overview, Transactions, Wallets, Budgets, Goals, Insights, Debt & Loans, Financial Hub, Planner, Assistant and Settings; formatting applies to shared Money without modifying integer financial records.
- Real password verification/hashing, current-cookie renewal and genuine other-session revocation; security responses omit secrets.
- Genuine CSV/JSON downloads, empty exports, original amounts, quote/newline/formula safety, manifest scope, metadata ownership, and rejection of attempts to select another user.
- Explicit unsupported provider/delivery/restore/deletion states; malformed restore requests cannot run an importer because no restore endpoint exists.
- Typed demo confirmation, current-owner/dataset isolation, repeat clearing, pending sample-AI protection and full transaction rollback on failure.
- Native dialog initial focus, Escape, focus restoration, busy dismissal protection; keyboard switches and FAQs; direct category URLs and browser back/forward.
- All seven categories and contained dialogs at **1440×900, 1366×768, 1280×800, 1024×768 and 390×844**. Both sidebar states are checked, including narrow overlay expansion. Tests wait for route selection and sidebar transitions rather than capturing a previous category or intermediate width.

## Visual review and evidence

Forty implementation screenshots are included: seven categories plus a security dialog at each of the five sizes. Desktop Profile, tablet Notifications, desktop Data & Account and narrow Data & Account were inspected visually. The initial narrow summary squeezed long names/emails; it was corrected with a reserved text column. Narrow category navigation now uses a labeled native select.

These are implementation-only images. The Settings Figma source could not be opened and no Figma MCP was available; exact Figma fidelity, component variant matching, original Settings icon matching and side-by-side design comparison remain **unverified**. No screenshots are used as runtime interface content.

## Intermediate failures resolved

- The first TypeScript build exposed an empty literal-union placeholder-route filter after Settings completed the route registry; the obsolete mapping/import was removed.
- Existing startup-migration assertions expecting v10 were updated only where startup now correctly applies v11. Canonical financial assertions remain unchanged.
- An initial new-test write/test command used the wrong working directory and did not create the intended file; it was corrected and rerun.
- A first browser invocation used a nonexistent `/usr/bin/chromium`; final commands resolve the installed `/usr/local/bin/chromium` through `command -v chromium`.
- Browser testing caught React `autoFocus` running before native dialog opening. Shared Dialog gained an explicit optional initial-focus selector and safe trigger restoration, then the whole existing browser suite passed.
- Responsive tests were strengthened to await first render, selected category and completed sidebar animation. Final screenshots are of the settled target category.
- Regenerated unrelated pre-existing QA images were restored from the original archive, so this delivery does not replace other features' visual evidence.

## Remaining limits

See `../SETTINGS.md`: no notification delivery, bank/Google connection, verified email change, photo upload, transactional restore, account-deletion policy/workflow, approved legal content, or support destination. Financial currency remains BDT; no conversion is implied. Exports are buffered financial snapshots, not full database backups or a large-data streaming/import service. Existing dev-tool dependency advisories and the Vite chunk-size warning remain documented for a separate maintenance update.
