from datetime import date,timedelta
from uuid import uuid4
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import pytest
from test_transactions import tx,wallet,payload
from app.finance.goal_service import metrics

@pytest.mark.parametrize('target,saved,state,status,pct,remaining',[(0,0,'active','In Progress',None,0),(0,10,'active','In Progress',None,-10),(100,0,'active','In Progress',0,100),(100,40,'active','In Progress',40,60),(100,40,'paused','Paused',40,60),(100,100,'active','Completed',100,0),(100,125,'active','Completed',125,-25)])
def test_metrics(target,saved,state,status,pct,remaining):
    m=metrics(target,saved,state);assert (m['status'],m['percentage'],m['remaining_minor'])==(status,pct,remaining)
def form(**kw):
    return dict(request_key=str(uuid4()),name='Emergency Fund',category='Emergency Fund',target_minor=100000,target_date=(date.today()+timedelta(days=180)).isoformat(),monthly_minor=10000,description='Safety net',icon='shield')|kw
def goal(c,**kw):
    r=c.post('/api/goals',json=form(**kw));assert r.status_code==201,r.text;return r.json()['id']
def listing(c,**kw):
    r=c.get('/api/goals',params=kw);assert r.status_code==200,r.text;return r.json()
def contribution(c,id,w,amount=1000,method='allocation',**kw):
    g=c.get('/api/goals/'+id).json()['goal'];p=dict(request_key=str(uuid4()),version=g['version'],wallet_id=w,amount_minor=amount,method=method,date=date.today().isoformat(),note='Monthly savings',limit_to_target=True)|kw
    r=c.post('/api/goals/'+id+'/contributions/preview',json=p);assert r.status_code==200,r.text;v=r.json();return p|dict(expected_balance_minor=v['wallet']['balance_minor'],expected_allocated_minor=v['wallet']['allocated_minor'])

def test_crud_contributions_summaries_and_overview(tx):
    c,s,u=tx;w=wallet(c);g=goal(c);p=contribution(c,g,w,40000)
    r=c.post('/api/goals/'+g+'/contributions',json=p);assert r.status_code==201,r.text
    assert c.post('/api/goals/'+g+'/contributions',json=p).json()==r.json()
    a=listing(c);assert (a['summary']['target_minor'],a['summary']['saved_minor'],a['summary']['remaining_minor'])==(100000,40000,60000)
    assert c.get('/api/goals/'+g).json()['total']==1
    assert c.get('/api/wallets').json()['summary']['total']['balance_minor']==100000
    overview=c.get('/api/overview/summary').json();assert overview['goals'][0]['saved']==400 and overview['summary']['income']==0
    p=form(version=2,target_minor=120000);assert c.patch('/api/goals/'+g,json=p).status_code==200
    assert c.patch('/api/goals/'+g,json=p).status_code==200
    p['request_key']=str(uuid4());assert c.patch('/api/goals/'+g,json=p).status_code==409
    with sqlite3.connect(s.database_path) as db:assert db.execute('SELECT saved_minor,target_minor FROM financial_goals WHERE id=?',(g,)).fetchone()==(40000,120000)
    assert c.get('/api/goals/options').json()['wallets'][0]['available_minor']==60000

def test_external_atomic_single_event_no_income_delete_releases(tx):
    c,s,u=tx;w=wallet(c);g=goal(c);p=contribution(c,g,w,25000,'external');a=c.post('/api/goals/'+g+'/contributions',json=p);assert a.status_code==201,a.text
    assert c.post('/api/goals/'+g+'/contributions',json=p).json()==a.json()
    assert c.get('/api/wallets').json()['summary']['total']['balance_minor']==125000
    assert c.get('/api/overview/summary').json()['summary']['income']==0
    assert c.get('/api/goals/options').json()['wallets'][0]['available_minor']==100000
    delete=dict(request_key=str(uuid4()),version=2);assert c.request('DELETE','/api/goals/'+g,json=delete).status_code==200
    assert c.request('DELETE','/api/goals/'+g,json=delete).status_code==200
    assert listing(c)['total']==0 and listing(c,scope='archived')['total']==1
    assert c.get('/api/goals/'+g).json()['total']==1
    assert c.get('/api/goals/options').json()['wallets'][0]['available_minor']==125000
    with sqlite3.connect(s.database_path) as db:
        assert db.execute('SELECT count(*) FROM wallet_events WHERE id=?',(a.json()['wallet_event_id'],)).fetchone()[0]==1
        assert db.execute('SELECT count(*) FROM transactions').fetchone()[0]==0

def test_pause_resume_complete_overfund_edit_preserves_history(tx):
    c,s,u=tx;w=wallet(c,opening=200000);g=goal(c);p=contribution(c,g,w,20000);assert c.post('/api/goals/'+g+'/contributions',json=p).status_code==201
    def state(v,state):return c.post('/api/goals/'+g+'/state',json=dict(request_key=str(uuid4()),version=v,state=state))
    assert state(2,'paused').status_code==200 and listing(c)['summary']['active_count']==0
    assert c.post('/api/goals/'+g+'/contributions/preview',json=p|dict(request_key=str(uuid4()),version=3)).status_code==409
    assert state(3,'active').status_code==200
    p=contribution(c,g,w,90000,limit_to_target=False);assert c.post('/api/goals/'+g+'/contributions',json=p).status_code==201
    m=listing(c)['items'][0];assert (m['status'],m['remaining_minor'],m['percentage'])==('Completed',-10000,110)
    assert listing(c)['summary']['active_count']==0 and listing(c,status='Completed')['filtered_count']==1
    assert state(5,'paused').status_code==409
    assert c.patch('/api/goals/'+g,json=form(target_minor=150000,version=5)).status_code==200
    assert listing(c)['items'][0]['saved_minor']==110000 and listing(c)['summary']['active_count']==1
    assert c.get('/api/goals/'+g).json()['total']==2

def test_invalid_dates_amounts_ownership_csrf(tx):
    c,s,u=tx;g=goal(c);w=wallet(c)
    for changes in [dict(target_minor=0),dict(target_minor=1.5),dict(category='Invalid'),dict(currency='USD'),dict(target_date='2200-01-01'),dict(name=' ')]:assert c.post('/api/goals',json=form(**changes)).status_code==422
    p=contribution(c,g,w)
    for changes in [dict(amount_minor=0),dict(amount_minor=1.1),dict(date=(date.today()+timedelta(days=1)).isoformat()),dict(wallet_id='not-owned'),dict(amount_minor=200000),dict(version=999),dict(method='income')]:
        r=c.post('/api/goals/'+g+'/contributions/preview',json=p|changes|dict(request_key=str(uuid4())));assert r.status_code in (404,409,422),r.text
    no_review=p.copy();no_review.pop('expected_balance_minor');assert c.post('/api/goals/'+g+'/contributions',json=no_review).status_code==422
    assert c.post('/api/goals/'+g+'/contributions',params={'dataset':'demo'},json=p).status_code==404
    c.headers['Origin']='https://bad.example';assert c.post('/api/goals',json=form()).status_code==403;c.headers['Origin']='http://localhost:5173'
    c.post('/api/auth/logout');assert c.get('/api/goals').status_code==401
    c.post('/api/auth/register',json=dict(full_name='Other User',email='other-goals@example.com',password='Fincept!2026',confirm_password='Fincept!2026',accepted_terms=True))
    assert c.get('/api/goals/'+g).status_code==404
    assert c.patch('/api/goals/'+g,json=form(version=1)).status_code==404
    assert c.post('/api/goals/'+g+'/contributions',json=p).status_code==404

def test_review_stale_wallet_and_forced_late_failure_rolls_back_deposit(tx):
    c,s,u=tx;w=wallet(c);g=goal(c);p=contribution(c,g,w,20000,'external')
    assert c.post('/api/transactions',json=payload(w,amount=1000)).status_code==201
    assert c.post('/api/goals/'+g+'/contributions',json=p).status_code==409
    p=contribution(c,g,w,20000,'external')
    with sqlite3.connect(s.database_path) as db:db.execute("CREATE TRIGGER reject_goal_insert BEFORE INSERT ON goal_contributions BEGIN SELECT RAISE(ABORT,'forced audit failure'); END")
    from fastapi.testclient import TestClient
    from app.main import create_app
    with TestClient(create_app(s),raise_server_exceptions=False) as other:
        other.cookies.update(c.cookies);other.headers.update(c.headers);assert other.post('/api/goals/'+g+'/contributions',json=p).status_code==500
    with sqlite3.connect(s.database_path) as db:
        assert db.execute('SELECT count(*) FROM wallet_events').fetchone()[0]==0
        assert db.execute('SELECT saved_minor FROM financial_goals WHERE id=?',(g,)).fetchone()[0]==0

def test_parallel_goals_cannot_allocate_wallet_twice(tx):
    c,s,u=tx;w=wallet(c);a=goal(c);b=goal(c,name='Travel',category='Travel');p=contribution(c,a,w,70000);q=contribution(c,b,w,70000)
    from fastapi.testclient import TestClient
    from app.main import create_app
    def run(args):
        id,data=args
        with TestClient(create_app(s)) as x:
            x.cookies.update(c.cookies);x.headers.update(c.headers);return x.post('/api/goals/'+id+'/contributions',json=data).status_code
    with ThreadPoolExecutor(2) as ex:results=list(ex.map(run,[(a,p),(b,q)]))
    assert sorted(results)==[201,409] and listing(c)['summary']['saved_minor']==70000
    assert c.get('/api/goals/options').json()['wallets'][0]['available_minor']==30000

def test_legacy_v6_preserved_unlinked_funding(tx):
    c,s,u=tx;wallet(c)
    with sqlite3.connect(s.database_path) as db:
        db.execute('DROP TABLE goal_contributions');db.execute('DROP TABLE goal_metadata')
        db.execute("INSERT INTO financial_goals VALUES ('legacy',?,'live','Imported',4000,10000,NULL)",(u['id'],));db.execute('PRAGMA user_version=6')
    from fastapi.testclient import TestClient
    from app.main import create_app
    with TestClient(create_app(s)) as x:
        x.cookies.update(c.cookies);x.headers.update(c.headers)
        assert x.get('/api/goals/legacy').json()['goal']['legacy_unlinked_minor']==4000
        assert x.patch('/api/goals/legacy',json=form(version=1,target_minor=10000)).status_code==200
        assert x.get('/api/goals/legacy').json()['items'][0]['method']=='legacy'
        assert x.get('/api/goals/options').json()['wallets'][0]['allocated_minor']==0
    with sqlite3.connect(s.database_path) as db:assert db.execute('PRAGMA user_version').fetchone()[0]==12

def test_dates_key_collision_paging_search(tx):
    c,s,u=tx;w=wallet(c);g=goal(c);p=contribution(c,g,w,1000,date=date.today().replace(day=1).isoformat())
    assert c.post('/api/goals/'+g+'/contributions',json=p).status_code==201
    p['amount_minor']=2000;assert c.post('/api/goals/'+g+'/contributions',json=p).status_code==409
    p=contribution(c,g,w,1000);assert c.post('/api/goals/'+g+'/contributions',json=p).status_code==201
    assert c.get('/api/goals/'+g+'?page=2&limit=1').json()['total']==2
    assert listing(c,search='safety',sort='target')['filtered_count']==1
    assert listing(c,category='Travel')['filtered_count']==0
    assert c.get('/api/goals/'+g+'?limit=0').status_code==422


def test_earmarks_expose_coverage_shortfall_and_inactive_wallet_rejection(tx):
    c,s,u=tx;w=wallet(c);g=goal(c);p=contribution(c,g,w,80000)
    assert c.post('/api/goals/'+g+'/contributions',json=p).status_code==201
    q=payload(w,amount=50000);q['occurred_at']=date.today().isoformat()+'T00:00:00'
    assert c.post('/api/transactions',json=q).status_code==201
    funds=c.get('/api/goals/options').json()['wallets'][0]
    assert (funds['balance_minor'],funds['allocated_minor'],funds['available_minor'],funds['coverage_shortfall_minor'])==(50000,80000,0,30000)
    fresh=dict(request_key=str(uuid4()),version=2,wallet_id=w,amount_minor=1000,method='allocation',date=date.today().isoformat())
    assert c.post('/api/goals/'+g+'/contributions/preview',json=fresh).status_code==409
    with sqlite3.connect(s.database_path) as db:
        db.execute("INSERT OR IGNORE INTO wallet_profiles(wallet_id,created_at,updated_at) VALUES (?,'2026-01-01','2026-01-01')",(w,))
        db.execute("UPDATE wallet_profiles SET status='inactive' WHERE wallet_id=?",(w,))
    assert c.post('/api/goals/'+g+'/contributions/preview',json=fresh|dict(method='external')).status_code==422
    assert c.get('/api/goals/'+g).json()['goal']['saved_minor']==80000

def test_production_demo_disabled(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import Settings,create_app
    with TestClient(create_app(Settings(database_path=str(tmp_path/'prod-goals.db'),environment='production',cookie_secure=True)),base_url='https://testserver') as c:
        assert c.get('/api/goals?dataset=demo').status_code==403
        assert c.get('/api/goals/options?dataset=demo').status_code==403
