"""Native-tool TEST DOUBLE + real auth/SQLite/canonical commands. No live provider claim."""
import asyncio
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import date,timedelta
from uuid import uuid4
import httpx
import pytest
from fastapi.testclient import TestClient
from app.main import Settings,create_app
from app.assistant.provider import ProviderTurn,OpenAIProvider,ProviderConfig,ProviderError
from app.assistant.actions import monthly_savings
from app.assistant.tools import definitions
from app.finance.budget_service import month_range
from test_assistant import register,new,send
from test_transactions import wallet

class NativeDouble:
    configured=True;name='test-native-double';model='test-only'
    def __init__(self):self.steps=[];self.calls=[]
    async def generate_tools(self,messages,tools):
        self.calls.append((json.loads(json.dumps(messages)),tools))
        step=self.steps.pop(0) if self.steps else 'Please clarify missing information.'
        if isinstance(step,Exception):raise step
        if isinstance(step,str):return ProviderTurn(step,[])
        return ProviderTurn('',[dict(id='call-'+str(len(self.calls)),type='function',function=dict(name=step[0],arguments=json.dumps(step[1])))])
    def plan(self,operations,total=None):
        p=dict(operations=operations)
        if total is not None:p['expected_budget_total_minor']=total
        self.steps=[('propose_changes',p)]
@pytest.fixture
def agent(tmp_path):
    provider=NativeDouble();settings=Settings(database_path=str(tmp_path/'agent.sqlite3'))
    with TestClient(create_app(settings,assistant_provider=provider)) as c:
        c.headers.update({'X-Fincept-Request':'1','Origin':'http://localhost:5173'});user=register(c)
        yield c,provider,settings,user

def budget_op(category='Food',amount=800000):
    a,z=month_range();return dict(operation='budget.create',data=dict(name=category+' monthly',category=category,limit_minor=amount,start_date=a,end_date=z))
def goal_op(name='Laptop'):
    due=date.today().replace(year=date.today().year+1)
    return dict(operation='goal.create',data=dict(name=name,category='Electronics',target_minor=6000000,target_date=due.isoformat()))
def tx_op(w,amount=50000):return dict(operation='transaction.create',data=dict(kind='expense',amount_minor=amount,wallet_id=w,category='Food',occurred_on=date.today().isoformat(),title='Groceries'))
def proposed(agent,ops=None,total=None):
    c,p,_,_=agent;p.plan(ops or [budget_op()],total);cid=new(c);r=send(c,cid,'Prepare my financial plan')
    assert r.status_code==200,r.text;proposal=r.json()['messages'][-1]['proposal'];assert proposal and proposal['status']=='pending'
    return cid,proposal
def confirm(c,p):return c.post('/api/assistant/proposals/'+p['id']+'/confirm',json=dict(version=p['version'],confirmation='CONFIRM'))
def count(settings,table):
    with sqlite3.connect(settings.database_path) as db:return db.execute('SELECT count(*) FROM '+table).fetchone()[0]

def test_oversized_proposals_leave_room_for_versioned_review_envelope():
    from app.assistant.actions import Plan
    from pydantic import ValidationError
    plan=dict(operations=[budget_op('Food',800000)])
    Plan.model_validate(plan)
    plan['operations'][0]['data']['notes']='x'*12000
    with pytest.raises(ValidationError,match='12,000 bytes'):
        Plan.model_validate(plan)

def test_native_budget_allocations_confirm_real_dashboard_and_replay(agent):
    c,p,s,u=agent;ops=[budget_op('Food',800000),budget_op('Transport',400000),budget_op('Education',600000),budget_op('Entertainment',300000),budget_op('Other',400000)]
    cid,proposal=proposed(agent,ops,2500000)
    assert proposal['preview']['budget_total_minor']==2500000 and count(s,'budgets')==0
    r=confirm(c,proposal);assert r.status_code==200,r.text;assert r.json()['status']=='executed'
    assert r.json()['result']['budget_total_minor']==2500000
    assert confirm(c,proposal).json()==r.json();assert count(s,'budgets')==5
    assert c.get('/api/budgets').json()['summary']['limit_minor']==2500000
    assert sum(b['limit'] for b in c.get('/api/overview/summary').json()['budgets'])<=25000 # Overview intentionally shows first four.
    assert c.get('/api/assistant/conversations/'+cid).json()['messages'][-1]['proposal']['result']==r.json()['result']

def test_cancel_never_writes_and_chat_confirm_is_not_approval(agent):
    c,p,s,_=agent;cid,proposal=proposed(agent)
    p.steps=['Use the separate confirmation button.'];assert send(c,cid,'Confirm').status_code==200;assert count(s,'budgets')==0
    body=dict(version=1);r=c.post('/api/assistant/proposals/'+proposal['id']+'/cancel',json=body);assert r.status_code==200 and r.json()['status']=='cancelled'
    assert confirm(c,proposal).status_code==409 and count(s,'budgets')==0
    assert c.post('/api/assistant/proposals/'+proposal['id']+'/cancel',json=body).status_code==200

def test_edit_revision_requires_exact_new_approval(agent):
    c,p,s,_=agent;_,proposal=proposed(agent)
    plan=proposal['plan'];plan['operations'][0]['data']['limit_minor']=900000
    r=c.patch('/api/assistant/proposals/'+proposal['id'],json=dict(version=1,plan=plan));assert r.status_code==200,r.text
    revised=r.json();assert revised['version']==2 and count(s,'budgets')==0
    assert confirm(c,proposal).status_code==409
    assert confirm(c,revised).status_code==200
    assert c.get('/api/budgets').json()['items'][0]['limit_minor']==900000

def test_expired_proposal_cannot_execute(agent):
    c,_,s,_=agent;_,p=proposed(agent)
    with sqlite3.connect(s.database_path) as db:db.execute('UPDATE assistant_proposals SET expires_at=? WHERE id=?',('2000-01-01T00:00:00+00:00',p['id']))
    assert c.get('/api/assistant/proposals/'+p['id']).json()['status']=='expired'
    assert confirm(c,p).status_code==409 and count(s,'budgets')==0

def test_goals_create_update_monthly_math_and_no_deposit(agent):
    c,p,s,_=agent;_,a=proposed(agent,[goal_op()]);assert a['preview']['items'][0]['record']['required_monthly_minor']==500000
    assert confirm(c,a).status_code==200;g=c.get('/api/goals').json()['items'][0]
    assert g['target_minor']==6000000 and g['monthly_minor']==500000 and g['saved_minor']==0
    _,b=proposed(agent,[dict(operation='goal.update',record_id=g['id'],data=dict(target_minor=8000000))]);assert confirm(c,b).status_code==200
    assert c.get('/api/goals/'+g['id']).json()['goal']['target_minor']==8000000
    assert count(s,'goal_contributions')==0 and count(s,'transactions')==0

def test_transaction_create_update_correct_values_wallet_and_overview(agent):
    c,p,s,_=agent;w=wallet(c,opening=1000000);_,a=proposed(agent,[tx_op(w)]);assert count(s,'transactions')==0
    r=confirm(c,a);assert r.status_code==200,r.text;t=r.json()['result']['items'][0]['record'];assert t['amount_minor']==50000
    assert c.get('/api/transactions/options').json()['wallets'][0]['balance_minor']==950000
    _,b=proposed(agent,[dict(operation='transaction.update',record_id=t['id'],data=dict(amount_minor=45000))]);assert confirm(c,b).status_code==200
    assert c.get('/api/transactions/'+t['id']).json()['amount_minor']==45000
    assert c.get('/api/overview/summary').json()['summary']['expenses']==450

def test_combined_failure_rolls_back_every_operation_and_retry(agent):
    c,p,s,_=agent;w=wallet(c,opening=100000);_,a=proposed(agent,[budget_op(),goal_op(),tx_op(w,50000)])
    # An unrelated manual expense changes actual funds AFTER review.
    r=c.post('/api/transactions',json=dict(request_key=str(uuid4()),kind='expense',amount_minor=90000,wallet_id=w,category='Shopping',occurred_at=date.today().isoformat()+'T00:00:00',title='Manual purchase'));assert r.status_code==201
    assert confirm(c,a).status_code==409 and count(s,'budgets')==0 and count(s,'financial_goals')==0 and count(s,'transactions')==1
    assert c.get('/api/assistant/proposals/'+a['id']).json()['status']=='pending'

def test_budget_update_stale_version_rejected_including_edit(agent):
    c,p,s,_=agent;_,a=proposed(agent);saved=confirm(c,a).json()['result']['items'][0]['record'];id=saved['id']
    _,b=proposed(agent,[dict(operation='budget.update',record_id=id,data=dict(limit_minor=900000))])
    # A manual canonical write increments the same version.
    data=b['plan']['operations'][0]['data']|dict(request_key=str(uuid4()),version=1,limit_minor=1000000)
    assert c.patch('/api/budgets/'+id,json=data).status_code==200
    assert confirm(c,b).status_code==409
    assert c.patch('/api/assistant/proposals/'+b['id'],json=dict(version=1,plan=b['plan'])).status_code==409
    assert count(s,'budgets')==1 and c.get('/api/budgets/'+id).json()['budget']['limit_minor']==1000000

@pytest.mark.parametrize('bad',[
 dict(operations=[budget_op()],expected_budget_total_minor=1),
 dict(operations=[budget_op(),budget_op()]),
 dict(operations=[budget_op()|{'data':budget_op()['data']|{'limit_minor':-1}}]),
 dict(operations=[budget_op()|{'data':budget_op()['data']|{'user_id':'attacker'}}]),
 dict(operations=[budget_op()|{'data':budget_op()['data']|{'category':'Unconfigured category'}}]),
 dict(operations=[goal_op()|{'data':goal_op()['data']|{'target_date':'2000-01-01'}}]),
 dict(operations=[dict(operation='transaction.create',data=dict(amount_minor=50000,kind='expense'))]),
 dict(operations=[dict(operation='budget.delete',record_id='anything',data={})]),
])
def test_invalid_plan_returns_tool_error_and_no_proposal_or_financial_write(agent,bad):
    c,p,s,_=agent;p.steps=[('propose_changes',bad),'Please clarify the invalid or missing details.'];r=send(c,new(c),'Prepare a plan')
    assert r.status_code==200,r.text;assert r.json()['messages'][-1]['proposal'] is None
    assert count(s,'budgets')==count(s,'financial_goals')==count(s,'transactions')==count(s,'assistant_proposals')==0
    result=json.loads(p.calls[-1][0][-1]['content']);assert result['financial_changes_saved'] is False and 'error' in result

def test_duplicate_goal_budget_and_transaction_blocked(agent):
    c,p,s,_=agent;w=wallet(c,opening=1000000)
    for op,table in [(budget_op(),'budgets'),(goal_op(),'financial_goals'),(tx_op(w),'transactions')]:
        _,a=proposed(agent,[op]);assert confirm(c,a).status_code==200
        p.plan([op]);r=send(c,new(c),'Create again');assert r.status_code==200 and r.json()['messages'][-1]['proposal'] is None
        assert count(s,table)==1

def test_auth_csrf_ownership_dataset_and_payload_tampering(agent):
    c,p,s,u=agent;cid,a=proposed(agent)
    assert c.post('/api/assistant/proposals/'+a['id']+'/confirm',json=dict(version=1,confirmation='CONFIRM',user_id=u['id'])).status_code==422
    assert c.post('/api/assistant/proposals/'+a['id']+'/confirm',headers={'X-Fincept-Request':''},json=dict(version=1,confirmation='CONFIRM')).status_code==403
    assert c.post('/api/assistant/proposals/'+a['id']+'/confirm',json=dict(version=1)).status_code==422
    assert c.get('/api/assistant/proposals/'+a['id']+'?dataset=demo').status_code==404
    register(c,'other-agent@example.com')
    assert c.get('/api/assistant/proposals/'+a['id']).status_code==404
    assert confirm(c,a).status_code==404
    assert c.post('/api/assistant/proposals/'+a['id']+'/cancel',json=dict(version=1)).status_code==404
    p.plan([dict(operation='budget.update',record_id='not-owned',data=dict(limit_minor=1))]);r=send(c,new(c),'Edit another user');assert r.status_code==200 and r.json()['messages'][-1]['proposal'] is None
    c.post('/api/auth/logout');assert confirm(c,a).status_code==401
    assert count(s,'budgets')==0

def test_concurrent_confirmation_returns_one_receipt(agent):
    c,_,s,_=agent;_,a=proposed(agent)
    with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(lambda _:confirm(c,a),range(2)))
    assert [r.status_code for r in responses]==[200,200]
    assert responses[0].json()==responses[1].json() and count(s,'budgets')==1

def test_sqlite_failure_rolls_back_and_safe_retry(agent):
    c,_,s,_=agent;_,a=proposed(agent,[budget_op(),goal_op()])
    with sqlite3.connect(s.database_path) as db:db.execute("CREATE TRIGGER fail_agent_goal BEFORE INSERT ON financial_goals BEGIN SELECT RAISE(ABORT,'PRIVATE DB ERROR'); END")
    r=confirm(c,a);assert r.status_code==503 and 'PRIVATE' not in r.text
    assert count(s,'budgets')==count(s,'financial_goals')==0
    with sqlite3.connect(s.database_path) as db:db.execute('DROP TRIGGER fail_agent_goal')
    assert confirm(c,a).status_code==200 and count(s,'budgets')==1 and count(s,'financial_goals')==1

def test_read_tools_use_real_owned_data_and_calculations(agent):
    c,p,s,u=agent;wallet(c,opening=1000000)
    p.steps=[('get_financial_options',{}),('analyze_spending',dict(start_date=date.today().isoformat(),end_date=date.today().isoformat())),('calculate_savings_target',dict(target_minor=6000000,months=12)),'No changes were requested.']
    r=send(c,new(c),'Analyze and calculate');assert r.status_code==200,r.text
    assert len(p.calls)==4 and count(s,'assistant_proposals')==0
    results=[json.loads(x['content']) for x in p.calls[-1][0] if x['role']=='tool']
    assert results[0]['wallets'][0]['name']=='Cash' and results[1]['record_count']==0 and results[2]['required_monthly_minor']==500000
    assert not any(secret in json.dumps(results) for secret in ['password_hash','token_hash',u['email'],u['id']])

def test_native_provider_transport_contract_and_malformed_calls():
    config=ProviderConfig(provider='openai',api_key='test-secret',model='test-tool-model')
    def response(request):
        body=json.loads(request.content);assert body['tools']==definitions() and body['tool_choice']=='auto' and body['parallel_tool_calls'] is False and body['store'] is False
        return httpx.Response(200,json={'choices':[{'message':{'content':None,'tool_calls':[{'id':'c1','type':'function','function':{'name':'get_budgets','arguments':'{}'}}]}}]})
    turn=asyncio.run(OpenAIProvider(config,httpx.MockTransport(response)).generate_tools([],definitions()));assert turn.tool_calls[0]['function']['name']=='get_budgets'
    def invalid(_):return httpx.Response(200,json={'choices':[{'message':{'tool_calls':[{'id':'x','type':'function','function':{'name':'sql','arguments':{}}}]}}]})
    with pytest.raises(ProviderError,match='invalid_tool'):asyncio.run(OpenAIProvider(config,httpx.MockTransport(invalid)).generate_tools([],definitions()))

def test_unknown_tool_and_tool_loop_limits_never_execute(agent):
    c,p,s,_=agent;p.steps=[('execute_sql',dict(sql='DELETE FROM budgets'))];r=send(c,new(c),'malicious');assert r.status_code==502 and r.json()['code']=='invalid_tool'
    p.steps=[('get_budgets',{})]*5;r=send(c,new(c),'loop');assert r.status_code==502 and r.json()['code']=='tool_limit'
    assert count(s,'budgets')==count(s,'assistant_proposals')==0

def test_restart_persists_approval_and_receipt(agent):
    c,p,s,_=agent;_,a=proposed(agent);cookies=c.cookies
    with TestClient(create_app(s)) as other:
        other.cookies.update(cookies);other.headers.update({'X-Fincept-Request':'1'})
        assert other.get('/api/assistant/proposals/'+a['id']).json()['status']=='pending'
        first=confirm(other,a);assert first.status_code==200
    assert confirm(c,a).json()==first.json() and count(s,'budgets')==1
