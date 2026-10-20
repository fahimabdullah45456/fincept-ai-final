"""Insights read model and CSV report.

Reuses the shared accounting helpers instead of a parallel dashboard ledger:
- service.period_range for period resolution/validation (shared with Overview),
- only canonical `income`/`expense` transactions count; transfer principal never does
  (single transfer fees are already stored as ordinary expenses),
- budget_service.evaluate for budget performance (shared with Budgets and Overview),
- goal_service.goals/summary for the active-goal savings snapshot (shared with Goals).
All amounts are integer minor units (paisa).
"""
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
import csv
import io
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from .service import period_range, month_shift, between
from .budget_service import evaluate
from .goal_service import goals as goal_records, summary as goal_summary
from .csv_safety import csv_safe

Period = Literal['this_month', 'last_month', 'last_3_months', 'this_year', 'custom']
Dataset = Literal['live', 'demo']
COUNTED = ('income', 'expense')


def month_end(day):
    return month_shift(day.replace(day=1), 1) - timedelta(days=1)


def is_full_month(first, last):
    return first.day == 1 and last == month_end(first)


def share(part, whole):
    return round(part * 100 / whole, 1) if whole else None


def change(current, previous):
    # No fabricated comparison: a zero previous value yields no percentage.
    return round((current - previous) * 100 / previous, 1) if previous else None


def range_label(first, last, exact=False):
    if not exact and is_full_month(first, last):
        return f'{first:%B %Y}'
    if not exact and first == date(first.year, 1, 1) and last == date(first.year, 12, 31):
        return str(first.year)
    if not exact and first.day == 1 and last == month_end(last):
        return f'{first:%B}–{last:%B %Y}' if first.year == last.year else f'{first:%B %Y}–{last:%B %Y}'
    if first == last:
        return f'{first.day:02d} {first:%b %Y}'
    if first.year == last.year:
        return f'{first.day:02d} {first:%b}–{last.day:02d} {last:%b %Y}'
    return f'{first.day:02d} {first:%b %Y}–{last.day:02d} {last:%b %Y}'


def months_label(first, last):
    if first.replace(day=1) == last.replace(day=1):
        return f'{first:%B}'
    return f'{first:%B}–{last:%B}' if first.year == last.year else f'{first:%B %Y}–{last:%B %Y}'


def totals(rows):
    income = sum(r['amount_minor'] for r in rows if r['kind'] == 'income')
    expenses = sum(r['amount_minor'] for r in rows if r['kind'] == 'expense')
    return income, expenses


def spans_for(first, last):
    """Chart buckets: six-month context for one calendar month, otherwise the range itself."""
    if is_full_month(first, last):
        starts = [month_shift(first, i - 5) for i in range(6)]
        return 'context', [(s, month_end(s)) for s in starts]
    starts = []
    cursor = first.replace(day=1)
    while cursor <= last:
        starts.append(cursor)
        cursor = month_shift(cursor, 1)
    if len(starts) <= 12:
        return 'monthly', [(max(s, first), min(month_end(s), last)) for s in starts]
    spans = []
    quarter = date(first.year, (first.month - 1) // 3 * 3 + 1, 1)
    while quarter <= last:
        spans.append((max(quarter, first), min(month_end(month_shift(quarter, 2)), last)))
        quarter = month_shift(quarter, 3)
    return 'quarterly', spans


def cash_flow(rows, first, last, period, today):
    mode, spans = spans_for(first, last)
    buckets = []
    for a, b in spans:
        selected_rows = [r for r in rows if between(r, a, b)]
        income, expenses = totals(selected_rows)
        quarter = mode == 'quarterly'
        buckets.append({
            'label': f"Q{(a.month - 1) // 3 + 1} {a.year}" if quarter else f'{a:%b}',
            'full_label': range_label(a, b),
            'start': a.isoformat(), 'end': b.isoformat(),
            'income_minor': income, 'expenses_minor': expenses, 'net_minor': income - expenses,
            'record_count': len(selected_rows),
            'selected': mode != 'context' or a == first,
        })
    omitted = []
    # Leading periods without records are not charted as a zero trend; the selected bucket is always kept.
    while len(buckets) > 1 and buckets[0]['record_count'] == 0:
        omitted.append(buckets.pop(0))
    if period == 'this_year':
        while len(buckets) > 1 and buckets[-1]['record_count'] == 0 and date.fromisoformat(buckets[-1]['start']) > today:
            buckets.pop()
    label = range_label(first, last, period == 'custom')
    if not any(b['record_count'] for b in buckets):
        scope = 'Selected range · Monthly recorded totals'
    elif mode == 'context' and len(buckets) > 1:
        a, b = date.fromisoformat(buckets[0]['start']), date.fromisoformat(buckets[-1]['end'])
        span = f'{a:%b}–{b:%b %Y}' if a.year == b.year else f'{a:%b %Y}–{b:%b %Y}'
        scope = f'{span} trend · Selected period highlighted'
    elif mode == 'context':
        scope = 'Selected range · Monthly recorded totals'
    elif omitted:
        scope = f"{label} recorded history · No records for {months_label(date.fromisoformat(omitted[0]['start']), date.fromisoformat(omitted[-1]['end']))}"
    else:
        scope = 'Selected range · ' + ('Quarterly' if mode == 'quarterly' else 'Monthly') + ' recorded totals'
    return {'mode': mode, 'scope': scope, 'buckets': buckets,
            'has_history': any(b['record_count'] for b in buckets)}


def grouped(rows, kind, fallback):
    groups = defaultdict(lambda: [0, 0])
    for r in rows:
        if r['kind'] == kind:
            key = r['category'] or fallback
            groups[key][0] += r['amount_minor']
            groups[key][1] += 1
    total = sum(v[0] for v in groups.values())
    items = [{'name': name, 'amount_minor': amount, 'percentage': share(amount, total), 'count': count}
             for name, (amount, count) in groups.items()]
    items.sort(key=lambda x: (x['name'] == fallback, -x['amount_minor'], x['name'].casefold()))
    return {'total_minor': total, 'items': items}


def build(conn, user, dataset, period, start=None, end=None, today=None):
    today = today or date.today()
    first, last, previous_first, previous_last = period_range(period, start, end, today)
    single = is_full_month(first, last)
    mode, spans = spans_for(first, last)
    query_start = min(spans[0][0], first, month_shift(first, -1) if single else first)
    rows = [dict(r) for r in conn.execute(
        "SELECT id,kind,amount_minor,category,occurred_at FROM transactions WHERE user_id=? AND dataset=? "
        "AND kind IN ('income','expense') AND substr(occurred_at,1,10)>=? AND substr(occurred_at,1,10)<=?",
        (user, dataset, query_start.isoformat(), last.isoformat()))]
    transfers = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE user_id=? AND dataset=? AND kind='transfer' "
        "AND substr(occurred_at,1,10)>=? AND substr(occurred_at,1,10)<=?",
        (user, dataset, first.isoformat(), last.isoformat())).fetchone()[0]
    current = [r for r in rows if between(r, first, last)]
    income, expenses = totals(current)
    summary = {'income_minor': income, 'expenses_minor': expenses, 'net_minor': income - expenses,
               'savings_rate': share(income - expenses, income), 'comparison': None}
    if single:
        p_first = month_shift(first, -1)
        p_income, p_expenses = totals([r for r in rows if between(r, p_first, first - timedelta(days=1))])
        summary['comparison'] = {'label': f'{p_first:%B}', 'start': p_first.isoformat(),
                                 'end': (first - timedelta(days=1)).isoformat(),
                                 'income_minor': p_income, 'expenses_minor': p_expenses,
                                 'income_change': change(income, p_income), 'expense_change': change(expenses, p_expenses)}
    categories = grouped(current, 'expense', 'Other')
    sources = grouped(current, 'income', 'Other Income')
    largest = max(categories['items'], key=lambda x: (x['amount_minor'], x['name'] != 'Other'), default=None)
    shopping = sum(x['amount_minor'] for x in categories['items'] if x['name'].casefold() == 'shopping')
    budget_data = evaluate(conn, user, dataset, first.isoformat(), last.isoformat())
    budgets = [{'id': b['id'], 'name': b['name'], 'category': b['category'], 'spent_minor': b['spent_minor'],
                'limit_minor': b['limit_minor'], 'remaining_minor': b['remaining_minor'],
                'percentage': round(b['percentage'], 1) if b['percentage'] is not None else None,
                'status': b['status'], 'start_date': b['start_date'], 'end_date': b['end_date'],
                'conflicted': b['conflicted']} for b in budget_data['items']]
    goal_snapshot = goal_summary(goal_records(conn, user, dataset))
    return {
        'dataset': dataset,
        'period': period,
        'range': {'start': first.isoformat(), 'end': last.isoformat(), 'label': range_label(first, last, period == 'custom'),
                  'single_month': single, 'days': (last - first).days + 1},
        'summary': summary,
        'cash_flow': cash_flow(rows, first, last, period, today),
        'categories': categories,
        'income_sources': sources,
        'trends': {'largest_category': largest, 'shopping_minor': shopping, 'net_minor': income - expenses},
        'savings': {'as_of': today.isoformat(), 'saved_minor': goal_snapshot['saved_minor'],
                    'target_minor': goal_snapshot['target_minor'], 'remaining_minor': goal_snapshot['remaining_minor'],
                    'percentage': round(goal_snapshot['percentage'], 1) if goal_snapshot['percentage'] is not None else None,
                    'active_count': goal_snapshot['active_count']},
        'budgets': {'count': len(budgets), 'items': budgets[:3], 'ambiguous_count': budget_data['ambiguous_count']},
        # No AI provider is integrated. Nothing deterministic is presented as an AI finding.
        'ai': {'available': False, 'reason': 'not_configured', 'findings': []},
        'record_count': len(current),
        'transfer_count': transfers,
    }


def amount(minor, masked):
    if masked:
        return '****'
    sign = '-' if minor < 0 else ''
    minor = abs(minor)
    return f'{sign}{minor // 100}.{minor % 100:02d}'


def percent(value):
    return 'Not available' if value is None else f'{value}'


def report_csv(data, masked, generated_at=None):
    generated_at = generated_at or datetime.now(timezone.utc).isoformat(timespec='seconds')
    out = io.StringIO(newline='')
    w = csv.writer(out)
    r = data['range']
    w.writerow(['FINCEPT AI Insights report'])
    w.writerow(['Period', csv_safe(r['label'])])
    w.writerow(['Start date', r['start']])
    w.writerow(['End date', r['end']])
    w.writerow(['Generated at (UTC)', generated_at])
    w.writerow(['Dataset', 'Sample (illustrative)' if data['dataset'] == 'demo' else 'Live records'])
    w.writerow(['Monetary values', 'Masked (privacy mode)' if masked else 'BDT'])
    w.writerow([])
    s = data['summary']
    w.writerow(['Summary', 'Value'])
    w.writerow(['Total income (BDT)', amount(s['income_minor'], masked)])
    w.writerow(['Total expenses (BDT)', amount(s['expenses_minor'], masked)])
    w.writerow(['Net cash flow (BDT)', amount(s['net_minor'], masked)])
    w.writerow(['Savings rate (%)', percent(s['savings_rate'])])
    if s['comparison']:
        c = s['comparison']
        w.writerow([f"Income change vs {c['label']} (%)", percent(c['income_change'])])
        w.writerow([f"Expense change vs {c['label']} (%)", percent(c['expense_change'])])
    w.writerow([])
    w.writerow(['Chart scope', csv_safe(data['cash_flow'].get('scope', 'Selected range'))])
    w.writerow(['Income vs expenses', 'Start date', 'End date', 'Income (BDT)', 'Expenses (BDT)', 'Net cash flow (BDT)', 'In selected range'])
    for b in data['cash_flow']['buckets']:
        w.writerow([csv_safe(b['full_label']), b['start'], b['end'], amount(b['income_minor'], masked),
                    amount(b['expenses_minor'], masked), amount(b['net_minor'], masked),
                    'Yes' if b.get('selected', True) else 'Context only'])
    w.writerow([])
    w.writerow(['Expense category', 'Amount (BDT)', 'Share of expenses (%)', 'Records'])
    for x in data['categories']['items']:
        w.writerow([csv_safe(x['name']), amount(x['amount_minor'], masked), percent(x['percentage']), x['count']])
    w.writerow([])
    w.writerow(['Income source', 'Amount (BDT)', 'Share of income (%)', 'Records'])
    for x in data['income_sources']['items']:
        w.writerow([csv_safe(x['name']), amount(x['amount_minor'], masked), percent(x['percentage']), x['count']])
    w.writerow([])
    w.writerow(['Notes'])
    w.writerow(['Internal wallet transfers are excluded from income and expenses. Savings rate = net cash flow / income.'])
    w.writerow(['Budget and goal snapshots are not included in this transaction analytics report.'])
    return '\ufeff' + out.getvalue()


def insights_router(db, current_user, environment):
    router = APIRouter(prefix='/api/insights', tags=['Insights'])

    def check(dataset):
        if dataset == 'demo' and environment == 'production':
            raise HTTPException(403, 'Sample workspaces are disabled in production.')

    @router.get('')
    def read(period: Period = 'this_month', dataset: Dataset = 'live', start: date | None = None,
             end: date | None = None, user=Depends(current_user)):
        check(dataset)
        with db() as conn:
            return build(conn, user['id'], dataset, period, start, end)

    @router.get('/export')
    def export(period: Period = 'this_month', dataset: Dataset = 'live', start: date | None = None,
               end: date | None = None, masked: bool = False, user=Depends(current_user)):
        check(dataset)
        with db() as conn:
            data = build(conn, user['id'], dataset, period, start, end)
        name = f"fincept-insights-{data['range']['start']}-to-{data['range']['end']}.csv"
        return Response(report_csv(data, masked), media_type='text/csv; charset=utf-8',
                        headers={'Content-Disposition': f'attachment; filename="{name}"',
                                 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})

    return router
