# FINCEPT AI — Figma-first design implementation

## Authority and scope

Read root `CLAUDE.md` before coding. Figma is the design source of truth, not a generic template or a previous screenshot-based approximation. This policy applies to every segment: Authentication, Overview, Transactions, Wallets, Budgets, Financial Goals, Insights, AI Assistant, Planner, Debt & Loans, Financial Hub and Settings. Implement only the segment authorized by the user.

Source file: https://www.figma.com/design/kpEbLoKLaLiUcB8Q6xxgRl/FINCEPT-AI?node-id=2001-5217

Authentication reference frames: Sign Up `2001:5220`; Sign In `2001:5306`. Desktop reference is 1440 × 980. Do not invent mobile or tablet variants.

## Required inspection sequence

1. Read project instructions and existing architecture before changes.
2. Identify the relevant frame URLs and inspect each through Figma MCP.
3. Inspect component masters, instance overrides, properties, variants and local/library relationships. Unpublished local components also count; published-library listings alone are not exhaustive.
4. Inspect vector paths, original image fills, text/font properties, export settings and relevant children. An empty exportSettings array does not establish that vector export is impossible.
5. Record a Figma-to-React component map and asset inventory before implementation.
6. Preserve the original design; report missing evidence rather than claiming inspection or export success.

Do not substitute a component from another segment merely because it has a similar name. Reuse it only after verifying its intended appearance/properties match.

## Vector-first asset retrieval

Use supported Figma MCP asset tools and follow their exposed schemas. Request SVG when the design requires original vectors. Check both the node export and vector asset results; prefer the isolated graphic over a render of its surrounding button/frame. If a parent export includes unrelated canvas backgrounds or text converted into paths, target the relevant vector-bearing child instead. Inspect results rather than assuming an `.svg` filename means a pure vector.

Download returned temporary URLs immediately; do not invent them or embed them in runtime code or permanent documentation. Store approved reusable assets locally under an appropriate `public/assets/` subfolder or the existing project's asset convention. Audit-only exports belong under `docs/asset-audit/` until integrated.

For each asset record:
- Source file key and node ID, original node name and role.
- Local file path, export format, viewBox/dimensions and aspect ratio.
- Whether downloaded, structurally verified, visually reviewed, and integrated (distinct statuses).
- Usage/component mapping and any documented fallback or limitation.

Validate SVG XML and actual paths, fills/strokes, viewBox, gradients, clipping and masks. Inspect for `<image>`/raster data, scripts, event handlers, external references and unexpected background/canvas objects. Preserve original geometry and colors; do not wrap PNG data in SVG and call it vector. Optimize only if fidelity is demonstrably unchanged. Use CSS sizing that retains aspect ratio and verify browser zoom behavior.

Genuine source photography/textures can stay in their original raster format. An inability to export a parent does not justify rasterizing accessible vector children. Report a genuine unavailable asset and use a faithful alternative only when necessary, documenting the limitation instead of silently replacing it.

## Real UI, not screenshot UI

Screenshots are permitted for reference and QA evidence only. They are not substitutes for screens, sections, forms, text, cards, buttons or other interface components. Never flatten editable text/vector collections into a single runtime PNG.

Use semantic React/HTML for controls and browser-rendered text, including text within financial cards and labels. Use the original SVG geometry for icons/chart paths and reusable React/DOM/vector composition for surrounding illustration cards/rings. Do not replace the original logo or invent another financial illustration.

## React component conventions

Figma components define design structure and reusable properties; they are not executable React packages. Implement faithful semantic equivalents, mapping labels, booleans and variants to typed props and state. Keep one shared component per verified design concept rather than per screen. Preserve master/instance relationships conceptually through reusable components and explicit overrides.

Current architecture: React + TypeScript + Vite, React Router, plain CSS, feature-scoped auth components and a FastAPI backend. Preserve it. Do not introduce Tailwind or a second component system without a justified task requirement. Keep reusable authentication presentation separate from validation, requests and session state.

Verified authentication map:

| Original Figma component | Node | Current React equivalent | Notes |
| --- | --- | --- | --- |
| Brand/Logo Mark | `3:18` | AuthBrand used by AuthBrandPanel and auth confirmation | Original SVG mark + live Manrope wordmark integrated |
| Input/Field | `3:23` | FormField / PasswordField | Label, Placeholder, Show eye properties; preserve real inputs |
| Button/Primary | `3:30` | PrimaryButton | Label property; preserve real button and loading state |
| Button/Social | `3:32` | SocialAuthButton | Label property; original Google SVG verified |
| Password/Strength | `3:39` | PasswordStrength | Shared four-segment presentation, dynamic state |

The authentication masters inspected here have text/boolean properties but no component-set variant definitions. Do not invent claims of named Figma hover/error variants. Existing runtime interaction/error states still require accessible behavior and documented styling. Elsewhere, actual variant sets exist (e.g. Transactions CalculatorKey State and Overview Balance Toggle); inspect them when those segments are authorized.

The illustration is editable Figma frame content, **not a single reusable COMPONENT master**. Its chart, ring, category cards, labels and icons should be composed faithfully rather than mislabeled as an imported component library.

## Verified design baseline (authentication only)

- Brand orange: #F9733B; warm main background: #F7F7F4.
- Manrope with original frame-specific weights, sizes, line heights and tracking.
- Split layout at 1440 × 980: left 749px, right 691px; auth card width 500px.
- White card surfaces, subtle borders/shadows, original radii and spacing.

These are authentication reference values, not permission to overwrite distinct tokens/layouts on other pages. Read each relevant design first. Some original colors have contrast limitations; do not claim AA compliance or silently redesign them.

## Review gate

Before calling design implementation complete, verify original asset provenance, absence of screenshot substitutions, live text/controls, shared components and variant mapping. Compare rendered desktop states with actual Figma references; check layout, font metrics, asset proportions and zoom sharpness. Run relevant tests/build and document unresolved differences honestly.

The authentication asset correction pass is now implemented: original SVG logo/chart/icons, live wordmark/cards/text and a vector ring replace the runtime PNG substitutions. See `AUTHENTICATION_ASSET_AUDIT.md` for verified runtime references, browser zoom evidence and remaining rendering limits. Legacy PNGs are retained only as unused reference assets.


## Shared sidebar

Sidebar.tsx follows original Figma sidebar 2001:5466 and its icon frames. Original vector geometry is reused locally through CSS alpha masks so route-state colors can change without duplicating SVG paths. The original SVG brand mark and live Manrope wordmark are used. The user-requested expanded state is 252px; minimized stays 76px. The toggle uses Lucide because no original sidebar toggle component was found. This is one shared layout, not separate sidebars per feature.

## Overview implementation map

Overview source frame `2001:5465` is now implemented. See OVERVIEW.md and public/assets/overview/provenance.json for inspected sections and exact icon nodes. Topbar 2001:5531 → ApplicationHeader; summaries 2001:5574 → SummaryCards; analytics 2001:5649 → CashFlowChart/CategorySpending; budgets 2001:5774 → BudgetList; insight 2001:5857 → InsightCard; goals 2001:5879 → GoalsList; recent 2001:5908 → RecentTransactions. These are reusable React translations of the original structure, not screenshot exports or claims of executable imported Figma components. Dynamic charts must show actual records rather than fixed illustrative SVG paths.

## Transactions implementation map

Read-only source: canvas `2001:7024`, desktop `2001:7034` (1440 × 1312). Inspected individual table/filter/card frames, add/edit income/expense/transfer/withdraw forms, drawers, confirmations and original component masters; see TRANSACTIONS.md.

- Desktop page → `features/transactions/Transactions.tsx`, existing ApplicationHeader/AuthenticatedLayout/Sidebar.
- TransactionModal, AmountInput, CalculatorKeypad, QuickAmountButtons, WalletSelector, CategorySelector, TransferFeeBreakdown and DateTimeSelector → shared `TransactionForm.tsx` for add/edit.
- Advanced filters/category panels → `TransactionTools.tsx` with shared native Dialog.
- Table/details/confirmation → semantic table and shared Dialog in Transactions.tsx.
- `styles/transactions.css` preserves the original desktop hierarchy, four cards, rounded panels and type colors. Internal scroll keeps short dialogs and narrow desktop tables usable. Native date/time picker rendering remains browser dependent.
- Shared authenticated interactions: 140–160ms hover/press/focus, 200ms dialog/backdrop transitions, progressive native-select popover animation and reduced-motion opt-out. Native dialogs trap focus, restore it on close and lock background scroll.

No Figma nodes were changed. Runtime UI uses actual controls and local SVGs, never screenshots. Original reference exports and actual browser screenshots are in `docs/transactions-qa/`. Available Figma MCP inspection/export operations were used; separate figma-use/design-to-code skill resources were unavailable in the execution environment and were not claimed as loaded.

## Calendar/category correction

The native date picker and inline category-create field from the initial Transactions delivery are superseded by the original `DateTimeSelector` (`230:4953`) and Create custom category (`2001:32339`) translations. See CALENDAR_CATEGORY_CORRECTION.md. Their styles are feature-scoped in transaction-corrections.css; the rest of the product is unchanged. Category creation now persists original icon/color choices in additive presentation metadata. Existing names, financial records and accounting rules are preserved.


## Financial Insights & Analytics component map

Source: Figma `kpEbLoKLaLiUcB8Q6xxgRl`, page `2001:7028`; originals and state references in `insights-qa/`. `Insights` reuses the authenticated shell, not a parallel layout. `SummaryCards` maps the four 140px cards; `IncomeExpenseChart` maps `2001:81316` with native focusable grouped bars; `CategoryDonut` maps `2001:81372` with live SVG segments and category buttons. `SpendingTrends`, `IncomeSources`, `SavingsProgress`, `BudgetPerformance`, `AiInsights` implement the remaining sections; `InsightsDialogs` owns range/category/export variants. Current real backend data overrides illustrative sample numbers and AI findings.

Original colors: #20211F text, #777873 muted, #E9E8E3 border, #F9733B primary, #FFF0E8 peach, #258358 positive, #EEEDE8 tracks. Cards r20, buttons r12/h44, heading 30/45/800, section headings 22/33/800, card headings 18/27/800. Category palette and original six 18px vectors are recorded in `ASSETS.md`. UI uses shared `Money` masks instead of introducing a second privacy convention.

Wide desktop: four summary cards, proportional 760:520 primary split, three trend/budget cards, two secondary columns. Available-content container thresholds 1180px and 900px preserve the same desktop components with both sidebar states. Button/plot 160ms, dropdown 150ms, dialogs 200ms, reduced-motion overrides; no mobile-specific design is claimed. Budget dates/scope and current savings dates remain visible so unlike financial scopes are never mixed.


## AI Assistant map — 2001:7029

Read-only inspection covered Welcome/Conversation/History/Generation Failure plus nested masters: ChatHeader125:19669, SuggestedQuestionCard125:19681 (hover125:29066), MessageComposer125:19688, AI/User messages125:19695/19702, FinancialSummaryCard125:19705, TypingIndicator125:19717, ChatErrorState125:19723 and ConversationHistory125:19729. Reuse the existing shell/header/sidebar, local Manrope and global privacy. The original orange #F9733B, off-white #F7F7F4, border #E9E8E3, white and peach #FFF0E8 are preserved. Header title28/800, welcome26/800, cards/messages14/500–700; 44px actions, 16px message/question radii, 14px composer/summary radii, 20px workspace/history radii. Assistant orange-button text follows the inspected dark text without changing previous pages. Original sparkle SVGs are local; no screenshot UI. The four exact Figma suggestion questions populate the composer. Truthful live configuration/history/calculation labels replace illustrative sample-state assertions. All free-form financial prose is conservatively concealed under the shared privacy preference. See ASSISTANT.md and assistant-qa screenshots for viewport adaptations, motion and documented differences.

## Planner implementation map
Planner page `2001:7030`, main frame `2001:89823`, masters `2001:97310` were inspected read-only, including task/plan forms and state frames. `styles/planner.css` preserves this feature's five100px summary cards, 900:380 calendar/agenda split with20px gap, r16 panels,84px minimum date cells and r20 scrollable dialogs. Source tokens remain Manrope/#F9733B/#F7F7F4/#20211F. Narrow **desktop** containers stack agenda when needed; no mobile redesign. Shared shell, global Money privacy, Dialog and DateTimePicker remain authoritative. Actual saved records replace Figma sample data; unavailable reminder controls are explicitly disabled. Four status scopes match the reference; cancelled records remain discoverable under All. Hover/pressed/month transitions are scoped and reduced-motion aware. See PLANNER.md and planner-qa for evidence and disclosed limitations.

## Settings implementation evidence and exception

Settings uses real reusable category navigation, profile summary, labeled form controls, switches, notification groups, integration/danger cards, notices and the shared native dialog. Colors, Manrope, spacing conventions and local vectors are reused from existing tokens/shell. Settings-specific Figma frame/component inspection was unavailable, so neither exact variant mapping nor pixel fidelity is claimed. The user requested proceeding after this was disclosed. `settings.css` supports the requested desktop/narrow widths within this segment; other screens retain their designs. See `SETTINGS.md` and generated `settings-qa/` screenshots for scope and verification.
