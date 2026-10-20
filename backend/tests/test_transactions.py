"""Real SQLite/HTTP command, isolation, accounting and export regressions."""
import csv
import io
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import date,timedelta
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.main import Settings,create_app

@pytest.fixture
def tx(tmp_path):
    settings=Settings(database_path=str(tmp_path/'tx.sqlite3'))
    with TestClient(create_app(settings)) as c:
        c.headers.update({'X-Fincept-Request':'1','Origin':'http://localhost:5173'})
        user=c.post('/api/auth/register',json=dict(full_name='Transaction User',email='transactions@example.com',password='Fincept!2026',confirm_password='Fincept!2026',accepted_terms=True)).json()['user']
        yield c,settings,user

def wallet(c,name='Cash',opening=100000,kind='cash'):
    r=c.post('/api/transactions/wallets',json=dict(request_key=str(uuid4()),name=name,kind=kind,opening_minor=opening,opening_date=date.today().replace(day=1).isoformat()))
    assert r.status_code==201,r.text
    return r.json()['id']
# Midnight is already recorded at any test-run time; noon can be a future ledger event.
def payload(w,kind='expense',amount=1000,**kw):
    return dict(request_key=str(uuid4()),kind=kind,amount_minor=amount,wallet_id=w,category='Salary' if kind=='income' else 'Food',occurred_at=date.today().isoformat()+'T00:00:00',title='Test record',**kw)
def create(c,w,kind='expense',amount=1000,**kw):
    r=c.post('/api/transactions',json=payload(w,kind,amount,**kw));assert r.status_code==201,r.text;return r.json()
def options(c):return c.get('/api/transactions/options').json()
def test_crud_persists_same_id_version_and_balances(tx):
    c,s,u=tx;w=wallet(c);x=create(c,w);assert options(c)['wallets'][0]['balance_minor']==99000
    r=c.get('/api/transactions');assert r.status_code==200,r.text;assert r.json()['summary']['expenses_minor']==1000
    saved=c.get('/api/transactions/'+x['id']).json();assert saved['title']=='Test record'
    p=payload(w,amount=2500,version=x['version']);p['notes']='Receipt kept';edit=c.patch('/api/transactions/'+x['id'],json=p);assert edit.status_code==200,edit.text
    assert edit.json()['id']==x['id'] and edit.json()['version']==2
    assert options(c)['wallets'][0]['balance_minor']==97500
    assert c.patch('/api/transactions/'+x['id'],json=payload(w,amount=500,version=1)).status_code==409
    d=c.request('DELETE','/api/transactions/'+x['id'],json=dict(request_key=str(uuid4()),version=2));assert d.status_code==200,d.text
    assert c.get('/api/transactions/'+x['id']).status_code==404 and options(c)['wallets'][0]['balance_minor']==100000
    with sqlite3.connect(s.database_path) as db:assert db.execute('SELECT count(*) FROM transactions WHERE user_id=?',(u['id'],)).fetchone()[0]==0

def test_transfers_fees_edit_delete_are_atomic_and_not_cashflow(tx):
    c,_,_=tx;w=wallet(c);d=wallet(c,'Savings',0,'savings');p=payload(w,'transfer',20000,destination_wallet_id=d,fee_minor=500)
    r=c.post('/api/transactions',json=p);assert r.status_code==201,r.text;x=r.json()
    data=c.get('/api/transactions').json();assert {k:data['summary'][k] for k in ['income_minor','expenses_minor','net_minor','count']}==dict(income_minor=0,expenses_minor=500,net_minor=-500,count=2)
    assert sorted(w['balance_minor'] for w in options(c)['wallets'])==[20000,79500]
    assert c.post('/api/transactions',json=p).json()['id']==x['id'];assert c.get('/api/transactions').json()['total']==2
    p.update(amount_minor=30000,fee_minor=1000,version=1,request_key=str(uuid4()));assert c.patch('/api/transactions/'+x['id'],json=p).status_code==200
    assert c.get('/api/transactions').json()['summary']['expenses_minor']==1000
    fee=next(t for t in c.get('/api/transactions').json()['items'] if t['linked_transfer_id']);assert c.request('DELETE','/api/transactions/'+fee['id'],json=dict(request_key=str(uuid4()),version=1)).status_code==409
    delete=dict(request_key=str(uuid4()),version=2);assert c.request('DELETE','/api/transactions/'+x['id'],json=delete).status_code==200
    assert c.request('DELETE','/api/transactions/'+x['id'],json=delete).status_code==200
    assert c.get('/api/transactions').json()['total']==0
    assert sorted(w['balance_minor'] for w in options(c)['wallets'])==[0,100000]

def test_validation_ownership_csrf_and_production_sample(tx,tmp_path):
    c,s,u=tx;w=wallet(c);d=wallet(c,'Bank',0,'bank')
    for amount in [0,-1,1.25,True,10000000000001]:assert c.post('/api/transactions',json=payload(w,amount=amount)).status_code==422
    assert c.post('/api/transactions',json=payload(w,'transfer',10,destination_wallet_id=w)).status_code==422
    assert c.post('/api/transactions',json=payload(w,'transfer',10,destination_wallet_id=d,mode='withdraw')).status_code==422
    assert c.post('/api/transactions',json=payload('not-owned')).status_code==422
    x=create(c,w)
    for method in ['patch','delete']:
        assert c.request(method.upper(),'/api/transactions/'+x['id'],headers={'Origin':'https://attacker.invalid'},json={}).status_code==403
    c.post('/api/auth/register',json=dict(full_name='Other User',email='other@example.com',password='Fincept!2026',confirm_password='Fincept!2026',accepted_terms=True))
    assert c.get('/api/transactions/'+x['id']).status_code==404
    assert c.patch('/api/transactions/'+x['id'],json=payload(w,version=1)).status_code==404
    assert c.request('DELETE','/api/transactions/'+x['id'],json=dict(request_key=str(uuid4()),version=1)).status_code==404
    assert c.get('/api/transactions').json()['total']==0
    assert c.post('/api/transactions',json=payload(w)).status_code==422
    c.post('/api/auth/logout');assert c.get('/api/transactions').status_code==401
    with TestClient(create_app(Settings(database_path=str(tmp_path/'prod.db'),environment='production',cookie_secure=True))) as prod:
        assert prod.get('/api/transactions?dataset=demo').status_code==403

def test_overdraft_future_payments_and_partial_failure_rollback(tx):
    c,_,_=tx;w=wallet(c,opening=10000);d=wallet(c,'Cash 2',0)
    today=date.today();later=(today+timedelta(days=1)).isoformat()+'T12:00:00'
    p=payload(w,amount=9000);p['occurred_at']=later;assert c.post('/api/transactions',json=p).status_code==201
    r=c.post('/api/transactions',json=payload(w,'transfer',1000,destination_wallet_id=d,fee_minor=1));assert r.status_code==409
    assert c.get('/api/transactions').json()['total']==1
    assert next(x for x in options(c)['wallets'] if x['id']==d)['balance_minor']==0
    income=create(c,w,'income',1000)
    create(c,w,amount=2000)
    assert c.request('DELETE','/api/transactions/'+income['id'],json=dict(request_key=str(uuid4()),version=1)).status_code==409
    assert c.get('/api/transactions/'+income['id']).status_code==200

def test_filters_sort_pagination_summary_date_scope_and_export(tx):
    c,_,_=tx;w=wallet(c,opening=10000000);d=wallet(c,'Bank',0,'bank')
    for n in range(28):create(c,w,amount=(n+1)*100)
    create(c,w,'income',10000);create(c,w,'transfer',500,destination_wallet_id=d)
    x=c.get('/api/transactions?limit=25&sort=highest').json();assert len(x['items'])==25 and x['total']==30
    assert x['items'][0]['amount_minor']==10000
    assert c.get('/api/transactions?page=2&limit=25').json()['items'].__len__()==5
    filtered=c.get('/api/transactions?kind=expense&minimum=2000&maximum=2500&sort=lowest').json();assert filtered['total']==6 and filtered['items'][0]['amount_minor']==2000
    assert filtered['summary']['count']==30 # date-scoped totals deliberately independent of table filters
    assert c.get('/api/transactions?wallet='+d).json()['total']==1
    assert c.get('/api/transactions?search=%25').json()['total']==0
    assert c.get('/api/transactions?maximum=100&minimum=200').status_code==422
    assert c.get('/api/transactions?sort=amount;DROP').status_code==422
    assert c.get('/api/transactions?limit=1000').status_code==422
    p=payload(w);p['title']='=HYPERLINK("evil")';p['description']='a,b\n"quote"';p['notes']='\t=2+3';create_r=c.post('/api/transactions',json=p);assert create_r.status_code==201
    export=c.get('/api/transactions/export?search=HYPERLINK');assert export.status_code==200 and export.headers['content-type'].startswith('text/csv')
    rows=list(csv.reader(io.StringIO(export.text.lstrip('\ufeff'))));assert len(rows)==2 and rows[1][1].startswith("'=") and rows[1][2]=='a,b\n"quote"' and rows[1][3].startswith("'=")

def test_categories_rename_reassign_protect_defaults(tx):
    c,_,_=tx;w=wallet(c);cat=c.post('/api/transactions/categories',json=dict(name='Coffee',kind='expense'));assert cat.status_code==201
    id=cat.json()['id'];assert c.post('/api/transactions/categories',json=dict(name=' coffee ',kind='expense')).status_code==409
    p=payload(w);p['category']='Coffee';x=c.post('/api/transactions',json=p).json()
    assert c.patch('/api/transactions/categories/'+id,json=dict(name='Cafe',kind='expense')).status_code==200
    saved=c.get('/api/transactions/'+x['id']).json();assert saved['category']=='Cafe' and saved['version']==2
    assert c.request('DELETE','/api/transactions/categories/'+id,json=dict(replacement='Missing')).status_code==422
    assert c.request('DELETE','/api/transactions/categories/'+id,json=dict(replacement='Food')).status_code==200
    assert c.get('/api/transactions/'+x['id']).json()['category']=='Food'
    assert c.request('DELETE','/api/transactions/categories/default:expense:Food',json=dict(replacement='Other')).status_code==404

def test_concurrent_debits_and_idempotent_conflicts(tx):
    c,_,_=tx;w=wallet(c,opening=1000);p=payload(w,amount=700)
    with ThreadPoolExecutor(max_workers=2) as pool:codes=list(pool.map(lambda _:c.post('/api/transactions',json=payload(w,amount=700)).status_code,range(2)))
    assert sorted(codes)==[201,409]
    p=payload(w,amount=100);assert c.post('/api/transactions',json=p).status_code==201
    p['amount_minor']=200;assert c.post('/api/transactions',json=p).status_code==409

def test_migration_restart_preserves_existing_rows_and_demo_isolation(tx):
    c,s,u=tx;w=wallet(c);x=create(c,w)
    c.post('/api/overview/demo');assert c.get('/api/transactions?dataset=demo').json()['total']==48
    assert c.get('/api/transactions').json()['total']==1
    with TestClient(create_app(s)) as other:
        with sqlite3.connect(s.database_path) as db:
            assert db.execute('PRAGMA user_version').fetchone()[0]==12
            assert db.execute('SELECT title FROM transactions WHERE id=?',(x['id'],)).fetchone()[0]=='Test record'

def test_withdrawal_date_filters_archived_wallet_and_locked_kind(tx):
    c,s,u=tx;bank=wallet(c,'Bank',100000,'bank');cash=wallet(c,'Cash',0,'cash')
    x=create(c,bank,'transfer',10000,destination_wallet_id=cash,mode='withdraw',fee_minor=100)
    assert x['mode']=='withdraw' and x['destination_wallet_id']==cash
    summary=c.get('/api/transactions?start='+date.today().isoformat()+'&end='+date.today().isoformat()).json()
    assert summary['total']==2 and summary['summary']['income_minor']==0 and summary['summary']['expenses_minor']==100
    yesterday=(date.today()-timedelta(days=1)).isoformat()
    assert c.get('/api/transactions?start='+yesterday+'&end='+yesterday).json()['total']==0
    with sqlite3.connect(s.database_path) as db:db.execute('UPDATE wallet_metadata SET archived=1 WHERE wallet_id=?',(bank,))
    assert c.post('/api/transactions',json=payload(bank)).status_code==422
    p=payload(cash,'income',100,version=1)
    assert c.patch('/api/transactions/'+x['id'],json=p).status_code==422
    assert c.get('/api/transactions?dataset=invalid').status_code==422

def test_upgrade_actual_version_two_database_without_metadata(tx):
    c,s,u=tx;w=wallet(c);x=create(c,w)
    # Simulate an existing v2 installation: its six/twelve-column canonical rows remain intact.
    with sqlite3.connect(s.database_path) as db:
        for table in ['wallet_events','wallet_profiles','category_appearance','financial_requests','custom_categories','transaction_metadata','wallet_metadata']:db.execute('DROP TABLE '+table)
        db.execute('PRAGMA user_version=2')
    with TestClient(create_app(s)):
        with sqlite3.connect(s.database_path) as db:
            assert db.execute('PRAGMA user_version').fetchone()[0]==12
            assert db.execute('SELECT amount_minor FROM transactions WHERE id=?',(x['id'],)).fetchone()[0]==1000
            assert len(db.execute('PRAGMA table_info(transactions)').fetchall())==12
            assert db.execute('SELECT name FROM wallets WHERE id=?',(w,)).fetchone()[0]=='Cash'


def test_category_appearance_persists_and_rename_preserves_it(tx):
    c,s,u=tx
    created=c.post('/api/transactions/categories',json=dict(name='Weekend dining',kind='expense',icon='calendar',color='#5378c8'))
    assert created.status_code==201,created.text
    id=created.json()['id']
    saved=next(x for x in options(c)['categories'] if x['id']==id)
    assert (saved['icon'],saved['color'])==('calendar','#5378c8')
    assert c.patch('/api/transactions/categories/'+id,json=dict(name='Dining out',kind='expense')).status_code==200
    saved=next(x for x in options(c)['categories'] if x['id']==id)
    assert (saved['name'],saved['icon'],saved['color'])==('Dining out','calendar','#5378c8')
    with sqlite3.connect(s.database_path) as db:
        assert db.execute('SELECT icon,color FROM category_appearance WHERE category_id=?',(id,)).fetchone()==('calendar','#5378c8')
    assert c.request('DELETE','/api/transactions/categories/'+id,json={'replacement':'Food'}).status_code==200
    with sqlite3.connect(s.database_path) as db:assert db.execute('SELECT COUNT(*) FROM category_appearance WHERE category_id=?',(id,)).fetchone()[0]==0


def test_category_appearance_validates_allowlisted_values_and_existing_categories(tx):
    c,s,u=tx
    for change in [dict(icon='../../escape'),dict(color='url(https://example.com)'),dict(color='#ffffff')]:
        response=c.post('/api/transactions/categories',json=dict(name='Bad category',kind='expense',**change))
        assert response.status_code==422
    made=c.post('/api/transactions/categories',json=dict(name='Legacy category',kind='income')).json()['id']
    with sqlite3.connect(s.database_path) as db:db.execute('DELETE FROM category_appearance WHERE category_id=?',(made,))
    saved=next(x for x in options(c)['categories'] if x['id']==made)
    assert (saved['icon'],saved['color'])==('receipt','#f9733b')
