"""Insights read model: auth, ownership, shared accounting, period validation and CSV export."""
import csv
import io
import sqlite3
from datetime import date
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.main import Settings, create_app
from app.finance.insights import build, report_csv, range_label, cash_flow, month_end
from app.finance.csv_safety import csv_safe


def register(c, email):
    r = c.post('/api/auth/register', json=dict(full_name='Insights User', email=email, password='Fincept!2026',
                                                confirm_password='Fincept!2026', accepted_terms=True))
    assert r.status_code == 201, r.text


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(Settings(database_path=str(tmp_path / 'insights.sqlite3')))) as c:
        c.headers.update({'X-Fincept-Request': '1', 'Origin': 'http://localhost:5173'})
        register(c, 'insights@example.com')
        c.db_path = str(tmp_path / 'insights.sqlite3')
        yield c


def wallet(c, name='Bank', opening=10_000_000, kind='bank'):
    r = c.post('/api/transactions/wallets', json=dict(request_key=str(uuid4()), name=name, kind=kind, opening_minor=opening,
                                                      opening_date=date.today().replace(day=1).isoformat()))
    assert r.status_code == 201, r.text
    return r.json()['id']


def record(c, w, kind, amount, category, **kw):
    body = dict(request_key=str(uuid4()), kind=kind, amount_minor=amount, wallet_id=w, category=category,
                occurred_at=date.today().isoformat() + 'T09:00:00', title=kw.pop('title', (category or 'Transfer') + ' record'), **kw)
    r = c.post('/api/transactions', json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_requires_authentication(client):
    client.post('/api/auth/logout')
    assert client.get('/api/insights').status_code == 401
    assert client.get('/api/insights/export').status_code == 401


def test_empty_workspace_is_honest(client):
    r = client.get('/api/insights').json()
    assert r['summary']['income_minor'] == 0 and r['summary']['savings_rate'] is None
    assert r['summary']['comparison']['income_change'] is None  # no fabricated % against a zero month
    assert r['categories']['items'] == [] and r['income_sources']['items'] == []
    assert r['trends']['largest_category'] is None
    assert r['cash_flow']['has_history'] is False and len(r['cash_flow']['buckets']) == 1
    assert r['budgets']['count'] == 0 and r['savings']['active_count'] == 0
    assert r['ai'] == {'available': False, 'reason': 'not_configured', 'findings': []}


def test_demo_reconciles_with_overview_and_budgets(client):
    assert client.post('/api/overview/demo').status_code == 201
    r = client.get('/api/insights?dataset=demo').json()
    overview = client.get('/api/overview/summary?dataset=demo').json()
    assert r['summary']['income_minor'] == round(overview['summary']['income'] * 100) == 5_200_000
    assert r['summary']['expenses_minor'] == round(overview['summary']['expenses'] * 100) == 3_820_000
    assert r['summary']['net_minor'] == 1_380_000 and r['summary']['savings_rate'] == overview['summary']['savings_rate'] == 26.5
    assert sum(x['amount_minor'] for x in r['categories']['items']) == r['categories']['total_minor'] == 3_820_000
    assert {x['name']: round(x['amount_minor'] / 100, 2) for x in r['categories']['items']} == {x['name']: x['amount'] for x in overview['categories']}
    assert r['categories']['items'][-1]['name'] == 'Other'  # catch-all stays last
    assert r['trends']['largest_category']['name'] == 'Housing' and r['trends']['shopping_minor'] == 490_000
    comparison = r['summary']['comparison']
    assert comparison['label'] == 'September' or comparison['income_minor'] > 0
    assert comparison['income_change'] == round((5_200_000 - comparison['income_minor']) * 100 / comparison['income_minor'], 1)
    shopping = next(b for b in r['budgets']['items'] if b['name'] == 'Shopping')
    assert shopping['spent_minor'] == 490_000 and shopping['status'] == 'Exceeded' and shopping['percentage'] == 108.9
    budgets = client.get('/api/budgets?dataset=demo&month=' + date.today().strftime('%Y-%m')).json()
    assert r['budgets']['count'] == len(budgets['items'])
    goals = client.get('/api/goals?dataset=demo').json()['summary']
    assert r['savings']['saved_minor'] == goals['saved_minor'] and r['savings']['target_minor'] == goals['target_minor']
    assert r['transfer_count'] == 4 and r['record_count'] == 44
    report = client.get('/api/insights/export?dataset=demo').text
    assert 'Chart scope' in report and 'In selected range' in report and 'Context only' in report
    buckets = r['cash_flow']['buckets']
    assert len(buckets) == 6 and buckets[-1]['selected'] and not any(b['selected'] for b in buckets[:-1])
    assert client.get('/api/insights').json()['summary']['income_minor'] == 0  # live data untouched


def test_transfers_are_excluded_and_fee_counts_once(client):
    bank, savings = wallet(client), wallet(client, 'Savings', 0, 'savings')
    record(client, bank, 'income', 5_000_000, 'Salary')
    record(client, bank, 'income', 1_000_000, 'Freelance')
    record(client, bank, 'expense', 1_200_000, 'Shopping')
    record(client, bank, 'transfer', 2_000_000, 'Transfer', destination_wallet_id=savings, fee_minor=1_000)
    r = client.get('/api/insights').json()
    assert r['summary']['income_minor'] == 6_000_000
    assert r['summary']['expenses_minor'] == 1_201_000  # transfer principal excluded, fee is a single expense
    assert r['transfer_count'] == 1
    assert [x['name'] for x in r['income_sources']['items']] == ['Salary', 'Freelance']
    assert [x['percentage'] for x in r['income_sources']['items']] == [83.3, 16.7]


def test_owner_isolation(client, tmp_path):
    record(client, wallet(client), 'income', 700_000, 'Salary')
    client.post('/api/auth/logout')
    register(client, 'other@example.com')
    r = client.get('/api/insights').json()
    assert r['summary']['income_minor'] == 0 and r['record_count'] == 0


def test_period_validation(client):
    assert client.get('/api/insights?period=custom&start=2026-02-01&end=2026-01-01').status_code == 422
    assert client.get('/api/insights?period=custom&start=2026-02-01').status_code == 422
    assert client.get('/api/insights?period=custom&start=2020-01-01&end=2026-01-01').status_code == 422
    assert client.get('/api/insights?period=yesterday').status_code == 422
    assert client.get('/api/insights?period=custom&start=2026-02-30&end=2026-03-01').status_code == 422
    ok = client.get('/api/insights?period=custom&start=2026-09-01&end=2026-10-31').json()
    assert ok['range']['label'] == '01 Sep–31 Oct 2026' and ok['summary']['comparison'] is None


def test_period_resolution_and_buckets(client):
    today = date(2026, 10, 18)
    conn = sqlite3.connect(client.db_path)
    conn.row_factory = sqlite3.Row
    with conn:
        three = build(conn, 'nobody', 'live', 'last_3_months', today=today)
        year = build(conn, 'nobody', 'live', 'this_year', today=today)
        last = build(conn, 'nobody', 'live', 'last_month', today=today)
    assert (three['range']['start'], three['range']['end']) == ('2026-08-01', '2026-10-31')
    assert three['range']['label'] == 'August–October 2026'
    assert (year['range']['start'], year['range']['end'], year['range']['label']) == ('2026-01-01', '2026-12-31', '2026')
    assert last['range']['label'] == 'September 2026' and last['range']['single_month']
    assert range_label(date(2025, 12, 1), date(2026, 1, 31)) == 'December 2025–January 2026'
    rows = [{'kind': 'income', 'amount_minor': 100, 'category': 'Salary', 'occurred_at': '2025-02-03T10:00:00'}]
    quarterly = cash_flow(rows, date(2024, 1, 1), date(2025, 6, 30), 'custom', today)
    assert quarterly['mode'] == 'quarterly' and quarterly['buckets'][0]['label'] == 'Q1 2025'
    assert 'No records for' in quarterly['scope']


def test_export_csv_masking_and_formula_safety(client):
    bank = wallet(client)
    record(client, bank, 'income', 5_200_000, 'Salary')
    created = client.post('/api/transactions/categories', json=dict(name='=HYPERLINK("x")', kind='expense'))
    assert created.status_code in (200, 201), created.text
    record(client, bank, 'expense', 1_234_567, '=HYPERLINK("x")')
    r = client.get('/api/insights/export')
    assert r.status_code == 200 and r.headers['content-type'].startswith('text/csv')
    assert 'attachment; filename="fincept-insights-' in r.headers['content-disposition']
    rows = list(csv.reader(io.StringIO(r.text.lstrip('\ufeff'))))
    flat = {row[0]: row[1:] for row in rows if row}
    assert flat['Total income (BDT)'] == ['52000.00'] and flat['Total expenses (BDT)'] == ['12345.67']
    assert flat['Net cash flow (BDT)'] == ['39654.33']
    assert "'=HYPERLINK(\"x\")" in flat and '=HYPERLINK("x")' not in flat
    masked = client.get('/api/insights/export?masked=true').text
    assert '52000.00' not in masked and '****' in masked and 'Masked (privacy mode)' in masked
    assert client.get('/api/insights/export?period=custom&start=2026-02-01&end=2026-01-01').status_code == 422


def test_csv_safe_and_negative_amounts():
    assert csv_safe('@SUM(1)') == "'@SUM(1)" and csv_safe(' -1') == "' -1" and csv_safe('\tx') == "'\tx" and csv_safe('Food') == 'Food'
    data = {'dataset': 'live', 'range': {'label': 'October 2026', 'start': '2026-10-01', 'end': '2026-10-31'},
            'summary': {'income_minor': 0, 'expenses_minor': 150, 'net_minor': -150, 'savings_rate': None, 'comparison': None},
            'cash_flow': {'buckets': []}, 'categories': {'items': []}, 'income_sources': {'items': []}}
    text = report_csv(data, False, '2026-10-18T00:00:00+00:00')
    assert 'Net cash flow (BDT),-1.50' in text and 'Savings rate (%),Not available' in text


def test_custom_range_inclusive_boundaries_and_partial_budget_limit(client):
    bank = wallet(client)
    current = date.today().replace(day=1)
    first, last = current.isoformat(), month_end(current).isoformat()
    p = dict(request_key=str(uuid4()), name='Food plan', category='Food', limit_minor=100000,
             start_date=first, end_date=last, reset_period='monthly', alert_threshold=75)
    assert client.post('/api/budgets', json=p).status_code == 201
    for day, minor in [(1, 1000), (10, 2000), (11, 4000)]:
        body = dict(request_key=str(uuid4()), kind='expense', wallet_id=bank, amount_minor=minor,
                    category='Food', title='Food', occurred_at=current.replace(day=day).isoformat()+'T00:00:00')
        assert client.post('/api/transactions', json=body).status_code == 201
    end = current.replace(day=10).isoformat()
    r = client.get(f'/api/insights?period=custom&start={first}&end={end}').json()
    assert r['summary']['expenses_minor'] == 3000  # both endpoints inclusive; day 11 excluded
    assert r['budgets']['items'][0]['spent_minor'] == 3000
    assert r['budgets']['items'][0]['limit_minor'] == 100000  # never silently prorated
    assert r['budgets']['items'][0]['remaining_minor'] == 97000
    assert r['summary']['savings_rate'] is None and r['summary']['net_minor'] == -3000
    assert r['summary']['comparison'] is None
    report = client.get(f'/api/insights/export?period=custom&start={first}&end={end}').text
    assert 'Total expenses (BDT),30.00' in report and 'Net cash flow (BDT),-30.00' in report
    assert 'Savings rate (%),Not available' in report


def test_category_csv_quoting_and_masked_export_ownership(client):
    bank = wallet(client)
    category = 'Food, "special"\nsecond line'
    # Stored imported categories are still handled safely by the CSV read model.
    with sqlite3.connect(client.db_path) as conn:
        user = conn.execute('SELECT id FROM users WHERE email=?', ('insights@example.com',)).fetchone()[0]
        conn.execute('INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?,?,?,NULL)',
                     (str(uuid4()), user, 'live', bank, None, 'expense', 12345, 'Imported expense', '', category, date.today().isoformat()+'T00:00:00'))
    text = client.get('/api/insights/export').text
    rows = list(csv.reader(io.StringIO(text.lstrip('\ufeff'))))
    assert [category, '123.45', '100.0', '1'] in rows
    client.post('/api/auth/logout')
    register(client, 'csv-other@example.com')
    assert category not in client.get('/api/insights/export').text
    assert '123.45' not in client.get('/api/insights/export?masked=true').text


def test_production_demo_read_and_export_disabled(tmp_path):
    settings = Settings(database_path=str(tmp_path/'production-insights.sqlite3'), environment='production',
                        cookie_secure=True, frontend_origins=('https://testserver',))
    with TestClient(create_app(settings), base_url='https://testserver') as c:
        c.headers.update({'X-Fincept-Request': '1', 'Origin': 'https://testserver'})
        register(c, 'production-insights@example.com')
        assert c.get('/api/insights?dataset=demo').status_code == 403
        assert c.get('/api/insights/export?dataset=demo').status_code == 403
        assert c.get('/api/insights').headers['cache-control'] == 'no-store'


def test_uncategorized_imports_reconcile_with_other_drill_down(client):
    bank = wallet(client)
    with sqlite3.connect(client.db_path) as conn:
        user = conn.execute('SELECT id FROM users WHERE email=?', ('insights@example.com',)).fetchone()[0]
        for category, minor in [(None, 100), ('', 200), ('Other', 300)]:
            conn.execute('INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?,?,?,NULL)',
                         (str(uuid4()), user, 'live', bank, None, 'expense', minor, 'Imported expense', '', category, date.today().isoformat()+'T00:00:00'))
    data = client.get('/api/insights').json()
    assert data['categories']['items'] == [dict(name='Other', amount_minor=600, percentage=100.0, count=3)]
    listing = client.get('/api/transactions?kind=expense&category=Other').json()
    assert listing['total'] == 3 and sum(t['amount_minor'] for t in listing['items']) == 600
