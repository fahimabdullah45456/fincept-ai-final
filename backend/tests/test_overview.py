import sqlite3
from datetime import date
import pytest
from fastapi.testclient import TestClient
from app.main import Settings,create_app
from app.finance.service import period_range

@pytest.fixture
def overview(tmp_path):
    settings=Settings(database_path=str(tmp_path/'finance.sqlite3'))
    with TestClient(create_app(settings)) as client:
        client.headers.update({'X-Fincept-Request':'1','Origin':'http://localhost:5173'})
        data=dict(full_name='Tamim User',email='overview@example.com',password='Fincept!2026',confirm_password='Fincept!2026',accepted_terms=True)
        user=client.post('/api/auth/register',json=data).json()['user']
        yield client,settings,user

def test_auth_required(overview):
    c,_,_=overview;c.post('/api/auth/logout')
    for route in ['summary','insights','recent-transactions']:assert c.get('/api/overview/'+route).status_code==401
    assert c.post('/api/overview/demo').status_code==401

def test_empty_live_and_separate_explicit_demo(overview):
    c,_,_=overview;r=c.get('/api/overview/summary').json()
    assert r['summary']['income']==0 and r['summary']['savings_rate'] is None and r['summary']['wallet_count']==0
    assert not r['budgets'] and not r['goals']
    assert c.post('/api/overview/demo').status_code==201
    demo=c.get('/api/overview/summary?dataset=demo').json()
    assert demo['summary']['income']==52000 and demo['summary']['expenses']==38200
    assert demo['summary']['available_balance']==61350 and demo['summary']['savings_rate']==26.5
    assert c.get('/api/overview/summary').json()['summary']['income']==0
    assert c.get('/api/overview/recent-transactions?dataset=demo').json()['total']==48
    assert c.post('/api/overview/demo').status_code==201
    assert c.get('/api/overview/recent-transactions?dataset=demo').json()['total']==48

def test_reconciled_categories_budgets_goals_and_transfer_fee(overview):
    c,_,_=overview;c.post('/api/overview/demo');r=c.get('/api/overview/summary?dataset=demo').json()
    assert sum(x['amount'] for x in r['categories'])==38200
    shopping=next(b for b in r['budgets'] if b['name']=='Shopping')
    assert shopping['spent']==4900 and shopping['remaining']==-400 and shopping['percentage']==108.9
    assert r['goals'][0]['percentage']==40
    insight=c.get('/api/overview/insights?dataset=demo').json()['insight'];assert insight['kind']=='budget_over' and insight['budget']['name']=='Shopping'
    expenses=c.get('/api/overview/recent-transactions?dataset=demo&kind=expense').json();assert expenses['total']==38
    transfers=c.get('/api/overview/recent-transactions?dataset=demo&kind=transfer').json();assert transfers['total']==4

def test_reporting_filters_order_and_bounded_pagination(overview):
    c,_,_=overview;c.post('/api/overview/demo')
    records=c.get('/api/overview/recent-transactions?dataset=demo').json();assert len(records['items'])==6
    assert [r['date'] for r in records['items']]==sorted([r['date'] for r in records['items']],reverse=True)
    assert c.get('/api/overview/recent-transactions?dataset=demo&search=Uber').json()['total']==1
    assert c.get('/api/overview/recent-transactions?dataset=demo&search=%25').json()['total']==0
    assert c.get('/api/overview/recent-transactions?dataset=demo&category=Housing').json()['total']==1
    assert c.get('/api/overview/summary?dataset=demo&period=last_month').json()['summary']['income']==46000
    r=c.get('/api/overview/summary?dataset=demo&grouping=weekly').json();assert len(r['cash_flow']['buckets'])==6
    assert r['cash_flow']['grouping']=='weekly'

def test_validation_and_user_isolation(overview):
    c,_,_=overview;c.post('/api/overview/demo')
    for query in ['period=nope','dataset=nope','grouping=nope','period=custom','period=custom&start=2026-10-20&end=2026-10-01','period=custom&start=2000-01-01&end=2026-01-01']:
        assert c.get('/api/overview/summary?'+query).status_code==422
    assert c.get('/api/overview/recent-transactions?limit=1000').status_code==422
    c.post('/api/auth/register',json=dict(full_name='Other User',email='other@example.com',password='Fincept!2026',confirm_password='Fincept!2026',accepted_terms=True))
    assert c.get('/api/overview/summary?dataset=demo').json()['summary']['income']==0
    assert c.get('/api/overview/recent-transactions?dataset=demo').json()['total']==0

def test_negative_savings_and_uncategorized_records(overview):
    c,s,u=overview;today=date.today().isoformat()
    with sqlite3.connect(s.database_path) as db:
        db.execute("PRAGMA foreign_keys=ON");db.execute("INSERT INTO financial_workspaces VALUES (?,'live')",(u['id'],))
        db.execute("INSERT INTO wallets VALUES ('wallet',?,'live','Cash',0,?)",(u['id'],today))
        for id,kind,amount in [('i','income',10000),('e','expense',15000)]:
            db.execute('INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(id,u['id'],'live','wallet',None,kind,amount,id,'',None,today,None))
    r=c.get('/api/overview/summary').json();assert r['summary']['savings_rate']==-50 and r['summary']['available_balance']==-50
    assert r['categories'][0]['name']=='Other'
    assert c.get('/api/overview/insights').json()['insight']['kind']=='negative_cash_flow'

def test_period_definitions_and_zero_limits(overview):
    a,b,p,q=period_range('this_month',today=date(2026,3,10));assert (a,b,p,q)==(date(2026,3,1),date(2026,3,31),date(2026,2,1),date(2026,2,28))
    c,s,u=overview;c.post('/api/overview/demo')
    with sqlite3.connect(s.database_path) as db:
        db.execute("UPDATE budgets SET limit_minor=0 WHERE user_id=?",(u['id'],));db.execute("UPDATE financial_goals SET target_minor=0 WHERE user_id=?",(u['id'],))
    r=c.get('/api/overview/summary?dataset=demo').json();assert all(b['percentage'] is None for b in r['budgets']);assert all(g['percentage'] is None for g in r['goals'])

def test_production_rejects_sample_workspace(tmp_path):
    # Existing secure auth cookies require HTTPS in production.
    settings=Settings(database_path=str(tmp_path/'production.sqlite3'),environment='production',cookie_secure=True,frontend_origins=('https://localhost:5173',))
    with TestClient(create_app(settings),base_url='https://localhost:5173') as client:
        client.headers.update({'X-Fincept-Request':'1','Origin':'https://localhost:5173'})
        response=client.post('/api/auth/register',json=dict(full_name='Production User',email='prod@example.com',password='Fincept!2026',confirm_password='Fincept!2026',accepted_terms=True))
        assert response.status_code==201
        assert client.post('/api/overview/demo').status_code==403
        assert client.get('/api/overview/summary?dataset=demo').status_code==403
        assert client.get('/api/overview/summary').status_code==200
