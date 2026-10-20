# Authentication — implemented vector asset corrections

## Current status: implemented and browser-verified

This is no longer an audit-only result. The actual Sign In and Sign Up UI uses original Figma SVGs, live browser text, shared React elements and CSS/SVG geometry. No authentication page requests either legacy PNG. No backend, authentication logic, validation, labels, navigation, dependencies or unrelated application features were changed.

Previously retrieved assets under `docs/asset-audit/` were reused without downloading them again. Six were copied byte-for-byte into `public/assets/auth/`; the seventh, Google, already matched the existing runtime `public/assets/google.svg` and was left untouched. Only missing illustration geometry and wordmark details were re-inspected in Figma; no design content was modified.

## Original components and actual implementation

| Figma component | Node | Runtime implementation |
| --- | --- | --- |
| Brand/Logo Mark | `3:18` | `AuthBrand`: original SVG mark, live FINCEPT wordmark |
| Input/Field | `3:23` | Shared FormField / PasswordField; Label, Placeholder and Show eye equivalents |
| Button/Primary | `3:30` | Existing PrimaryButton; unchanged behavior |
| Button/Social | `3:32` | Existing SocialAuthButton with unchanged original Google SVG |
| Password/Strength | `3:39` | Existing shared PasswordStrength; unchanged behavior |

The original authentication components expose text/boolean properties, not named component-set variants. The financial illustration remains a composition based on editable frame `2001:5234`, not a claimed prebuilt Figma COMPONENT import. AuthFinancialIllustration is shared by both pages, with reusable IllustrationCategoryCard and IllustrationProgressRing subcomponents.

The previously inspected file also has component masters for Transactions, AI Assistant, Planner, Debt & Loans, Financial Hub, Settings and Overview. Actual examples include the Transactions CalculatorKey interaction variants and Overview Balance Toggle visibility/hover variants. No other segment was implemented or modified in this correction pass.

## Original SVGs now used by the UI

| Runtime path | Source node | viewBox | Actual usage |
| --- | --- | --- | --- |
| `public/assets/auth/logo-mark.svg` | `3:18` | 0 0 38 38 | AuthBrand on both pages and protected auth confirmation |
| `public/assets/auth/savings-chart.svg` | `2001:5242` | 0 0 324 96 | Original chart path, gradient and point in the live savings card |
| `public/assets/auth/housing-icon.svg` | `2001:5253` | 0 0 18 18 | Housing card |
| `public/assets/auth/wallet-icon.svg` | `2001:5260` | 0 0 18 18 | Emergency fund card |
| `public/assets/auth/groceries-icon.svg` | `2001:5269` | 0 0 18 18 | Groceries card |
| `public/assets/auth/password-eye.svg` | `3:27` | 0 0 20 20 | Actual password visibility buttons, including confirm password |
| `public/assets/google.svg` (unchanged) | `3:32` / `3:33` icon subtree | 0 0 18 18 | Actual Google authentication button |

All six promoted SVGs match their audited originals byte-for-byte. XML checks reject image/script/foreignObject elements, event handlers and non-local hrefs. Their paths, fills, viewBoxes, gradients and clipping were not redrawn or altered. SVG images retain their original width/height ratios in the UI.

## Live illustration structure and fidelity

The logical illustration coordinate space remains 605 × 340, at the original placement in the shared brand panel. It contains:
- CSS back card (340 × 250, -3° rotation) and white savings card (372 × 257).
- Browser text for MONTHLY SAVINGS, ৳8,450, the monthly delta, category labels/details and illustrative-value disclaimer.
- The original 324 × 96 savings chart SVG.
- A real 64px SVG progress ring with 78% inner radius, 75% clockwise arc and a live 75% label.
- Three shared HTML/CSS category cards using the original housing, wallet and groceries SVGs.

The wordmark is live Manrope Bold, 23px, 1.5px tracking, 31px line box; the original 38px SVG mark and 10px gap preserve the original brand proportions. Both main pages and the protected confirmation use AuthBrand, eliminating the remaining standalone brand PNG reference.

The same original eye SVG is used in both password visibility states. Existing type switching, aria-pressed and Show/Hide accessible labels remain unchanged. No original eye-off asset was verified, so an invented alternate icon is not claimed or substituted. Google OAuth remains unconfigured and its existing honest unavailable message is unchanged.

## Removed runtime PNG references

- `/assets/fincept-brand.png` removed from AuthBrandPanel and the protected confirmation component in App.tsx.
- `/assets/auth-financial-illustration.png` removed from AuthFinancialIllustration.

Both original PNG files remain in `public/assets/` as legacy references; no source component references them. No unrelated assets were deleted. The app's live text is not baked into screenshots or outlined SVG sections.

## Currency glyph and remaining discrepancies

Manrope's distributed font has no U+09F3 taka glyph. When changing raster text to browser text this initially produced a missing glyph, caught in visual review. A 2.4KB local Noto Sans Bengali variable-font subset now supplies **only U+09F3**; Manrope remains unchanged for Latin text. The font's SIL OFL license is included. Figma reports the text layer as Manrope but does not identify the currency fallback, so identical fallback glyph metrics cannot be guaranteed. Minor currency glyph width, browser antialiasing and CSS-vs-Figma shadow rendering differences remain; no missing glyph or layout break was observed in the final captures. Pixel-identical rendering across platforms is not claimed.

At 125%/150% zoom, the existing desktop minimum canvas remains in use and requires scrolling in a 1440 × 980 physical window. This is intentional desktop behavior, not a mobile/tablet variant. Original contrast limitations remain unchanged.

## Actual running UI verification

- Started Vite frontend and the unchanged FastAPI backend.
- Opened both actual routes and checked original SVG sources, loaded image state, live text wordmark, live savings/category text, three composed cards and two SVG ring circles.
- Confirmed zero PNG image elements and zero PNG network requests on both authentication pages.
- Exercised show/hide password on both routes; original eye SVG remains loaded and input behavior is preserved.
- Retained original Google asset; hash comparison confirms it is unchanged.
- Native Chromium zoom used `chrome.tabs.setZoom` and `chrome.tabs.getZoom`, not CSS zoom, pinch scaling or device-scale-factor simulation. Verified browser zoom 1/1.25/1.5 with unchanged CSS zoom and a 1440 × 980 physical viewport; effective CSS widths were 1440/1152/960. Native scrolling keeps the desktop form usable.
- Captured and individually opened both pages at all three zooms; compared the reference-scale rendering with the original Figma screenshot. Also reviewed refreshed validation, loading, server-error and protected confirmation captures.
- Six zoom captures and machine-readable runtime assertions: `docs/asset-correction-zooms/`. Repeat with `tests/verify-asset-zoom.mjs` while the app runs; its test-only extension is not bundled into the application.

## Final checks

- `npm run build`: PASS (TypeScript + Vite).
- `npm test`: PASS — 13 tests.
- `npm run test:e2e`: PASS — 12 tests, including live asset/reference checks.
- Backend `python -m pytest -q`: PASS — 11 tests; one pre-existing upstream Starlette/httpx deprecation warning.
- Total automated regression tests: **36 passed**, plus six native-zoom page checks.
- Hash comparisons confirmed 15 protected backend/auth logic/Google/dependency/config files unchanged.

See `docs/ASSET_CORRECTION_FILES.md` for every added/modified deliverable relative to the previous project archive.
