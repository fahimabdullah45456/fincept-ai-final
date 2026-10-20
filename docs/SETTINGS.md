# Settings

## Scope and design evidence

Settings is integrated into the existing React Router shell at `/settings` (redirects to `/settings/profile`) with seven URL-based categories: Profile, Privacy & Security, Notifications, Financial Preferences, Connected Services, Data & Account, and Help & About. Nested URLs support browser back/forward, direct links, and the existing sidebar active state.

The supplied Figma file/node `2001:7033`, including Profile `2001:130745`, could not be inspected: page loading returned unavailable and no Figma MCP/Codex integration was present. After the user requested proceeding, implementation was performed directly in the supplied repository, using the written requirements, Manrope, existing tokens and shell. Exact Figma layouts, category labels beyond the supplied brief, component variants, and Settings-specific icon matching remain **unverified**, not claimed pixel-identical. No Figma file was modified. Screenshots in `docs/settings-qa/` show implementation evidence only, not Figma comparisons.

## Setup and migration

Use the existing README setup: `npm ci`, the backend's `requirements-dev.txt`, existing FastAPI startup and Vite commands. No new dependency or environment variable is required. Startup applies additive schema **v11**: `user_settings(user_id, preferences_json, version, updated_at)`. Back up an existing deployed database and preserve your `.env` before upgrading. Existing canonical ledger rows, users, authentication, sessions, accounting and datasets are retained.

- Authenticated identity comes only from the existing cookie-session dependency. No request can select a user ID for writes.
- Existing origin checks, `X-Fincept-Request: 1`, safe validation responses and Argon2 hasher are reused.
- `user_settings.user_id` references the existing `users` table. There is no duplicate user model, auth client, or ledger.

## Category behavior

### Profile

Reads `AuthProvider.user`. Display-name updates normalize whitespace, validate 2–100 characters server-side, persist to `users.full_name`, and update the shared auth context immediately without unmounting the route or reloading the document. Cancel resets unsaved fields. Initials are derived from the signed-in user's name. Avatar uploads are not supported by the current schema. Email is explicitly read-only because a verified email-change workflow is not implemented.

### Privacy & Security

The Settings switch calls the same `ApplicationPreferences.toggle` as the header. The non-sensitive `fincept.money.hidden` preference remains browser-local and synchronous, including across account navigation/refresh. Storage events synchronize other tabs in the same browser. If browser storage is blocked, the active in-memory choice still works and Settings explains the persistence limitation. No separate server money-privacy switch is created.

Real password changes verify the existing password through the existing Argon2 hasher, enforce the existing strength policy, hash the replacement, revoke all sessions, and issue a fresh current-browser cookie in one database transaction. The current browser is renewed with the normal eight-hour session policy (or configured `SESSION_HOURS`), not a new remembered session. Incorrect passwords do not change anything. Security commands share a persisted rate-limit bucket.

Session information shows a real active-session count and current-session expiry, not invented device/IP information. Sign Out Other Sessions requires the current password and preserves the current session. No password/hash/token appears in public security responses. Two-factor authentication is explicitly unavailable.

### Notifications

Budget alerts, goal updates, payment reminders, and product updates can be stored as account preferences. The screen prominently states that **email, push, and reminder delivery do not exist**. Saving these desired preferences neither sends notifications nor installs a scheduler. The groups are based on the written scope, not verified Figma field inspection.

### Financial Preferences

BDT is read-only because canonical wallet writes currently support BDT only. Account preferences control thousands grouping and flexible/up-to-two versus fixed-two decimal display. The shared `Money` component, Overview/Insights chart axes and accessible amounts, and wallet/transaction selectors consume the same formatter. Amount input editing and calculations remain unchanged, and no record is converted, rounded, or rewritten. The Financial Hub's FX tool remains separate. There is no unsupported account currency switch or date preference that silently does nothing.

Account preference writes use an expected version and `BEGIN IMMEDIATE`: concurrent stale writes return 409 rather than overwriting another save. Save controls are locked while saving. Failed saves retain edits and show errors; a conflict offers an explicit reload/discard option. Initial load failures show retry rather than presenting fabricated defaults as a successful fetch.

### Connected Services

Google sign-in is not configured and no bank-linking provider is implemented. These statuses agree with the existing auth config and backend capabilities; no random/connected state or fake OAuth flow is created. Connect actions are unavailable with explanations. Refresh asks the backend again. Manual wallets are not misrepresented as provider connections, and financial records are never removed by connection controls.

### Data & Account

**Real exports:** only the authenticated user's selected `live` financial rows. Scope may be all supported financial data, transactions, wallets/events, budgets, or goals/contributions. CSV downloads are ZIP archives with one properly quoted UTF-8-BOM CSV per allowlisted table and `manifest.json`; JSON downloads contain `{manifest, data}`. All-table exports additionally include custom categories, Planner, Debt & Loans, and Financial Hub shopping records. Metadata joins are constrained through owned parent records. A single read transaction keeps the export consistent. Empty tables retain column headers.

CSV text reuses the shared formula-injection safety helper; commas, quotes and newlines are written through Python's CSV writer. Numeric minor-unit values remain numeric. The manifest identifies generation time, dataset, scope, per-table counts, format/schema versions, original minor-unit amounts, and exclusions. CSV neutralization may prefix an apostrophe on unsafe string cells; JSON retains original strings. Exports exclude credentials, password hashes, sessions, idempotency receipts, AI conversations and account preferences. An export is **not** a full account/database backup.

Exports intentionally contain original **unmasked** values. A mandatory UI review discloses this even when monetary privacy is active. The export endpoint is authenticated, but like existing download endpoints does not require a password; review is a UI consent step, not a server reauthentication claim. Backend `dataset=demo` export is allowed only outside production; the Settings UI never mixes demo and live exports.

**Financial snapshot:** JSON export is a real financial snapshot, explicitly not restorable in this version. No restore button pretends to upload/import data. There is no restore API, importer, duplicate policy or partial-success simulation. Full database backup is an administrator/deployment responsibility outside this UI.

**Clear Demo Data:** available only outside production. Requires the exact text `CLEAR DEMO DATA` on the server and in the confirmation dialog. In a single transaction, deletes only rows with the current owner's explicit `dataset='demo'` classification, including owned child metadata, sample finance, Planner, Debt/Hub and Assistant history. A pending sample AI request prevents clearing. Foreign-key dependency order is respected; failures roll back. Live records and other users remain intact. Unscoped idempotency receipts are retained rather than guessed to be demo. Repeating a completed clear honestly returns zero counts. This does not disable the existing development Explore sample data action, which can create a new explicit sample workspace later.

**Delete Account:** explicitly unavailable. No reviewed account-retention/deletion policy or complete deletion pipeline is present. No endpoint or frontend simulation is added. Provider deletion, anonymization and permanent account removal require a separately reviewed implementation.

### Help & About

Help Center opens real in-app guidance. FAQs use accessible native disclosures and contain answers grounded in the application's implemented behavior. About reads the real package version (`0.1.0`), not an invented release number. Support has no configured address, and the existing `/terms` and `/privacy` documents are unpublished development drafts: the UI clearly identifies these limitations rather than inventing a destination or presenting draft legal content as final.

## API contracts

All endpoints require the existing signed-in session; mutations require existing CSRF headers.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/settings` | Account preferences/version and genuine capability/integration limitations |
| PATCH | `/api/settings/profile` | `{full_name}`; returns public user |
| PATCH | `/api/settings/preferences` | `{notifications, financial, version}`; returns saved preferences/version; stale version is 409 |
| GET | `/api/settings/security` | Real active-session count and current expiry only |
| POST | `/api/settings/password` | `{current_password, new_password, confirm_password}`; hash update, session revocation and renewal |
| POST | `/api/settings/sessions/revoke-others` | `{current_password}`; returns actual revoked count |
| GET | `/api/settings/export?format=csv\|json&scope=all\|transactions\|wallets\|budgets\|goals&dataset=live\|demo` | Authorized financial export; no underlying amounts change |
| POST | `/api/settings/demo/clear` | `{confirmation:"CLEAR DEMO DATA"}`; transactional owner/sample-only cleanup |

There is deliberately no restore or delete-account endpoint. Unknown/extra mutation fields (including an attempted user ID or email change) are rejected, and sensitive validation inputs are never echoed.

## Frontend integration and accessibility

`src/features/settings/Settings.tsx`, `components.tsx`, `api.ts` and `src/styles/settings.css` own the segment. Existing sidebar/header, protected routes, native Dialog, local Icon assets and auth/preferences providers are reused. Settings-scoped responsive rules do not redesign other feature screens. Buttons, switches, selects and inputs have accessible names, visible focus and busy/disabled states. Native dialogs trap focus, block the background, close on Escape when safe, and prevent closing during consequential requests. The shared Dialog now supports optional initial focus and restores focus to a still-mounted trigger. Motion respects reduced-motion.

## Verification

See `docs/settings-qa/README.md` and `docs/IMPLEMENTATION_STATUS.md` for executed commands, results and outstanding limitations. Automated browser tests create real disposable test accounts against the local backend; these are test fixtures, not production sample identity or frontend success simulations.
