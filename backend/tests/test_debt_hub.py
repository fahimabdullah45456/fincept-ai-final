from datetime import date,timedelta,datetime,timezone
from uuid import uuid4
import sqlite3
import pytest
from fastapi.testclient import TestClient
from app.main import Settings,create_app
from app.debt.routes import schedule
from app.hub import fx
H={'X-Fincept-Request':'1','Origin':'http://localhost:5173'}
def key():return str(uuid4())
def account(c):
    r=c.post('/api/auth/register',json=dict(full_name='Debt User',email=key()+'@example.com',password='Fincept!2026',confirm_password='Fincept!2026',accepted_terms=True));assert r.status_code==201,r.text
@pytest.fixture
def env(tmp_path):
    path=str(tmp_path/'app.sqlite3');app=create_app(Settings(database_path=path))
    with TestClient(app,headers=H) as c:account(c);yield c,path,app

def debt(**kw):return dict(request_key=key(),kind='borrowed',name='Family loan',counterparty='Family',principal_minor=3000000,opened_date='2020-01-01',due_date=(date.today()+timedelta(days=10)).isoformat())|kw
def create(c,p=None):
    r=c.post('/api/debts',json=p or debt());assert r.status_code==201,r.text;return r.json()
def command(r,**kw):return dict(request_key=key(),version=r['version'])|kw
def test_debt_payment_replay_reverse_and_archive(env):
    c,path,_=env;p=debt(interest_minor=5000);r=create(c,p);assert create(c,p)['id']==r['id'];url='/api/debts/'+r['id']
    pay=command(r,principal_minor=1000000,interest_minor=2000,fee_minor=100,paid_date=date.today().isoformat())
    x=c.post(url+'/payments',json=pay);assert x.status_code==201,x.text;x=x.json();assert x['outstanding_minor']==2000000 and x['interest_remaining_minor']==3000
    assert c.post(url+'/payments',json=pay).json()['version']==2
    assert c.post(url+'/payments',json=pay|{'request_key':key()}).status_code==409
    bad=command(x,principal_minor=2000001,paid_date=date.today().isoformat());assert c.post(url+'/payments',json=bad).status_code==422
    assert c.request('DELETE',url,json=command(x)).status_code==422
    reversal=command(x,reason='Entered the wrong payment');y=c.post(url+'/payments/'+x['history'][0]['id']+'/reverse',json=reversal);assert y.status_code==200,y.text;y=y.json();assert y['outstanding_minor']==3000000 and len(y['history'])==2
    full=c.post(url+'/payments',json=command(y,principal_minor=3000000,interest_minor=5000,paid_date=date.today().isoformat())).json();assert full['state']=='Paid Off'
    assert c.request('DELETE',url,json=command(full)).status_code==200
    with sqlite3.connect(path) as db:assert db.execute('SELECT count(*) FROM transactions').fetchone()[0]==0 and db.execute('SELECT count(*) FROM debt_payments').fetchone()[0]==3

def test_owner_scope_versions_and_edit_lock(env):
    c,_,_=env;p=debt();r=create(c,p);url='/api/debts/'+r['id'];edit=p|command(r,name='Renamed');assert c.patch(url,json=edit).status_code==200
    r=c.get('/api/debts').json()['items'][0];x=c.post(url+'/payments',json=command(r,principal_minor=1,paid_date=date.today().isoformat())).json()
    assert c.patch(url,json=p|command(x,principal_minor=4000000)).status_code==422
    account(c);assert c.get('/api/debts').json()['items']==[];assert c.patch(url,json=edit).status_code==404
    assert c.post(url+'/payments',json=command(x,principal_minor=1,paid_date=date.today().isoformat())).status_code==404

def emi(**kw):return debt(kind='emi',purchase_minor=100000,down_minor=10000,principal_minor=90000,interest_minor=0,frequency='Monthly',first_date='2028-01-31',installment_minor=26000,installments=4,due_date=None)|kw
@pytest.mark.parametrize('first,expected',[('2028-01-31',['2028-01-31','2028-02-29','2028-03-31','2028-04-30']),('2027-12-31',['2027-12-31','2028-01-31','2028-02-29','2028-03-31']),('2027-01-31',['2027-01-31','2027-02-28','2027-03-31','2027-04-30'])])
def test_monthly_schedule(first,expected):
    rows=schedule(emi(first_date=first));assert [x['due_date'] for x in rows]==expected;assert [x['amount_minor'] for x in rows]==[26000,26000,26000,12000];assert sum(x['principal_minor'] for x in rows)==90000

def test_emi_summary_no_doublecount_and_partial(env):
    c,_,_=env;r=create(c,emi(first_date='2020-01-31',interest_minor=10000,installment_minor=30000));assert len(r['schedule'])==4
    s=c.get('/api/debts').json()['summary'];assert s['borrowed_minor']==90000 and s['overdue_minor']==100000
    x=c.post('/api/debts/'+r['id']+'/payments',json=command(r,principal_minor=27000,interest_minor=3000,paid_date=date.today().isoformat())).json();assert x['schedule'][0]['status']=='Paid' and x['schedule'][1]['status']=='Overdue';assert x['outstanding_minor']==63000
@pytest.mark.parametrize('change',[{'principal_minor':0},{'due_date':'2019-01-01'},{'interest_minor':-1},{'principal_minor':1.5},{'opened_date':'2027-02-29'}])
def test_invalid_debt(env,change):assert env[0].post('/api/debts',json=debt(**change)).status_code==422
@pytest.mark.parametrize('change',[{'installments':3},{'purchase_minor':0},{'first_date':'2019-01-01'},{'installments':600,'first_date':'2099-01-31'}])
def test_invalid_emi(env,change):assert env[0].post('/api/debts',json=emi(**change)).status_code==422

def test_upcoming_boundaries_lent_and_paid_dates(env):
    c,_,_=env
    for offset in [-1,0,1,30,31]:create(c,debt(principal_minor=100,due_date=(date.today()+timedelta(days=offset)).isoformat()))
    create(c,debt(kind='lent',principal_minor=200))
    s=c.get('/api/debts').json()['summary'];assert s==dict(borrowed_minor=500,lent_minor=200,upcoming_minor=200,upcoming_count=2,overdue_minor=100,overdue_count=1)
    r=c.get('/api/debts').json()['items'][0];assert c.post('/api/debts/'+r['id']+'/payments',json=command(r,principal_minor=1,paid_date=(date.today()+timedelta(days=1)).isoformat())).status_code==422

def list_input():return dict(request_key=key(),name='Groceries',category='Food',items=[dict(name='Rice',quantity=2,unit_minor=5000)])
def test_shopping_lifecycle_unknown_actual_no_spending(env):
    c,path,_=env;p=list_input();res=c.post('/api/hub/lists',json=p);assert res.status_code==201,res.text;r=res.json();assert c.post('/api/hub/lists',json=p).json()['id']==r['id'];url='/api/hub/lists/'+r['id'];item=r['items'][0]
    data={k:item[k] for k in ['name','quantity','unit_minor','category','notes']};data|=dict(request_key=key(),version=1,purchased=True,purchased_date=date.today().isoformat())
    x=c.patch(url+'/items/'+item['id'],json=data);assert x.status_code==200,x.text;x=x.json();assert x['actual_minor'] is None and x['unknown_actual_count']==1 and x['complete']
    assert c.get('/api/hub').status_code==200
    data|=dict(request_key=key(),version=2,actual_minor=9000);x=c.patch(url+'/items/'+item['id'],json=data).json();assert x['actual_minor']==9000 and x['comparable_estimate_minor']==10000
    assert c.patch(url+'/items/'+item['id'],json=data|{'request_key':key()}).status_code==409
    assert c.request('DELETE',url,json=command(x)).status_code==200
    with sqlite3.connect(path) as db:assert db.execute('SELECT count(*) FROM transactions').fetchone()[0]==0 and db.execute('SELECT count(*) FROM shopping_items').fetchone()[0]==0

def test_shopping_ownership_and_validation(env):
    c,_,_=env;r=c.post('/api/hub/lists',json=list_input()).json();url='/api/hub/lists/'+r['id'];account(c)
    assert c.get('/api/hub').json()['lists']==[];assert c.request('DELETE',url,json=command(r)).status_code==404
    assert c.post('/api/hub/lists',json=list_input()|{'items':[dict(name='Bad',quantity=0)]}).status_code==422
    assert c.post('/api/hub/lists',json=list_input()|{'items':[dict(name='Bad',actual_minor=1)]}).status_code==422

def test_fx_cache_and_failure(env,monkeypatch):
    c,_,_=env;calls=[]
    def provider(base):
        calls.append(base);return dict(base=base,rates={x:1 for x in fx.CURRENCIES},source=fx.SOURCE,source_url='https://www.exchangerate-api.com/docs/free',as_of=datetime.now(timezone.utc).isoformat(),fetched_at=datetime.now(timezone.utc).isoformat())
    monkeypatch.setattr(fx,'fetch_rates',provider)
    assert c.get('/api/hub/rates?base=BDT').json()['status']=='live';assert c.get('/api/hub/rates?base=BDT').json()['status']=='cached';assert calls==['BDT']
    monkeypatch.setattr(fx,'fetch_rates',lambda base:(_ for _ in ()).throw(OSError('offline')))
    assert c.get('/api/hub/rates?base=USD').status_code==503;assert c.get('/api/hub/rates?base=XXX').status_code==422

def test_hub_wallet_reconciles_and_activity(env):
    c,_,_=env
    w=c.post('/api/transactions/wallets',json=dict(request_key=key(),name='Cash',kind='cash',opening_minor=10000,opening_date='2020-01-01'));assert w.status_code==201,w.text
    x=c.get('/api/hub');assert x.status_code==200,x.text;assert x.json()['total_minor']==10000
    t=c.post('/api/planner/tasks',json=dict(request_key=key(),title='Real task',due_date=date.today().isoformat()));assert t.status_code==201
    x=c.get('/api/hub').json();assert x['activities'][0]['amount_minor'] is None

def test_weekly_schedule_exact_remainder_and_interest_rounding():
    rows=schedule(emi(first_date='2028-02-22',frequency='Weekly',interest_minor=7,installment_minor=26000))
    assert [r['due_date'] for r in rows]==['2028-02-22','2028-02-29','2028-03-07','2028-03-14']
    assert sum(r['principal_minor'] for r in rows)==90000 and sum(r['interest_minor'] for r in rows)==7
    assert rows[-1]['amount_minor']==12007

def test_payment_interest_overpay_atomic_and_no_sample_mixing(env):
    c,path,_=env;r=create(c,debt(interest_minor=10));url='/api/debts/'+r['id']+'/payments'
    assert c.post(url,json=command(r,principal_minor=100,interest_minor=11,paid_date=date.today().isoformat())).status_code==422
    assert c.get('/api/debts').json()['items'][0]['version']==1
    assert c.get('/api/debts?dataset=demo').json()['items']==[]
    with sqlite3.connect(path) as db:assert db.execute('SELECT count(*) FROM debt_payments').fetchone()[0]==0

def test_shopping_item_add_edit_remove_and_list_versions(env):
    c,_,_=env;r=c.post('/api/hub/lists',json=list_input()|{'items':[]}).json();url='/api/hub/lists/'+r['id'];p=dict(request_key=key(),name='Milk',quantity=2,unit_minor=125)
    x=c.post(url+'/items',json=p);assert x.status_code==201,x.text;x=x.json();assert c.post(url+'/items',json=p).json()['id']==r['id'];assert x['estimated_minor']==250
    assert c.patch(url,json=dict(request_key=key(),version=r['version'],name='Old version')).status_code==409
    y=c.patch(url,json=dict(request_key=key(),version=x['version'],name='New name',category='Groceries')).json();item=x['items'][0]
    assert c.request('DELETE',url+'/items/'+item['id'],json=command(item)).status_code==200
    z=c.get('/api/hub').json()['lists'][0];assert z['items']==[] and z['name']=='New name' and z['version']==y['version']+1

def test_zero_actual_is_not_unknown(env):
    c,_,_=env;p=list_input();p['items'][0]|=dict(purchased=True,purchased_date=date.today().isoformat(),actual_minor=0)
    r=c.post('/api/hub/lists',json=p);assert r.status_code==201,r.text;assert r.json()['actual_minor']==0 and r.json()['unknown_actual_count']==0

@pytest.mark.parametrize('age,expected',[(25,'stale'),(49,'unavailable')])
def test_fx_stale_cache_and_hard_expiry(env,monkeypatch,age,expected):
    import json
    c,path,_=env;stamp=(datetime.now(timezone.utc)-timedelta(hours=age)).isoformat();payload=dict(base='BDT',rates={x:1 for x in fx.CURRENCIES},as_of=stamp,fetched_at=stamp,source=fx.SOURCE)
    with sqlite3.connect(path) as db:db.execute('INSERT INTO hub_fx_cache VALUES (?,?,?)',('BDT',json.dumps(payload),stamp))
    monkeypatch.setattr(fx,'fetch_rates',lambda base:(_ for _ in ()).throw(OSError('offline')))
    r=c.get('/api/hub/rates?base=BDT');assert r.status_code==(200 if expected=='stale' else 503)
    if expected=='stale':assert r.json()['status']=='stale' and r.json()['warning']

def test_new_routes_require_session_and_csrf(env):
    c,_,_=env
    assert c.post('/api/debts',headers={'X-Fincept-Request':'0'},json=debt()).status_code==403
    c.post('/api/auth/logout')
    for url in ['/api/debts','/api/hub','/api/hub/rates']:assert c.get(url).status_code==401

def test_occasion_activity_uses_existing_plan_and_not_wallet_money(env):
    c,_,_=env;date_str=(date.today()+timedelta(days=5)).isoformat()
    p=dict(request_key=key(),name='Birthday',occasion_type='Birthday',occasion_date=date_str,start_date=date.today().isoformat(),target_minor=100000,frequency='Monthly',planned_minor=10000)
    r=c.post('/api/planner/plans',json=p);assert r.status_code==201,r.text
    x=c.get('/api/hub');assert x.status_code==200,x.text;x=x.json();assert x['total_minor']==0 and x['activities'][0]['amount_minor']==10000
