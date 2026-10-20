"""Wallet HTTP/SQLite invariants. No mocked accounting or persistence."""
import sqlite3
from uuid import uuid4
from datetime import date,datetime,timedelta
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from app.main import create_app
from test_transactions import tx,wallet,create,payload

def key():return str(uuid4())
def ws(c):return c.get('/api/wallets').json()
def one(c,w):return c.get('/api/wallets/'+w).json()['wallet']
def meta(c,w,**kwargs):
    x=one(c,w);return dict(request_key=key(),name=x['name'],kind=x['kind'],provider=x['provider'],identifier_last4=x['identifier_last4'],notes=x['notes'],status=x['status'],version=x['version'])|kwargs

def event(c,w,**kwargs):
    p=dict(request_key=key(),version=one(c,w)['version'],classification='external',amount_minor=20000,reason='Previously owned untracked cash',occurred_at=datetime.now().isoformat(timespec='seconds'))|kwargs
    return c.post('/api/wallets/'+w+'/events',json=p)
def action(c,w,a):return c.post('/api/wallets/'+w+'/'+a,json=dict(request_key=key(),version=one(c,w)['version']))

def test_wallet_metadata_summary_restart_and_safe_identifier(tx):
    c,s,u=tx
    p=dict(request_key=key(),name='My bank',kind='bank',opening_minor=12345,opening_date=date.today().isoformat(),provider='My Institution',identifier_last4='4821',notes='Manual',currency='BDT')
    r=c.post('/api/transactions/wallets',json=p);assert r.status_code==201,r.text
    id=r.json()['id'];assert c.post('/api/transactions/wallets',json=p).json()==r.json()
    wallet(c,'Mobile',20000,'mobile');wallet(c,'Cash',5000,'cash');wallet(c,'Savings',10000,'savings')
    x=ws(c);assert x['summary']['total']==dict(balance_minor=47345,count=4)
    assert x['summary']['bank']==dict(balance_minor=12345,count=1)
    assert sum(x['summary'][k]['balance_minor'] for k in ['bank','mobile','cash','savings'])==47345
    r=c.patch('/api/wallets/'+id,json=meta(c,id,name='Renamed',provider='Updated',notes='New note'));assert r.status_code==200
    assert one(c,id)['balance_minor']==12345
    p['request_key']=key();p['identifier_last4']='123456789';assert c.post('/api/transactions/wallets',json=p).status_code==422
    with TestClient(create_app(s)) as other:
        other.cookies.update(c.cookies);assert one(other,id)['provider']=='Updated'
    assert c.get('/api/transactions').json()['summary']['income_minor']==0

def test_external_and_adjustment_events_reconcile_overview_without_income(tx):
    c,s,u=tx;w=wallet(c,opening=10000)
    r=event(c,w);assert r.status_code==201,r.text
    assert one(c,w)['balance_minor']==30000
    r=event(c,w,classification='adjustment',amount_minor=None,corrected_minor=25000,expected_balance_minor=30000,reason='Reconcile cashbook');assert r.status_code==201,r.text
    assert one(c,w)['balance_minor']==25000
    d=c.get('/api/wallets/'+w).json();assert len(d['activity'])==2;assert {a['kind'] for a in d['activity']}=={'external','adjustment'}
    assert c.get('/api/transactions').json()['summary']['net_minor']==0
    overview=c.get('/api/overview/summary').json();assert overview['summary']['available_balance']==250
    with sqlite3.connect(s.database_path) as db:assert db.execute('select count(*) from wallet_events').fetchone()[0]==2

def test_event_idempotency_validation_and_stale_balance(tx):
    c,s,u=tx;w=wallet(c)
    p=dict(request_key=key(),version=1,classification='adjustment',amount_minor=100,reason='Correction',occurred_at=datetime.now().isoformat(timespec='seconds'))
    a=c.post('/api/wallets/'+w+'/events',json=p);assert a.status_code==201
    assert c.post('/api/wallets/'+w+'/events',json=p).json()==a.json()
    p['amount_minor']=200;assert c.post('/api/wallets/'+w+'/events',json=p).status_code==409
    assert event(c,w,amount_minor=-1).status_code==422
    assert event(c,w,classification='adjustment',reason=' ').status_code==422
    assert event(c,w,classification='adjustment',amount_minor=None,corrected_minor=100,expected_balance_minor=999999).status_code==409
    assert event(c,w,occurred_at='2026-02-31').status_code==422
    assert event(c,w,occurred_at='2026-01-01T10:00:00Z').status_code==422

def test_transfer_preserves_funds_excludes_principal_and_both_wallet_filters(tx):
    c,s,u=tx;a=wallet(c,'Cash',100000);b=wallet(c,'Bank',20000,'bank')
    p=payload(a,'transfer',20000,destination_wallet_id=b);r=c.post('/api/transactions',json=p);assert r.status_code==201
    assert one(c,a)['balance_minor']==80000;assert one(c,b)['balance_minor']==40000
    assert ws(c)['summary']['total']['balance_minor']==120000
    assert c.get('/api/transactions').json()['summary']['net_minor']==0
    for w in [a,b]:assert c.get('/api/transactions',params={'wallet':w}).json()['total']==1
    assert c.post('/api/transactions',json=p).json()==r.json()
    p['request_key']=key();p['destination_wallet_id']=a;assert c.post('/api/transactions',json=p).status_code==422
    p['destination_wallet_id']=b;p['amount_minor']=999999;assert c.post('/api/transactions',json=p).status_code==409
    assert one(c,a)['balance_minor']==80000;assert one(c,b)['balance_minor']==40000

def test_archive_preserves_history_and_excludes_selectors_financial_commands(tx):
    c,s,u=tx;a=wallet(c,'Cash');b=wallet(c,'Bank',0,'bank');t=create(c,a)
    assert action(c,a,'archive').status_code==200
    assert ws(c)['summary']['total']['balance_minor']==0
    assert c.get('/api/wallets/'+a).json()['activity'][0]['id']==t['id']
    assert c.post('/api/transactions',json=payload(a,'income')).status_code==422
    assert c.post('/api/transactions',json=payload(b,'transfer',100,destination_wallet_id=a)).status_code==422
    assert event(c,a).status_code==422
    r=c.request('DELETE','/api/transactions/'+t['id'],json=dict(request_key=key(),version=t['version']));assert r.status_code==409
    assert c.get('/api/overview/summary').json()['summary']['available_balance']==0
    assert action(c,a,'restore').status_code==200
    assert one(c,a)['balance_minor']==99000
    assert ws(c)['summary']['total']['balance_minor']==99000

def test_unused_delete_safe_and_inactive_rules(tx):
    c,s,u=tx;a=wallet(c,'Used',100);assert action(c,a,'delete').status_code==409
    b=wallet(c,'Unused',0);assert action(c,b,'delete').status_code==200;assert c.get('/api/wallets/'+b).status_code==404
    assert c.patch('/api/wallets/'+a,json=meta(c,a,status='inactive')).status_code==200
    assert ws(c)['summary']['total']['count']==0
    assert c.post('/api/transactions',json=payload(a,'income')).status_code==422
    assert c.patch('/api/wallets/'+a,json=meta(c,a,status='active')).status_code==200
    assert one(c,a)['balance_minor']==100

def test_ownership_dataset_and_authentication(tx):
    c,s,u=tx;a=wallet(c);cookie=dict(c.cookies)
    c.cookies.clear();assert c.get('/api/wallets').status_code==401
    c.post('/api/auth/register',json=dict(full_name='Other User',email='other-wallet@example.com',password='Fincept!2026',confirm_password='Fincept!2026',accepted_terms=True))
    assert ws(c)['items']==[];assert c.get('/api/wallets/'+a).status_code==404
    assert c.post('/api/wallets/'+a+'/archive',json=dict(request_key=key(),version=1)).status_code==404
    p=dict(request_key=key(),version=1,classification='external',amount_minor=100,reason='Cash',occurred_at=datetime.now().isoformat(timespec='seconds'))
    assert c.post('/api/wallets/'+a+'/events',json=p).status_code==404
    c.cookies.clear();c.cookies.update(cookie)
    assert c.get('/api/wallets/'+a,params={'dataset':'demo'}).status_code==404
    assert c.patch('/api/wallets/'+a,json=meta(c,a,version=99)).status_code==409

def test_simultaneous_transfer_does_not_partially_overdraw(tx):
    c,s,u=tx;a=wallet(c,'Source',10000);b=wallet(c,'Destination',0);cookies=dict(c.cookies)
    def send(_):
        with TestClient(create_app(s)) as client:
            client.cookies.update(cookies);client.headers.update(dict(c.headers));return client.post('/api/transactions',json=payload(a,'transfer',8000,destination_wallet_id=b)).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:assert sorted(pool.map(send,range(2)))==[201,409]
    assert one(c,a)['balance_minor']==2000;assert one(c,b)['balance_minor']==8000

def test_future_guard_includes_adjustment_and_rolls_back(tx):
    c,s,u=tx;w=wallet(c,opening=10000);future=(date.today()+timedelta(days=3)).isoformat()+'T12:00:00'
    r=c.post('/api/transactions',json=payload(w,'expense',9000)|{'occurred_at':future});assert r.status_code==201
    assert event(c,w,classification='adjustment',amount_minor=None,corrected_minor=5000,expected_balance_minor=10000).status_code==409
    assert one(c,w)['balance_minor']==10000
    assert action(c,w,'archive').status_code==409


def test_wallet_history_can_span_more_than_ten_years_but_unscoped_queries_cannot(tx):
    c,s,u=tx
    w=wallet(c,'Historic wallet',opening=0)
    with sqlite3.connect(s.database_path) as db:db.execute("UPDATE wallets SET opening_date='1901-01-01' WHERE id=?",(w,))
    query=dict(start='1901-01-01',end=date.today().isoformat())
    assert c.get('/api/transactions',params=query).status_code==422
    r=c.get('/api/transactions',params=query|dict(wallet=w))
    assert r.status_code==200,r.text
    assert r.json()['total']==0
    assert c.get('/api/transactions',params=query|dict(wallet='not-owned')).json()['total']==0
