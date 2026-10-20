"""Real SQLite budget CRUD, shared calculations, allocation and ownership regressions."""
from datetime import date,timedelta
from uuid import uuid4
import sqlite3
import pytest
from test_transactions import tx,wallet,payload
from app.finance.budget_service import metrics,month_range

@pytest.mark.parametrize('limit,spent,status,pct,remaining,risk',[(0,0,'On Track',None,0,False),(0,1,'Exceeded',None,-1,True),(10000,0,'On Track',0,10000,False),(10000,7499,'On Track',74.99,2501,False),(10000,7500,'On Track',75,2500,True),(10000,8500,'Near Limit',85,1500,True),(10000,10000,'Near Limit',100,0,True),(10000,12000,'Exceeded',120,-2000,True)])
def test_metrics(limit,spent,status,pct,remaining,risk):
    r=metrics(limit,spent);assert (r['status'],r['percentage'],r['remaining_minor'],r['at_risk'])==(status,pct,remaining,risk)

def form(**kw):
    first,last=month_range();return dict(request_key=str(uuid4()),name='Food & Dining',category='Food',limit_minor=10000,start_date=first,end_date=last,reset_period='monthly',alert_threshold=75,notes='Monthly plan',**kw)
def budget(c,p=None):
    r=c.post('/api/budgets',json=p or form());assert r.status_code==201,r.text;return r.json()
def list_(c,**kw):
    r=c.get('/api/budgets',params=kw);assert r.status_code==200,r.text;return r.json()
def expense(c,w,amount=1000,**kw):
    p=payload(w,amount=amount);p.update(kw);r=c.post('/api/transactions',json=p);assert r.status_code==201,r.text;return r.json()

def test_crud_persistence_replay_version_and_history(tx):
    c,s,u=tx;w=wallet(c);t=expense(c,w,8500);p=form();b=budget(c,p)
    assert c.post('/api/budgets',json=p).json()==b
    data=list_(c);assert data['total']==1 and data['summary']['spent_minor']==8500
    assert data['items'][0]['status']=='Near Limit' and data['summary']['risk_count']==1
    with sqlite3.connect(s.database_path) as db:assert db.execute('SELECT limit_minor FROM budgets WHERE id=?',(b['id'],)).fetchone()[0]==10000
    p.update(request_key=str(uuid4()),version=1,limit_minor=20000)
    r=c.patch('/api/budgets/'+b['id'],json=p);assert r.status_code==200,r.text
    assert c.patch('/api/budgets/'+b['id'],json=p).json()['version']==2
    p['request_key']=str(uuid4());assert c.patch('/api/budgets/'+b['id'],json=p).status_code==409
    assert list_(c)['items'][0]['remaining_minor']==11500
    assert c.request('DELETE','/api/budgets/'+b['id'],json=dict(request_key=str(uuid4()),version=1)).status_code==409
    delete=dict(request_key=str(uuid4()),version=2)
    assert c.request('DELETE','/api/budgets/'+b['id'],json=delete).status_code==200
    assert c.request('DELETE','/api/budgets/'+b['id'],json=delete).status_code==200
    assert list_(c)['summary']['limit_minor']==0
    assert c.get('/api/transactions/'+t['id']).status_code==200
    with sqlite3.connect(s.database_path) as db:
        assert db.execute('SELECT count(*) FROM budget_metadata WHERE budget_id=?',(b['id'],)).fetchone()[0]==0
        assert db.execute('PRAGMA user_version').fetchone()[0]==12

def test_filters_summary_period_boundaries_and_exclusions(tx):
    c,s,u=tx;w=wallet(c,opening=1000000);d=wallet(c,'Savings',0,'savings');first,last=month_range();a=date.fromisoformat(first)
    # Extend opening to test both inclusive boundaries without altering production rules.
    with sqlite3.connect(s.database_path) as db:db.execute('UPDATE wallets SET opening_date=? WHERE id=?',((a-timedelta(days=40)).isoformat(),w))
    expense(c,w,2000,occurred_at=first+'T00:00:00');expense(c,w,3000,occurred_at=last+'T23:59:59')
    expense(c,w,9000,occurred_at=(a-timedelta(days=1)).isoformat()+'T12:00:00')
    expense(c,w,8000,category='Shopping');expense(c,w,5000,kind='income',category='Salary')
    expense(c,w,10000,kind='transfer',category='',destination_wallet_id=d)
    food=budget(c);p=form();p.update(category='Shopping',name='Shopping');budget(c,p)
    data=list_(c);assert data['summary']['spent_minor']==13000 and data['summary']['limit_minor']==20000
    assert list_(c,search='shopping')['filtered_count']==1
    assert list_(c,category='Food')['summary']==data['summary']
    assert list_(c,status='On Track')['filtered_count']==2
    assert list_(c,sort='name')['items'][0]['name']=='Food & Dining'
    detail=c.get('/api/budgets/'+food['id'],params={'limit':1,'page':2}).json();assert detail['total']==2 and len(detail['items'])==1
    prev=(a-timedelta(days=1)).strftime('%Y-%m');assert list_(c,month=prev)['total']==0
    ov=c.get('/api/overview/summary').json()
    assert sum(b['spent'] for b in ov['budgets'])==130
    assert ov['budgets'][0]['percentage']==50
    with sqlite3.connect(s.database_path) as db:
        from app.finance.budget_service import evaluate
        db.row_factory=sqlite3.Row
        same=evaluate(db,u['id'],'live',first,last)
        assert same['summary']['spent_minor']==13000

def test_validation_category_overlap_and_isolation(tx):
    c,_,_=tx;created=budget(c)
    assert c.post('/api/budgets',json=form()).status_code==409
    for field,value in [('limit_minor',0),('limit_minor',True),('limit_minor',1.25),('limit_minor',10000000000001),('category','Not my category'),('name','  '),('end_date','1900-01-01'),('alert_threshold',85),('reset_period','yearly')]:
        p=form();p[field]=value;assert c.post('/api/budgets',json=p).status_code==422,(field,value)
    assert c.get('/api/budgets',params={'month':'2026-99'}).status_code==422
    assert c.get('/api/budgets',params={'sort':'unknown'}).status_code==422
    assert c.get('/api/budgets/'+created['id']+'?dataset=demo').status_code==404
    assert c.post('/api/budgets',headers={'Origin':'https://attacker.invalid'},json=form()).status_code==403
    c.post('/api/auth/register',json=dict(full_name='Other Budget User',email='other-budget@example.com',password='Fincept!2026',confirm_password='Fincept!2026',accepted_terms=True))
    assert c.get('/api/budgets/'+created['id']).status_code==404
    assert c.patch('/api/budgets/'+created['id'],json=form(version=1)).status_code==404
    assert c.request('DELETE','/api/budgets/'+created['id'],json=dict(request_key=str(uuid4()),version=1)).status_code==404
    assert list_(c)['total']==0
    c.post('/api/auth/logout');assert c.get('/api/budgets').status_code==401

def test_legacy_overlap_is_explicit_and_not_double_counted(tx):
    c,s,u=tx;w=wallet(c);expense(c,w,1000);b=budget(c);first,last=month_range()
    with sqlite3.connect(s.database_path) as db:
        db.execute('INSERT INTO budgets VALUES (?,?,?,?,?,?,?,?)',('legacy',u['id'],'live','Legacy','Food',0,first,last))
    data=list_(c);assert data['ambiguous_count']==1 and data['summary']['spent_minor']==0
    assert all(b['conflicted'] for b in data['items'])
    assert c.get('/api/budgets/'+b['id']).json()['total']==0
    c.request('DELETE','/api/budgets/legacy',json=dict(request_key=str(uuid4()),version=1))
    assert list_(c)['summary']['spent_minor']==1000

def test_weekly_custom_threshold_off_and_exact_category_matching(tx):
    c,_,_=tx;w=wallet(c);expense(c,w,8000,category='Food & Dining')
    p=form();p.update(reset_period='weekly',end_date=(date.fromisoformat(p['start_date'])+timedelta(days=6)).isoformat(),alert_threshold=None)
    b=budget(c,p);assert list_(c)['summary']['spent_minor']==0
    p.update(category='Food & Dining',reset_period='custom',end_date=month_range()[1],version=1,request_key=str(uuid4()))
    assert c.patch('/api/budgets/'+b['id'],json=p).status_code==200
    data=list_(c);assert data['summary']['spent_minor']==8000 and data['summary']['risk_count']==0
    p.update(limit_minor=7000,version=2,request_key=str(uuid4()));assert c.patch('/api/budgets/'+b['id'],json=p).status_code==200
    assert list_(c)['summary']['risk_count']==1

def test_new_periods_do_not_renew_or_rewrite_history(tx):
    c,_,_=tx;p=form();one=budget(c,p);p.update(start_date='2099-02-01',end_date='2099-02-28',request_key=str(uuid4()))
    two=budget(c,p);assert one['id']!=two['id'];assert list_(c,month='2099-02')['total']==1
    assert list_(c,month='2099-03')['total']==0

def test_atomic_overlap_guard_and_key_collision(tx):
    from concurrent.futures import ThreadPoolExecutor
    c,_,_=tx
    def attempt(_):return c.post('/api/budgets',json=form()).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(attempt,range(2)))
    assert sorted(results)==[201,409]
    assert list_(c)['total']==1
    p=form();p.update(category='Health',name='Health');budget(c,p)
    p['limit_minor']=20000
    assert c.post('/api/budgets',json=p).status_code==409

def test_production_demo_is_disabled(tmp_path):
    from app.main import Settings,create_app
    from fastapi.testclient import TestClient
    with TestClient(create_app(Settings(database_path=str(tmp_path/'production.sqlite3'),environment='production',cookie_secure=True,frontend_origins=('https://testserver',)))) as c:
        c.base_url='https://testserver'
        c.headers.update({'X-Fincept-Request':'1','Origin':'https://testserver'})
        r=c.post('/api/auth/register',json=dict(full_name='Production User',email='production-budget@example.com',password='Fincept!2026',confirm_password='Fincept!2026',accepted_terms=True))
        assert r.status_code==201,r.text
        assert c.get('/api/budgets?dataset=demo').status_code==403

def test_v5_migration_preserves_canonical_budget_and_transactions(tx):
    c,s,u=tx;w=wallet(c);expense(c,w,1000);first,last=month_range()
    with sqlite3.connect(s.database_path) as db:
        db.row_factory=sqlite3.Row
        db.execute('INSERT INTO budgets VALUES (?,?,?,?,?,?,?,?)',('v5-budget',u['id'],'live','Legacy plan','Food',0,first,last))
        before=[tuple(r) for r in db.execute('SELECT * FROM transactions')]
        db.execute('DROP TABLE budget_metadata');db.execute('PRAGMA user_version=5')
        from app.finance.schema import initialize
        initialize(db)
        assert db.execute('PRAGMA user_version').fetchone()[0]==7
        assert [tuple(r) for r in db.execute('SELECT * FROM transactions')]==before
    data=list_(c);assert data['items'][0]['id']=='v5-budget' and data['items'][0]['percentage'] is None
    assert data['items'][0]['status']=='Exceeded' and data['summary']['remaining_minor']==-1000
