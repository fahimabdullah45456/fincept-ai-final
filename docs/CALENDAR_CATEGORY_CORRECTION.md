# Targeted calendar and category-create correction

## Scope

This follow-up corrects only Transactions calendar/date-time controls and the Create custom category interface, using the user's existing Figma. No Figma nodes were changed. Authentication, Overview, application layout/sidebar/header, other page styling and financial accounting are not redesigned.

Read-only source file: `kpEbLoKLaLiUcB8Q6xxgRl`. Supplied section `2001:34544` contains the reusable `DateTimeSelector` component `230:4953` (482 × 342). The original Create custom category frame is `2001:32339` (640 × 668). Both were inspected for child geometry, text/font properties, fills, strokes and reusable structure; screenshots in `ui-correction-qa/` are reference/verification only. The available Figma MCP read-only inspection/export API was used; separate figma-use skill resources remained unavailable.

## Calendar

`src/features/transactions/DateTimePicker.tsx` translates the original calendar to actual semantic controls: Monday-first week headings, rounded selected-day fill, month title, Today/Yesterday, 24-hour time field and Apply. Original colors, font weights, spacing and day geometry are retained. Previous/next month buttons are small functional additions so the calendar works beyond the illustrative month; six-week months grow by one row. Date-only uses retain the same calendar without the time input.

Transactions add/edit date and time buttons share this one component. Transactions date-range/advanced-filter inputs and wallet-opening date reuse it, instead of invoking the browser's generic calendar. No Overview or authentication controls were replaced. Applying commits the draft; Escape/outside dismissal leaves existing values unchanged. It supports arrow keys, Home/End, Page Up/Down (Shift for years), valid leap/month boundaries, 1901–2100 limits and explicit 24-hour validation. Native browser Popover API places the popup in the top layer inside the existing native modal, with viewport clamping and focus return. Reduced-motion preference disables popup animation.

## Create custom category

`CreateCategory.tsx` implements the original centered dialog: heading/divider, category-name input, Income/Expense segmented buttons, six icon choices, six color circles/check selection, uniqueness guidance, and fixed Cancel/Create footer. The existing category manager gets a Create category entry point; existing rename/reassignment flows remain intact. The original Figma prototype footer is replaced with truthful live/sample context, not a fake prototype label.

All six original 22 × 22 category SVGs were exported read-only, XML-validated and stored in `public/assets/categories/`, with exact source nodes in `provenance.json`. They contain vector geometry, no raster/script/external resources. The Icon component gains only the local `categories` collection option. Styling is isolated in `transaction-corrections.css` and does not override global design tokens.

Category creation still uses the existing authenticated, owner/dataset-scoped API. Name/type rules and protected defaults remain unchanged. A small additive schema-v4 `category_appearance` table persists allowlisted icon/color choices without changing canonical financial/category columns, IDs or accounting. Existing categories fall back to receipt/orange; existing rename requests preserve saved appearance. Foreign-key cascade removes appearance when a category is reassigned/deleted. New choices are shown on custom entries in the existing category manager; unrelated financial table/Overview icon mappings are not restyled.

## Verification

See IMPLEMENTATION_STATUS.md for final executed counts and `ui-correction-qa/verification.txt` for commands. Added calendar unit coverage (Monday-first, apply-only commit, month/leap boundaries, keyboard, invalid time), category appearance validation/persistence/rename/fallback/cascade backend tests, and real-browser tests for date/time persistence, filter calendar integration, draft cancellation, duplicate category errors, icon/color/type persistence and all four requested desktop sizes.

The corrected project package supersedes the previous Authentication + Overview + Transactions ZIP; it is one complete source package, not a second application. Extract to a new folder and follow START_HERE.md. Back up existing databases and private environment files before the additive schema update. No new package dependencies, secrets, provider setup or deployment changes are required.
