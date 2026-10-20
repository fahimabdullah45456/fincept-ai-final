# Financial Hub — implemented v10

`/financial-hub` reuses the authenticated shell and global monetary privacy. The page contains Wallet Overview, persisted Shopping Lists, genuine Currency Converter, eight existing-route shortcuts and real upcoming activities.

## Wallet and activity sources
Wallets come directly from `finance.ledger.wallets`: same owner/dataset, opening balances, canonical transactions and wallet events as Wallets/Overview. Active, unarchived wallets only; savings/occasion earmarks are not added as new money. Runtime card count is dynamic, not five permanent sample wallets. Total includes eligible negative balances; allocation safely uses only positive balances with an explicit negative-balance disclosure, and disappears for zero funds/privacy. No duplicate balance table or financial-write service was added. Wallet View activity opens that exact existing Wallet Details using a query deep link.

Activities are saved open Planner tasks, active occasion deadlines with their explicitly planned contribution amounts, and unpaid EMI installments due today through 30 days. Ordinary tasks have no invented monetary amount. Occasions display deadlines, not a made-up recurring contribution event or delivery reminder. Activities are sorted by civil date/ID, capped at 20 on screen, and route to the existing source. No notifications are sent. Hub dates use UTC server calendar days; Debt uses its explicit browser-timezone API convention.

## Purchase planning
`shopping_lists` stores name/category/optional shopping date/notes/version. `shopping_items` stores whole-unit quantity, estimated unit price in integer minor units, purchase status/date, optional **actual total paid** and notes/version. Up to 200 items per list. List categories are purchase-planning labels, not automatic expense/budget category assignments. Creation can include initial items atomically. Items can be added, edited, marked purchased/unpurchased and removed. List metadata can be edited; consequential removal/deletion is confirmed. List version advances on item changes, so deleting a stale list cannot silently delete concurrently updated items.

Estimated total = quantity × estimated unit price. Remaining estimate includes unpurchased items. Actual recorded = known actual totals on purchased items only. Unknown actual cost is **not** zero; a deliberately recorded zero is valid. Variance compares only the same purchased items with known actual costs. Completed means a nonempty list with every item purchased; active metrics include non-completed lists only. View All Lists exposes active/completed filters and search.

**No spending is automatically recorded.** Creating a list, purchasing or deleting an item never creates/deletes an expense, changes a wallet, or changes a budget. Open Transactions is explicit navigation to the existing feature; there is no automatic matching/linking or duplicate expense creation. Actual costs are user-entered purchase-tracking values, not independently verified transaction records. Existing transaction history survives all list/item deletion.

## Real exchange rates
Server-side `hub/fx.py` uses **ExchangeRate-API Open Access** at the fixed HTTPS `https://open.er-api.com/v6/latest/{base}` endpoint. No API key is needed for this open-access plan. Terms/documentation: https://www.exchangerate-api.com/docs/free . Required attribution appears in the UI. Provider updates approximately daily; no claim of market-tick real-time pricing is made.

Explicit supported application currencies: BDT, USD, EUR, GBP, INR, JPY, CAD, AUD, SAR, AED. Unsupported API codes are rejected. The server validates base identity, finite positive rates and provider timestamp, never accepts a timestamp more than ten minutes ahead or older than 48 hours, and proxies only the fixed provider host. Responses are cached in SQLite for one hour (provider's documented safe request cadence), reusing actual provider `as_of` separately from `fetched_at`. If refresh fails, an existing rate no older than 48 hours may be returned as **stale**, visibly labeled with a warning. Older/unavailable data returns 503; no sample rate is substituted. Supported currencies can be expanded deliberately in both server and client configuration, not through arbitrary URLs.

The converter debounces currency fetches, aborts stale requests and clears obsolete results. Convert validates finite nonnegative amounts up to one trillion and six input decimals. Swap exchanges selectors and recalculates after the new base data arrives. Same-currency conversion is identity and needs no provider. JPY results use zero decimals; other supported currencies use two. Clear resets input/result/validation. Privacy conceals input/result/rate; rates are indicative and do not execute currency exchange. Provider/cache tests use explicit fixtures; a separate genuine authenticated endpoint check returned HTTP 200 for BDT and all ten supported currencies (see QA report). Outbound HTTPS access and provider availability are still necessary.

## Endpoints and security
- `GET /api/hub`: canonical active wallets, owned list details/summaries, actual activities.
- `GET /api/hub/rates?base=BDT`: authenticated provider/cache response.
- `POST /api/hub/lists`; `PATCH` / `DELETE /api/hub/lists/{id}`.
- `POST /api/hub/lists/{id}/items`; `PATCH` / `DELETE /api/hub/lists/{id}/items/{item_id}`.

Writes use existing session/CSRF protection, strict monetary inputs, owner/dataset isolation, IMMEDIATE transactions, versions and replay-safe request receipts. Item/list deletion cascades only planning records. Shared privacy conceals money in all summaries, forms, details, history, allocation and converter output. React escapes entered text. No new dependencies or client secrets were added.
