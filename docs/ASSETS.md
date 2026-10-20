# Local asset provenance — current runtime

Figma source: https://www.figma.com/design/kpEbLoKLaLiUcB8Q6xxgRl/FINCEPT-AI?node-id=2001-5217

Reference frames: Sign Up `2001:5220`; Sign In `2001:5306`.

## Original SVGs integrated

The following six original SVGs were promoted byte-for-byte from `docs/asset-audit/` into `public/assets/auth/`, without retrieving them again:

| File | Original node | viewBox | Component |
| --- | --- | --- | --- |
| `logo-mark.svg` | `3:18` Brand/Logo Mark | 0 0 38 38 | AuthBrand |
| `savings-chart.svg` | `2001:5242` Savings Line | 0 0 324 96 | AuthFinancialIllustration |
| `housing-icon.svg` | `2001:5253` vector frame | 0 0 18 18 | IllustrationCategoryCard |
| `wallet-icon.svg` | `2001:5260` vector frame | 0 0 18 18 | IllustrationCategoryCard |
| `groceries-icon.svg` | `2001:5269` vector frame | 0 0 18 18 | IllustrationCategoryCard |
| `password-eye.svg` | `3:27` Icon/Eye | 0 0 20 20 | FormField / PasswordField |

`public/assets/google.svg` remains the unchanged original Google asset from component `3:32` (icon subtree `3:33`), viewBox 0 0 18 18. Its paths/fills previously matched a fresh export. It is used by the actual SocialAuthButton. No OAuth configuration is implied.

All six promoted SVG files were parsed and checked for embedded raster, scripts, event handlers and external hrefs. Their original paths, colors, gradients and viewBoxes are unchanged. Rendered aspect ratios match original bounds. Runtime references were verified in both actual pages at native browser zoom 100%, 125% and 150%.

## Live geometry and text

FINCEPT wordmark: browser-rendered Manrope Bold 23px, line box 31px, tracking 1.5px, 10px gap from the original 38px logo mark, matching node `2001:5227`.

AuthFinancialIllustration composes frame `2001:5234` using HTML/CSS cards, live labels/amounts/disclaimer, original chart/icon SVGs and a 64px SVG annulus (78% inner radius, 75% arc) derived from the original ellipse geometry. It does not contain the old PNG or raster data embedded in SVG.

## Fonts and licensing

Manrope is bundled locally from `@fontsource-variable/manrope`; `docs/licenses/Manrope-OFL.txt` contains its SIL OFL license. Manrope has no U+09F3 taka character. Only that character is provided by a local variable-font subset at `public/assets/fonts/fincept-taka.woff` (2,404 bytes), family alias FINCEPT Taka, Unicode range U+09F3. Original source font: Google Fonts `ofl/notosansbengali/NotoSansBengali[wdth,wght].ttf`; license: `docs/licenses/NotoSansBengali-OFL.txt`. This is a documented glyph fallback, not a font extracted from Figma or a change to Latin typography. The fallback may have slightly different currency metrics from Figma's unspecified fallback.

Lucide remains a dependency for unchanged loading/check icons; the default password-eye icon no longer uses a Lucide substitute. Brand/illustration/icon rights remain with their respective owners; no new asset ownership is asserted.

## Retained legacy/reference assets

`public/assets/fincept-brand.png` is the previous Figma logo/wordmark render. `public/assets/auth-financial-illustration.png` is the previous isolated illustration render. These PNGs are retained as legacy reference files, but neither is referenced anywhere in `src/` or requested by the authentication pages. No unrelated assets were deleted.

`docs/figma-*.png` are original reference captures. `docs/rendered-*.png` and `docs/asset-correction-zooms/*.png` are QA captures, not runtime UI. No temporary Figma URL appears in application runtime code. See `AUTHENTICATION_ASSET_AUDIT.md` for verification and remaining fidelity limits.

## Shared sidebar — integrated vector assets

Source file `kpEbLoKLaLiUcB8Q6xxgRl`, Overview sidebar `2001:5466`.
Original sidebar inspected read-only with Figma MCP: 76px white rail, #E9E8E3 border, 44px navigation targets, 14px radii, 8px gaps, #777873 default icons and #F9733B / #FFF0E8 active state. Brand instance points to original master `3:18`.

The twelve SVGs below were retrieved with `download_assets`, downloaded locally and parsed/validated: no images/raster wrappers, scripts, event handlers, foreignObject or external dependencies. Downloads required curl after empty urllib responses. Geometry/viewBoxes remain unchanged. All are actually integrated, and rendered sidebar states were visually reviewed. Navigation SVGs are used as alpha masks with CSS currentColor to support active/inactive colors without duplicating geometry; the brand is a normal SVG image with live Manrope wordmark. No temporary asset URLs are used at runtime.

| Runtime asset under `public/assets/sidebar/` | Original node | Size |
|---|---|---|
| logo-mark.svg | `2001:5468` → master `3:18` | 38×38 |
| overview.svg | `2001:5470` | 22×22 |
| transactions.svg | `2001:5476` | 22×22 |
| wallets.svg | `2001:5482` | 22×22 |
| budgets.svg | `2001:5487` | 22×22 |
| financial-goals.svg | `2001:5491` | 22×22 |
| insights.svg | `2001:5496` | 22×22 |
| ai-assistant.svg | `2001:5500` | 22×22 |
| planner.svg | `2001:5503` | 22×22 |
| debt-loans.svg | `2001:5509` | 22×22 |
| financial-hub.svg | `2001:5515` | 22×22 |
| settings.svg | `2001:5527` | 20×20 |

No sidebar expand/collapse master was found among corresponding Overview page components. The toggle therefore uses permitted Lucide `PanelLeftOpen` / `PanelLeftClose`. Expanded width 252px and expanded label treatment implement the user's new behavior; they are not claimed to be an exported original expanded Figma variant. No Figma content was changed. The Figma use skill resource was not exposed by this connection; supported read-only Plugin API queries and asset export were used.

## Integrated Overview original SVGs

23 supported Figma SVG exports are stored in public/assets/overview/. Exact source node IDs and viewBoxes: public/assets/overview/provenance.json. Names: search, ai, bell, chevron, calendar, plus, wallet, income, expense, percent, food, transport, shopping, entertainment, right, view, edit, trash, work, home, left, privacy-visible, privacy-hidden. XML checked: no raster images, scripts, foreignObject or external dependencies. ApplicationHeader and Overview cards/table use these original paths through CSS masks, with state colors. Existing original sidebar budgets/financial-goals icons are reused for their matching quick actions. Dynamic chart geometry is scalable SVG computed from real data, not a flattened Figma screenshot. All card labels/amounts are browser text. No temporary asset URL is used at runtime.

## Original Transactions SVG assets

Source file remains `kpEbLoKLaLiUcB8Q6xxgRl`; read-only Figma `exportAsync` SVG exports, local under `public/assets/transactions/`. Machine-readable node names, dimensions and source IDs are in `provenance.json`.

| File | Source node | Use |
|---|---|---|
| download.svg | 2001:7133 | Export |
| list.svg | 2001:7193 | Total Transactions card |
| sort.svg | 2001:7242 | Sorting |
| more.svg | 2001:7309 | Row details |
| cart.svg | 2001:7283 | Grocery row icon |
| calculator.svg | I2001:9343;227:86247 | Calculator toggle |
| clock.svg | 2001:9321 | Time field |
| swap.svg | 2001:10126 | Swap transfer wallets |
| transfer.svg | 2001:7456 | Transfer rows/details |
| backspace.svg | 2001:9265 | Original Figma ⌫ text glyph exported as vector outlines, replacing a missing runtime-font glyph |

Original geometry/viewBoxes are retained. Icons use CSS masks to match current state colors. All ten SVG files were XML-parsed and checked for embedded images, scripts, event handlers and external references. Existing Authentication, Overview and navigation SVGs are reused without new exports. PNGs in transactions-qa are reference/verification evidence only, not runtime page backgrounds.

## Calendar/category follow-up

Original category icon vectors under `public/assets/categories/`: receipt `2001:32355`, wallet `2001:32358`, calendar `2001:32361`, plus `2001:32364`, clock `2001:32367`, check `2001:32370`. All are original read-only SVG exports with a 22 × 22 viewBox, parsed and validated (no raster, scripts, event handlers or external references), integrated into CreateCategory and the custom category-list appearance. Original category icon/color selection UI is live DOM. DateTimePicker reuses existing calendar/clock/chevron assets around a live calendar grid. Source mapping and reference/actual screenshots: CALENDAR_CATEGORY_CORRECTION.md and ui-correction-qa/. No Figma modifications.

## Wallets original vector exports
Source: kpEbLoKLaLiUcB8Q6xxgRl, page 2001:7025. Read-only export; validated XML, no raster/script/external references; used as currentColor masks.
- `2001:58332` Icon/plus → `public/assets/wallets/plus.svg`, original viewBox 18 × 18.
- `2001:58337` Icon/dl → `public/assets/wallets/dl.svg`, original viewBox 18 × 18.
- `2001:58343` Icon/swap → `public/assets/wallets/swap.svg`, original viewBox 18 × 18.
- `2001:58353` Icon/wallet → `public/assets/wallets/wallet.svg`, original viewBox 18 × 18.
- `2001:58364` Icon/bank → `public/assets/wallets/bank.svg`, original viewBox 18 × 18.
- `2001:58378` Icon/phone → `public/assets/wallets/phone.svg`, original viewBox 18 × 18.
- `2001:58389` Icon/cash → `public/assets/wallets/cash.svg`, original viewBox 18 × 18.
- `2001:58416` Icon/sort → `public/assets/wallets/sort.svg`, original viewBox 16 × 16.
- `2001:58425` Icon/grid → `public/assets/wallets/grid.svg`, original viewBox 16 × 16.
- `2001:58431` Icon/list → `public/assets/wallets/list.svg`, original viewBox 16 × 16.
- `2001:58463` Icon/right → `public/assets/wallets/right.svg`, original viewBox 14 × 14.
- `2001:58602` Icon/info → `public/assets/wallets/info.svg`, original viewBox 14 × 14.

Additional original Wallet vectors (same Figma file): `2001:58451` Icon/kebab → `public/assets/wallets/kebab.svg` (16×16); `2001:58566` Icon/target → `public/assets/wallets/target.svg` (22×22). Read-only SVG exports, XML-validated, preserved original circles/colors/viewBox; integrated into wallet actions and Savings cards. No screenshots used as runtime UI.

## Budgets — original vectors

Read-only inspection of page 2001:7026, desktop 2001:71662, form/filter/detail frames and handoff 2001:75114. Exported with the Figma node SVG exporter, then parsed to reject raster images, scripts, foreign objects, event handlers and external hrefs. Original geometry/viewBoxes are unchanged; rendered as the existing currentColor Icon masks. No Figma writes.

| Local `public/assets/budgets/` file | Source node | Native size | Use |
|---|---|---|---|
| plus.svg | 2001:71761 | 18×18 | Create action |
| budget.svg | 2001:71768 | 18×18 | Total/at-risk and fallback category |
| up.svg | 2001:71776 | 18×18 | Spent |
| wallet.svg | 2001:71784 | 18×18 | Remaining |
| search.svg | 2001:71812 | 18×18 | Search |
| food.svg | 2001:71825 | 20×20 | Food/Dining |
| bag.svg | 2001:71845 | 20×20 | Shopping |
| car.svg | 2001:71865 | 20×20 | Transportation |
| home.svg | 2001:71886 | 20×20 | Bills/Utilities/Housing |
| film.svg | 2001:71904 | 20×20 | Entertainment |
| health.svg | 2001:71923 | 20×20 | Health |

Shared logo, sidebar, kebab, chevron and calendar icons retain their existing original assets. Reference PNGs under docs/budgets-qa are audit-only. Budgets desktop and creation form were visually compared with the downloaded source references; browser text and controls remain real DOM.

## Financial Goals — original SVG exports

Read-only source page `2001:7027`, desktop `2001:75706`, associated dialogs and handoff `2001:80375`. Nine node SVGs were exported and checked for valid vector-only geometry, no raster wrapping, scripts, event handlers or external dependencies. Original viewBoxes/geometry remain unchanged; shared Icon uses currentColor masks. Hashes are retained in `goals-qa/assets.json`. No Figma modifications.

| Local `public/assets/goals/` | Figma node | Native size |
|---|---|---|
| plus.svg | 2001:75805 | 18×18 |
| target.svg | 2001:75812 | 18×18 |
| wallet.svg | 2001:75820 | 18×18 |
| up.svg | 2001:75828 | 18×18 |
| search.svg | 2001:75856 | 18×18 |
| shield.svg | 2001:75869 | 24×24 |
| laptop.svg | 2001:75896 | 24×24 |
| travel.svg | 2001:75923 | 24×24 |
| phone.svg | 2001:75949 | 24×24 |

Existing original shared logo/sidebar/calendar/chevron and Wallets kebab are reused. Source reference and implementation PNGs in goals-qa are visual evidence only, not runtime assets. All application text remains accessible DOM text.


## Financial Insights & Analytics — original vectors

Figma file `kpEbLoKLaLiUcB8Q6xxgRl`, Insights page `2001:7028`. Six original 18×18 SVG exports live under `public/assets/insights/`, with SHA-256 and viewBox details in `provenance.json`.

| File | Source node | Usage |
|---|---|---|
| `up.svg` | `2001:81293` | Income/cash-flow icon |
| `budget.svg` | `2001:81301` | Expense/savings-rate icon |
| `wallet.svg` | `2001:81309` | Net cash-flow icon |
| `home.svg` | `2001:81419` | Largest spending category |
| `bag.svg` | `2001:81427` | Shopping trend |
| `ai-sparkle.svg` | `2001:81518` | Honest AI-unavailable panel |

All have viewBox `0 0 18 18`; original vector geometry is preserved. Parsed SVG validation rejects image/script/foreignObject nodes, event handlers and href dependencies; all six passed. `Icon` renders them through the existing currentColor mask convention. The existing Transactions `download.svg` and shared chevron are reused for their established action roles. No whole-page raster is used at runtime. Chart bars, labels, ring segments and progress meters are live HTML/SVG driven by records; screenshots under `docs/insights-qa/` are reference/QA only.


## AI Assistant original vectors

File `kpEbLoKLaLiUcB8Q6xxgRl`, canvas2001:7029, Welcome workspace2001:86385. `download_assets` returned two original AI Sparkle vectors, with no raw image fills:

| Local file | Original geometry | Usage |
|---|---|---|
| `public/assets/assistant/sparkle.svg` | 36×36, viewBox `0 0 36 36`, original #F9733B path | Welcome indicator |
| `public/assets/assistant/suggestion.svg` | 18×18, viewBox `0 0 18 18`, original clipped #F9733B path | Suggested questions, header/message/typing badges through shared CSS-mask Icon |

Original paths, viewBoxes and clipping are retained. CurrentColor masking is presentation only. Icons scale proportionally in the smaller header/message badges; no raster replacement or reconstructed geometry. Both files passed XML validation excluding image/script/foreignObject, event handlers and external dependencies; internal clip-path references are retained. `public/assets/assistant/provenance.json` records origin/usage/validation. Reference PNGs in docs/assistant-qa are QA only, never referenced by runtime UI.

## Planner original vector
Figma file `kpEbLoKLaLiUcB8Q6xxgRl`, page `2001:7030`, OccasionCard master `156:9053`, original Type illustration `156:9054`. `public/assets/planner/occasion.svg` retains the original two-path gift geometry, orange stroke and `0 0 18.2 18.2` viewBox. It is used on occasion cards and as a CSS mask on selected occasion-preparation tasks. XML validation passed: no raster/image/script/foreignObject/event handlers/href/external dependencies. SHA-256 and provenance are in `public/assets/planner/provenance.json`. Shared calendar/sidebar/brand icons remain unchanged. `docs/planner-qa/` PNGs are reference/QA only, never runtime backgrounds.

## Debt & Loans / Financial Hub
Read-only Figma kpEbLoKLaLiUcB8Q6xxgRl: original obligation 167:22297, shopping bag 176:27251, lent 2001:100683 and overdue 2001:100698, saved locally under `public/assets/debt/` and `public/assets/hub/`. SVG XML validated: no raster image, script, event handler or external dependency. ViewBoxes, SHA-256 and usage are recorded in `docs/debt-hub-qa/assets.json`. Existing original calendar, sidebar shortcuts and wallet SVG geometry is reused. Master icon colors and proportions are retained; wallet summary icons use the Hub peach/orange treatment. PNGs in docs are visual QA only. No Figma writes performed.

## Settings assets — reuse, not new Figma extraction

No Settings-specific Figma export was available and no new artwork was downloaded or rasterized. Settings reuses the existing runtime originals: `/assets/sidebar/logo-mark.svg`, `/assets/overview/{bell,wallet,edit}.svg`, `/assets/wallets/{bank,dl}.svg`, and `/assets/google.svg`. Their existing provenance entries remain unchanged. Generic Settings icons absent from local assets use the already-installed `lucide-react` (`UserRound`, `ShieldCheck`, `Link2`, `Database`, `CircleHelp`, `ArrowUpRight`, `LockKeyhole`, `Info`). These are explicitly fallback icons, **not** represented as verified original Settings/Figma geometry. Implementation screenshots are QA-only and are never used as runtime UI.
