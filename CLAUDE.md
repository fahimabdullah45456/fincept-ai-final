# FINCEPT AI — Project instructions

## Mandatory preflight for every implementation task

Read this file and `docs/DESIGN_SYSTEM.md` **before coding**. Then inspect the existing project structure, dependencies, routing, styling, shared components, backend, tests, and relevant implementation status. Preserve working code and unrelated instructions. If a tool/agent does not automatically load CLAUDE.md, explicitly load it before work; this file is the project convention, not a guarantee of enforcement by every external tool.

Implement one explicitly requested segment at a time. Authentication, the shared application shell, the read-side Overview, full-stack Transactions, Wallets, Budgets, Financial Goals, Financial Insights & Analytics, and AI Financial Assistant segments are implemented. Read `docs/TRANSACTIONS.md` before extending transaction writes: preserve integer minor units, ownership/dataset isolation, atomic transfer fees, optimistic versions, idempotency receipts and ledger overdraft checks. Do not start other segments without the user's next instruction. Current design scope is desktop only; do not introduce mobile/tablet layouts or mobile bottom sheets unless the user changes that scope.

## Figma is the source of truth

Project: https://www.figma.com/design/kpEbLoKLaLiUcB8Q6xxgRl/FINCEPT-AI?node-id=2001-5217

Before implementing any page or component, inspect its actual Figma frame, component masters/instances, properties, variants, assets, typography and layout using the configured Figma MCP integration. Inspect individual target frames, not only the canvas or screenshots. Inspect the relevant library/local components before creating new React components. Follow available integration guidance; report unavailable tools or guidance honestly. Never claim a frame was inspected or an asset extracted without evidence.

Preserve original colors, typography, spacing, dimensions/proportions, borders, radii, shadows, icons, illustration placement and layout relationships. Do not redesign by preference or approximate a design when its original assets/properties can be accessed. Respect each segment's distinct designs rather than substituting assets from a different segment.

## Vector-first, original-asset policy

1. Inspect original structure and identify vector layers, text, reusable components and original image fills.
2. Prefer original Figma SVG assets for logos, icons, illustrations, chart geometry and decorative graphics when available.
3. Retrieve them through supported Figma asset/export capabilities. Inspect tool schemas. If the main export is null or raster, check returned SVG assets and target vector-bearing children. Never invent asset URLs.
4. Download temporary URLs promptly and store approved runtime assets locally. Record file key, node ID, original name, format, dimensions/viewBox and usage in `docs/ASSETS.md`.
5. Validate SVG content: preserve paths, colors, proportions, viewBox, gradients and clipping. Reject raster images wrapped in SVG, unexpected scripts, event handlers or external dependencies. Do not distort or replace the FINCEPT logo.
6. Report unavailable assets/export limitations. Only use a faithful fallback when necessary, explicitly identifying the exception and obtaining clarification if it materially changes the design. Do not silently downgrade an accessible vector to PNG.

**Never use screenshots or whole-screen/section raster exports as substitutes for UI components.** Do not flatten editable vector/text collections into a PNG. Do not redraw available original assets unnecessarily. Genuine original photographs/textures may stay raster; that is not permission to rasterize vector UI. Screenshots are for reference/visual QA only, not runtime interface implementation.

## Reusable component implementation

Implement real labels, text, inputs, buttons, checkboxes, dropdowns, cards, navigation, forms, modals and dialogs as semantic React/HTML components with browser-rendered text. Figma components are design definitions, not executable React code: translate their structure and properties into reusable components without claiming a Figma instance was directly imported as working code.

Map component variants to typed props/state; reuse shared components across screens. Keep segment-specific components separate from global components. Do not duplicate whole layouts or unrelated files for variants. Financial illustration cards, labels and ring should remain reusable React/DOM/vector elements; reuse the original chart/icon SVGs within them rather than exporting all text and cards as one image. Preserve exact available font identity/weights; load locally where possible and keep font licenses.

Follow the existing architecture: React + TypeScript + Vite, React Router, plain CSS, authentication feature folder, FastAPI backend. Do not assume Tailwind or add a parallel UI system. Keep presentation separate from requests, validation and auth state. Preserve authentication/security logic unless the task explicitly calls for a logic change.

## Verification and handoff

Check original/implemented desktop layouts side by side; inspect spacing, typography, assets, aspect ratios, component states and browser zoom sharpness. Run relevant tests/build checks after runtime changes. Record tests actually performed and unresolved exceptions in `docs/IMPLEMENTATION_STATUS.md`. Update asset provenance when assets change. Do not call an implementation vector-compliant while known raster substitutions remain.

These rules apply to Authentication, Overview, Transactions, Wallets, Budgets, Financial Goals, Insights, AI Assistant, Planner, Debt & Loans, Financial Hub and Settings.

## Authentication asset correction status

The original logo/chart/icon SVGs are now integrated under `public/assets/auth/`; the Google SVG remains unchanged. AuthBrand renders the original vector mark and live Manrope wordmark. AuthFinancialIllustration composes live cards/text, original SVG chart/icons and a vector ring. FormField uses the original password-eye SVG while retaining its existing visibility state and accessible labels. The two legacy PNGs remain in the repository as reference assets but have no application-source references. See `docs/AUTHENTICATION_ASSET_AUDIT.md` and `docs/IMPLEMENTATION_STATUS.md` for actual verification, minor rendering differences and the completed correction pass. Future changes must retain these reusable implementations rather than reintroduce raster substitutions.


## Shared sidebar and combined delivery

This project combines the vector-corrected Authentication version with the shared sidebar. Reuse src/components/layout/AuthenticatedLayout.tsx as the persistent parent and Sidebar.tsx/navigation.ts for every authenticated route. Expansion state belongs only to that parent. Do not recreate sidebars in feature pages. The sidebar uses original local Figma icon/brand SVGs, a 76px collapsed rail, 252px expanded rail and non-sensitive localStorage persistence. Overview now uses the real component at src/features/overview/Overview.tsx and canonical read APIs under backend/app/finance. Transactions, Wallets, Budgets, Financial Goals, Insights, AI Assistant, Planner, Debt & Loans, Financial Hub and Settings are implemented. Preserve explicit unavailable states for operations lacking safe infrastructure. Reuse the canonical wallets/transactions/budgets/goals schema in future segments, not duplicate dashboard records. Preserve corrected authentication components, local font fallback and vector assets. See docs/COMBINED_PROJECT.md and docs/ARCHITECTURE.md.

## Overview invariants

Read docs/OVERVIEW.md before changing financial presentation or accounting. Preserve owner/dataset isolation, integer minor-unit storage, ledger-based balances, transfer-principal exclusion, single fee expenses, real empty states and explicit development-only sample separation. All monetary text, axes, tooltips and accessible labels must respect the shared privacy preference. Preserve original SVG assets/provenance and reuse the shared layout. Do not claim future CRUD/AI/notification services are connected.

## Wallets invariants

Wallets is implemented; read docs/WALLETS.md before further financial work. Reuse backend/app/finance/ledger.py for balances; do not introduce parallel mutable balance totals. Preserve additive v5 metadata/events, original canonical transactions, explicit Add Money classification, Savings counted once, active/archive rules, optimistic versions and idempotency. Internal transfers never create income/expense. Opening balances and external/adjustment events are not income. Keep financial operations atomic, owner/dataset isolated and privacy synchronized with the shared layout. View Transactions reuses the existing route; combined audit activity is in Wallet Details.

## Budgets invariants

Read docs/BUDGETS.md before changing budget logic. Reuse canonical budgets plus additive v6 budget_metadata, and budget_service.evaluate for both Budgets and Overview. Integer categorized expenses only; exact category/date matching, inclusive periods, no income/transfer principal/wallet events. Prevent overlapping same-category writes atomically; flag/exclude ambiguous imported matches rather than double-counting. Preserve transaction history on plan deletion. Risk uses configured thresholds (default 75%), Near Limit starts at 85%, Exceeded is strictly over 100%. Saved Weekly/Monthly/Custom periods do not imply a recurring scheduler. Keep version/idempotency/ownership/CSRF rules and global monetary privacy. Do not redesign previous pages.

## Financial Goals accounting boundary

Read `docs/GOALS.md` before extending goals. Goals are allocations of wallet funds, not additional assets. Preserve immutable contribution history, owner/dataset scoping, active-only shared summaries, versioned/idempotent reviewed commands and atomic external deposit+allocation. Do not classify contributions as income. Schema v7 is additive; retain legacy unlinked funding honestly. Earmarks are not hard locks on later spending; display shortfalls instead of fabricating backing.


## Insights accounting and presentation boundary

Read `docs/INSIGHTS.md` before extending analytics. Reuse canonical transactions and shared period/budget/goal helpers; integer minor units, owner/dataset isolation, transfer-principal exclusion and single fee expenses remain mandatory. Never fabricate comparisons against zero or relabel sample income as unrecorded sources. Filters use inclusive calendar dates; last three months includes the current month. Budget spending is range-intersected versus full, unprorated limits; current goal allocations are explicitly dated snapshots, not period savings or new assets. No AI findings without a real configured provider. Preserve privacy in money/axes/tooltips/aria/dialogs and export previews; masked CSV hides monetary columns. CSV text must remain quote-safe and formula-injection-safe. Keep native, keyboard-accessible dialogs and reduced motion.


## AI Assistant boundary

Read `docs/ASSISTANT.md` before modifying chat. Reuse `backend/app/assistant` provider/context/routes/schema, owned SQLite conversations/messages/requests and the shared app shell/privacy. Additive app migration v8 must preserve all canonical finance rows. No production test doubles or fake replies. OpenAI configuration is server-side only (`AI_PROVIDER`, `AI_MODEL`, `OPENAI_API_KEY`); missing configuration must not break other pages. The user explicitly requested an actionable agent: preserve native allowlisted read tools and proposal-only mutation requests; only a separate authenticated, owner/dataset/version-bound confirmation can execute canonical finance commands. Read docs/AI_ACTIONS.md. Additive v12 approval schema follows Settings v11. No arbitrary SQL/code, direct model writes, chat-message approval or production test doubles. Use existing period/Insights/ledger/budget/goal calculations, bounded relevant owner/dataset facts and completed history. Preserve stable request IDs, failed-request retry, concurrency fencing and no open DB transaction across provider calls. UI text is escaped, never raw HTML; global privacy conceals full free-form messages and previews in addition to structured Money. The opt-in real-provider test requires credentials; do not describe test doubles as live-model verification.

## Planner boundary
Planner — Calendar & Tasks is implemented at `/planner`; read `docs/PLANNER.md` before extending it. Preserve v9 additive migration, civil dates/wall-time metadata, owner/dataset relationships, idempotency/versions and canonical Financial Goals allocation IDs. Completing a task is never a transaction; planned contributions are not automatic transfers. Reminder delivery remains unavailable. Keep the original five summary meanings and explicit global-vs-filtered scope. No fabricated calendar entries or saved balances.

## Debt & Loans and Financial Hub boundary
Debt & Loans and Financial Hub are implemented at `/debt-loans` and `/financial-hub`. Read `docs/DEBT_LOANS.md` and `docs/FINANCIAL_HUB.md` before extending either. Additive v10 owns debt/payment and purchase-planning tables. Debt/EMI payments are explicitly tracking-only: no automatic wallet movements, income/expense or external transfers. Preserve fixed-total interest, principal separation, immutable reversal history, civil-date schedules, settled-only archive, versions and idempotency. Hub reads canonical active Wallets; never duplicate balances or add earmarks. Purchased shopping items are not transactions; unknown actual cost is not zero. FX is server-proxied ExchangeRate-API Open Access with attribution, genuine provider timestamp, one-hour cache and explicit ≤48-hour stale fallback. No fabricated rates or reminder delivery. Retain shared monetary privacy and original Figma SVGs.

## Settings boundary (v11)

Settings is now implemented within the existing shell. Read `docs/SETTINGS.md` before extending it. Preserve local shared monetary privacy, server-owned versioned preferences, read-only BDT currency and verified-email limitation, Argon2 reauthentication/session rotation, owner-scoped export allowlists and transactional demo-only clearing. Exports contain unmasked original values after a disclosed review; they are not full/restorable backups. Do not enable fake notification delivery, third-party connections, restore, account deletion or final legal/support destinations. Settings Figma inspection was unavailable for this implementation and exact fidelity remains unverified. The user's Settings request explicitly adds narrow/tablet responsiveness; these overrides are Settings-scoped, not a redesign of prior desktop-only segments.
