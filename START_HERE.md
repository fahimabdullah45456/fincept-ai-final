# FINCEPT AI — combined project

This is one complete source-code package containing:
- Sign In and Sign Up with the verified vector asset corrections.
- Existing FastAPI/SQLite authentication backend and canonical financial read/write APIs.
- Full Financial Goals: persistent plans, reviewed contributions, wallet earmarks/external deposits, active summaries, pause/resume, history and privacy. See docs/GOALS.md for accounting and migration v7.
- Full Budgets: persistent category plans, period summaries, actual expense history, shared Overview calculations, filters and risk alerts.
- Full Wallets: real accounts, active summaries, grid/list, Add Money, transfers and archived wallets.
- Full Transactions: actual persistent CRUD, calculator, transfers/fees, categories, filtering, pagination and CSV export.
- Full Overview: summary, charts, categories, budgets, goals, insights and filtered/paged recent transactions.
- Shared, expandable/collapsible sidebar and protected routes.
- Full Insights: real period analytics, interactive charts, category detail and CSV export.
- AI Assistant: persistent chat, native financial read tools and confirmed budget/goal/income-expense create/update proposals through the existing backend. Real model replies require a privately configured tool-capable OpenAI model; see docs/ASSISTANT.md and docs/AI_ACTIONS.md.
- Settings: all seven categories, real profile/security/preferences, shared privacy, scoped CSV/JSON exports and confirmed demo cleanup. Unsupported restore, account deletion and providers are explicitly unavailable; see docs/SETTINGS.md.
- Tests, local assets, configuration examples and documentation.

You do NOT need to merge either earlier ZIP into this folder. Extract this ZIP into a new folder. Keep your previous project as a backup; do not overwrite an existing `.env` or database.

## Run locally

Prerequisites: Node.js/npm and Python 3.13 (the versions used for verification). See README.md for OS-specific virtualenv activation and environment configuration.

### 1. Backend — terminal one

```sh
cd fincept-ai/backend
python -m venv .venv
```

Activate the virtualenv (`.venv\Scripts\activate` on Windows, or `source .venv/bin/activate` on macOS/Linux), then:

```sh
python -m pip install -r requirements-dev.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. Frontend — terminal two

```sh
cd fincept-ai
npm ci
npm run dev
```

Open http://127.0.0.1:5173/sign-up to create a local account, or /sign-in to log in. After authentication, click **Open Overview**. New accounts show empty live data. Click **Explore sample data** to see the full illustrative page; the sample is explicitly labeled and never changes your live records. The sample option is development-only.

## Scope

Overview is implemented as a real read-side dashboard. Transactions is implemented as a real authenticated read/write page. Open Transactions, click **Create wallet**, enter your actual opening position, then **Add Transaction**. Save, refresh and verify the record; edit/delete use the same backend. A second wallet enables transfers. Overview reads the same ledger. No sample data is inserted into live accounts. Wallets is now implemented: use **Add Wallet** for an opening balance, **Add Money** with an explicit classification, or **Transfer** between two accounts. See docs/WALLETS.md. Budgets, Financial Goals, Insights, AI Assistant, Planner, Debt & Loans and Financial Hub are also included; see their feature documentation. AI insight is deterministic/rule-based, not an LLM. Google OAuth, password recovery and final legal content retain their existing configuration/implementation limitations. No demo credentials, secrets, databases, virtualenvs or node_modules are included. Dependencies are installed using the commands above.

See docs/COMBINED_PROJECT.md for merge and verification details.

## Calendar/category corrected package

This package also includes the original Figma calendar/date-time UI and Create custom category dialog. In Transactions, choose **Categories → Create category**, then select a name, type, icon and color. These choices persist through the existing backend. Date buttons open the custom calendar; **Apply** commits the date/time. No extra dependencies are required. Existing databases receive additive presentation-only schema v4; back up data before upgrading. See docs/CALENDAR_CATEGORY_CORRECTION.md.

## Wallets upgrade

This complete ZIP includes every earlier implemented feature plus Wallets. Do not merge old ZIPs into it. Preserve your existing `.env` and SQLite database separately; after backup, point this backend at that database to apply additive schema v5 automatically. No bank connection or new credentials are required. Full setup commands above remain unchanged.

## Budgets

Open `/budgets` after signing in. Existing SQLite databases migrate additively to v6 on backend startup; back up your database first. See `docs/BUDGETS.md` for API, period, allocation, overlap and threshold rules, `docs/BUDGETS_FILES.md` for the exact change inventory, and `docs/budgets-qa/verification.json` for executed checks. Saved Weekly/Monthly/Custom windows do not automatically renew; no new external configuration is required. Earlier Authentication, Overview, Transactions and Wallets code is included.

## Planner
Open **Planner** in the existing sidebar after signing in. New accounts start empty. Add a dated task or create an occasion savings plan; real data persists in SQLite. Use reviewed contributions rather than typing an opening saved amount. No reminder delivery is configured. See `docs/PLANNER.md` and `docs/PLANNER_FILES.md`. Startup upgrades the database additively to v9; back up existing data before upgrading.


## Latest segments: Debt & Loans and Financial Hub
This is a complete combined source package; do not merge older ZIPs into it. Open the existing sidebar destinations after signing in. Startup applies additive schema **v10**; back up your existing SQLite database and keep your private `.env` separately before upgrading. Fresh accounts start empty. Debt repayments and shopping purchases are tracking-only and never automatically change wallet balances or create expenses. The Hub reads your existing canonical wallets. FX uses ExchangeRate-API Open Access without an API key; server outbound HTTPS is required and rates are indicative. See `docs/DEBT_LOANS.md`, `docs/FINANCIAL_HUB.md` and `docs/debt-hub-qa/README.md` for setup boundaries and final verification.

## Latest segment: Settings

This package now includes the integrated seven-category Settings section. Run the same frontend/backend commands; no extra dependencies or secrets are required. Startup upgrades SQLite additively to **v11**. Preserve your private environment/database and back up before upgrading. See `docs/SETTINGS.md` for working operations, persistence, export scope, unavailable services, and design-access limitations. See `docs/settings-qa/README.md` for actual verification. Do not merge older feature ZIPs into this complete project.
