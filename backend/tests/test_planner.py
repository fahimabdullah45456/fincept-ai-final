"""Real SQLite/HTTP tests, no Planner persistence mocks."""
from datetime import date
from uuid import uuid4
import sqlite3
import pytest
from fastapi.testclient import TestClient
from app.main import Settings,create_app
from app.planner.routes import estimate

H={'X-Fincept-Request':'1','Origin':'http://localhost:5173'}
def account(c,email=None):
    r=c.post('/api/auth/register',headers=H,json=dict(full_name='Planner User',email=email or str(uuid4())+'@example.com',password='Fincept!2026',confirm_password='Fincept!2026',accepted_terms=True))
    assert r.status_code==201,r.text
    return r.json()['user']
@pytest.fixture
def setup(tmp_path):
    path=str(tmp_path/'planner.sqlite3');app=create_app(Settings(database_path=path))
    with TestClient(app) as c:
        c.headers.update(H);u=account(c);yield c,path,u,app

def task(**kw):return dict(request_key=str(uuid4()),title='Prepare birthday gift',due_date='2028-02-29',category='Occasion Preparation',priority='High',**kw)
def plan(**kw):return dict(request_key=str(uuid4()),name='Birthday Fund',occasion_type='Birthday',occasion_date='2028-12-15',start_date='2026-10-15',target_minor=1200000,frequency='Monthly',planned_minor=220000,**kw)
def post_task(c,p=None):
    r=c.post('/api/planner/tasks',json=p or task());assert r.status_code==201,r.text;return r.json()
def post_plan(c,p=None):
    r=c.post('/api/planner/plans',json=p or plan());assert r.status_code==201,r.text;return r.json()['id']
def listing(c,month='2028-02',**kw):
    r=c.get('/api/planner',params=dict(month=month,timezone='Asia/Dhaka',**kw));assert r.status_code==200,r.text;return r.json()

def test_empty_migration_and_existing_rows(setup):
    c,path,u,_=setup
    x=listing(c);assert x['items']==[] and x['plans']==[]
    assert x['summary']==dict(upcoming_tasks=0,overdue_tasks=0,upcoming_occasions=0,target_minor=0,saved_minor=0,remaining_minor=0)
    assert x['range_start']=='2028-01-31' and x['range_end']=='2028-03-05'
    with sqlite3.connect(path) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0]==12
        assert db.execute('SELECT count(*) FROM users').fetchone()[0]==1
        assert db.execute('SELECT count(*) FROM transactions').fetchone()[0]==0

def test_task_lifecycle_replay_versions_and_no_transaction(setup):
    c,path,_,_=setup;p=task(due_time='09:30',timezone='America/New_York');t=post_task(c,p)
    assert post_task(c,p)['id']==t['id']
    assert listing(c)['items'][0]['due_date']=='2028-02-29'
    edit=p|dict(request_key=str(uuid4()),version=1,title='Edited birthday gift',due_date='2028-03-01',status='In Progress')
    r=c.patch('/api/planner/tasks/'+t['id'],json=edit);assert r.status_code==200,r.text
    assert listing(c)['items'][0]['due_date']=='2028-03-01' # adjacent day in grid, not lost
    assert c.get('/api/planner/tasks/'+t['id']).json()['title']=='Edited birthday gift'
    edit['request_key']=str(uuid4());assert c.patch('/api/planner/tasks/'+t['id'],json=edit).status_code==409
    state=dict(request_key=str(uuid4()),version=2,status='Completed');url='/api/planner/tasks/'+t['id']+'/status'
    assert c.post(url,json=state).json()['status']=='Completed';assert c.post(url,json=state).status_code==200
    assert listing(c,status='Completed')['items'][0]['id']==t['id']
    delete=dict(request_key=str(uuid4()),version=3);url='/api/planner/tasks/'+t['id']
    assert c.request('DELETE',url,json=delete).status_code==200;assert c.request('DELETE',url,json=delete).status_code==200
    assert c.get(url).status_code==404 and not listing(c)['items']
    with sqlite3.connect(path) as db:assert db.execute('SELECT count(*) FROM transactions').fetchone()[0]==0

def test_date_category_status_search_filters_and_global_summary(setup):
    c,_,_,_=setup
    for title,due,status in [('Overdue','1901-01-01','To Do'),('Upcoming','2100-01-01','In Progress'),('Done','2100-01-02','Completed'),('Cancelled','2100-01-03','Cancelled')]:
        post_task(c,task()|dict(title=title,due_date=due,status=status))
    x=listing(c,'2100-01');assert x['summary']['upcoming_tasks']==1 and x['summary']['overdue_tasks']==1
    assert len(x['items'])==3 and len(listing(c,'2100-01',status='Cancelled')['items'])==1
    assert listing(c,'1901-01',status='Overdue')['items'][0]['title']=='Overdue'
    assert listing(c,'2100-01',search='upcoming',category='Occasion Preparation')['items'][0]['title']=='Upcoming'
    assert not listing(c,'2100-01',category='Personal')['items']
    assert listing(c,'2100-01',search='nothing')['summary']==x['summary']

@pytest.mark.parametrize('patch',[{'title':'   '},{'due_date':'2027-02-29'},{'due_date':'2028-02-30'},{'due_date':'1800-01-01'},{'due_time':'24:00'},{'timezone':'Invalid/Zone'},{'status':'Invalid'},{'priority':'Urgent'},{'category':'Missing'},{'reminder':'tomorrow'}])
def test_invalid_task_values(setup,patch):
    c,_,_,_=setup;assert c.post('/api/planner/tasks',json=task()|patch).status_code==422

@pytest.mark.parametrize('month',['2028-13','1800-01','2101-01','2028-2','bad'])
def test_bad_months(setup,month):
    c,_,_,_=setup;assert c.get('/api/planner',params={'month':month}).status_code==422

def test_plan_linking_edit_archive_and_canonical_totals(setup):
    c,path,u,_=setup;p=plan();id=post_plan(c,p);assert post_plan(c,p)==id
    t=post_task(c,task(plan_id=id));x=listing(c);g=x['plans'][0]
    assert g['saved_minor']==0 and x['summary']['target_minor']==1200000
    assert c.get('/api/goals/'+id).json()['goal']['id']==id
    edit=p|dict(request_key=str(uuid4()),version=1,name='Wedding Fund',occasion_type='Wedding',target_minor=1500000)
    assert c.patch('/api/planner/plans/'+id,json=edit).status_code==200
    assert c.patch('/api/planner/plans/'+id,json=edit).status_code==200
    assert c.get('/api/planner/plans/'+id).json()['name']=='Wedding Fund'
    edit['request_key']=str(uuid4());assert c.patch('/api/planner/plans/'+id,json=edit).status_code==409
    assert c.request('DELETE','/api/goals/'+id,json=dict(request_key=str(uuid4()),version=2)).status_code==200
    assert listing(c)['summary']['target_minor']==0 and listing(c)['plans'][0]['archived']==1
    assert c.get('/api/planner/tasks/'+t['id']).status_code==200
    assert c.post('/api/planner/tasks',json=task(plan_id=id)).status_code==422
    with sqlite3.connect(path) as db:assert db.execute('SELECT count(*) FROM financial_goals').fetchone()[0]==1

def test_real_reviewed_allocation_changes_planner_and_no_new_assets(setup):
    c,path,u,_=setup;id=post_plan(c)
    r=c.post('/api/transactions/wallets',json=dict(request_key=str(uuid4()),name='Main bank',kind='bank',currency='BDT',opening_minor=1000000,opening_date=date.today().isoformat()))
    assert r.status_code==201,r.text
    wallet=r.json()['id'];body=dict(request_key=str(uuid4()),version=1,method='allocation',wallet_id=wallet,amount_minor=200000,date=date.today().isoformat(),limit_to_target=True)
    pre=c.post('/api/goals/'+id+'/contributions/preview',json=body);assert pre.status_code==200,pre.text
    w=pre.json()['wallet'];body|=dict(expected_balance_minor=w['balance_minor'],expected_allocated_minor=w['allocated_minor'])
    r=c.post('/api/goals/'+id+'/contributions',json=body);assert r.status_code==201,r.text
    x=listing(c);assert x['summary']['saved_minor']==200000 and x['summary']['remaining_minor']==1000000
    assert c.get('/api/goals/options').json()['wallets'][0]['balance_minor']==1000000
    assert c.get('/api/goals/options').json()['wallets'][0]['available_minor']==800000
    with sqlite3.connect(path) as db:assert db.execute('SELECT count(*) FROM transactions').fetchone()[0]==0

@pytest.mark.parametrize('patch',[{'name':' '},{'target_minor':0},{'target_minor':2.5},{'occasion_date':'2027-02-29'},{'start_date':'2029-01-01'},{'occasion_type':'Custom','custom_type':''},{'occasion_type':'Unsupported'},{'already_saved_minor':1000}])
def test_invalid_plan(setup,patch):
    c,_,_,_=setup;assert c.post('/api/planner/plans',json=plan()|patch).status_code==422

def test_auth_owner_dataset_csrf_and_foreign_link(setup):
    c,path,u,app=setup;pid=post_plan(c);t=post_task(c,task(plan_id=pid));url='/api/planner/tasks/'+t['id']
    assert c.get(url+'?dataset=demo').status_code==404
    assert c.post('/api/planner/tasks',json=task(plan_id=pid),params={'dataset':'demo'}).status_code==404
    assert c.post('/api/planner/tasks',headers={'X-Fincept-Request':'0'},json=task()).status_code==403
    c.post('/api/auth/logout');account(c)
    assert c.get(url).status_code==404 and c.get('/api/planner/plans/'+pid).status_code==404
    assert c.patch(url,json=task(version=1)).status_code==404
    assert c.post(url+'/status',json=dict(request_key=str(uuid4()),version=1,status='Completed')).status_code==404
    assert c.request('DELETE',url,json=dict(request_key=str(uuid4()),version=1)).status_code==404
    assert c.patch('/api/planner/plans/'+pid,json=plan(version=1)).status_code==404
    assert c.post('/api/planner/tasks',json=task(plan_id=pid)).status_code==404
    c.post('/api/auth/logout');assert c.get('/api/planner?month=2028-02').status_code==401
    assert c.post('/api/planner/tasks',json=task()).status_code==401

def test_restart_persistence(setup):
    c,path,_,_=setup;pid=post_plan(c);t=post_task(c,task(plan_id=pid));cookie=c.cookies.get('fincept_session')
    with TestClient(create_app(Settings(database_path=path))) as second:
        second.cookies.set('fincept_session',cookie)
        assert second.get('/api/planner/tasks/'+t['id']).json()['plan_id']==pid
        assert second.get('/api/planner/plans/'+pid).json()['id']==pid

def test_recommendations_complete_periods_rounding_and_deadline():
    base=dict(target_date='2026-12-15',start_date='2026-10-15',target_minor=1200000,saved_minor=800000,frequency='Monthly',planned_minor=220000,archived=0,state='active')
    x=estimate(base,date(2026,10,15));assert (x['days_remaining'],x['weeks'],x['months'],x['weekly_minor'],x['monthly_estimate_minor'],x['plan_status'])==(61,8,2,50000,200000,'On Track')
    x=estimate(base|dict(target_date='2027-03-20',target_minor=6000000,saved_minor=2500000,planned_minor=600000),date(2026,10,15));assert x['weekly_minor']==159100 and x['monthly_estimate_minor']==700000 and x['plan_status']=='Needs Attention'
    assert estimate(base,date(2026,12,16))['monthly_estimate_minor'] is None
    assert estimate(base|dict(saved_minor=1200000),date(2026,12,16))['monthly_estimate_minor']==0
    assert estimate(base,date(2026,12,14))['monthly_estimate_minor']==400000
    assert estimate(base|dict(start_date='2026-12-01'),date(2026,10,15))['weeks']==2

def test_canonical_goal_edit_cannot_invalidate_occasion_dates(setup):
    c,_,_,_=setup;id=post_plan(c)
    body=dict(request_key=str(uuid4()),version=1,name='Shared occasion',category='Other',target_minor=1200000,target_date=None,monthly_minor=100000)
    assert c.patch('/api/goals/'+id,json=body).status_code==422
    body|=dict(request_key=str(uuid4()),target_date='2026-01-01')
    assert c.patch('/api/goals/'+id,json=body).status_code==422
    body|=dict(request_key=str(uuid4()),target_date='2029-01-01')
    assert c.patch('/api/goals/'+id,json=body).status_code==200
    g=listing(c)['plans'][0]
    assert g['target_date']=='2029-01-01' and g['planned_minor']==100000

def test_selected_timezone_drives_today_and_civil_dates_do_not_move(setup):
    c,_,_,_=setup;post_task(c,task(timezone='Pacific/Kiritimati',due_time='00:15'))
    from datetime import datetime
    from zoneinfo import ZoneInfo
    for zone in ['Pacific/Kiritimati','Pacific/Pago_Pago','America/New_York']:
        x=c.get('/api/planner',params=dict(month='2028-02',timezone=zone)).json()
        assert x['today']==datetime.now(ZoneInfo(zone)).date().isoformat()
        assert x['items'][0]['due_date']=='2028-02-29' and x['items'][0]['due_time']=='00:15'
