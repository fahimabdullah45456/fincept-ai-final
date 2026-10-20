# Sidebar delivery — changed files

Baseline: available `FINCEPT-AI-Figma-First-Rules.zip` project. Source/UI changes are sidebar-only; runtime backend/authentication logic and dependencies remain unchanged. Browser checks refreshed existing screenshot evidence.

- Modified: `CLAUDE.md`
- Modified: `README.md`
- Added: `docs/ARCHITECTURE.md`
- Modified: `docs/ASSETS.md`
- Modified: `docs/DESIGN_SYSTEM.md`
- Modified: `docs/IMPLEMENTATION_STATUS.md`
- Modified: `docs/rendered-protected-landing.png`
- Modified: `docs/rendered-sign-in-loading.png`
- Modified: `docs/rendered-sign-up-validation.png`
- Added: `docs/sidebar-qa/1024-expanded.png`
- Added: `docs/sidebar-qa/1024-minimized.png`
- Added: `docs/sidebar-qa/1280-expanded.png`
- Added: `docs/sidebar-qa/1280-minimized.png`
- Added: `docs/sidebar-qa/1366-expanded.png`
- Added: `docs/sidebar-qa/1366-minimized.png`
- Added: `docs/sidebar-qa/1440-expanded.png`
- Added: `docs/sidebar-qa/1440-minimized.png`
- Added: `public/assets/sidebar/ai-assistant.svg`
- Added: `public/assets/sidebar/budgets.svg`
- Added: `public/assets/sidebar/debt-loans.svg`
- Added: `public/assets/sidebar/financial-goals.svg`
- Added: `public/assets/sidebar/financial-hub.svg`
- Added: `public/assets/sidebar/insights.svg`
- Added: `public/assets/sidebar/logo-mark.svg`
- Added: `public/assets/sidebar/overview.svg`
- Added: `public/assets/sidebar/planner.svg`
- Added: `public/assets/sidebar/provenance.json`
- Added: `public/assets/sidebar/settings.svg`
- Added: `public/assets/sidebar/transactions.svg`
- Added: `public/assets/sidebar/wallets.svg`
- Modified: `src/app/App.tsx`
- Added: `src/components/layout/AuthenticatedLayout.test.tsx`
- Added: `src/components/layout/AuthenticatedLayout.tsx`
- Added: `src/components/layout/SegmentPlaceholder.tsx`
- Added: `src/components/layout/Sidebar.tsx`
- Added: `src/components/layout/navigation.ts`
- Added: `src/styles/application.css`
- Modified: `tests/auth.spec.ts`
- Added: `tests/sidebar.spec.ts`

Integration into a newer checkout: preserve newer authentication components/assets. Merge the shared route parent and navigation imports from `src/app/App.tsx` rather than blindly replacing a newer App.tsx. See `ARCHITECTURE.md`.
