"""Allowlisted financial proposals. Model output never grants execution authority."""
import json
import sqlite3
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Literal
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictInt, ValidationError, model_validator
from ..finance import budgets, goals, transactions as tx
from ..finance.goal_service import goals as goal_rows, CATEGORIES
from ..finance.ledger import wallets

KINDS=Literal['budget.create','budget.update','goal.create','goal.update','transaction.create','transaction.update']
class Model(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
class Operation(Model):
    operation: KINDS
    record_id: str|None=Field(default=None,min_length=1,max_length=160)
    data: dict
class Plan(Model):
    operations: list[Operation]=Field(min_length=1,max_length=12)
    expected_budget_total_minor: StrictInt|None=Field(default=None,gt=0,le=tx.MAX_MINOR)
    @model_validator(mode='after')
    def bounded_review(self):
        # Leave space for the version/envelope beneath the existing 16 KiB body cap.
        if len(self.model_dump_json().encode('utf-8'))>12000:
            raise ValueError('Keep the proposed plan below 12,000 bytes; shorten notes or split the plan.')
        return self
class Version(Model):
    version: StrictInt=Field(ge=1)
class Confirm(Version):
    confirmation: Literal['CONFIRM']
class Edit(Version):
    plan: Plan

def stamp():return datetime.now(timezone.utc).isoformat(timespec='microseconds')
def expiry():return (datetime.now(timezone.utc)+timedelta(minutes=30)).isoformat(timespec='microseconds')
def problem(message,status=422):raise HTTPException(status,{'message':message})
def safe_error(exc):
    if isinstance(exc,ValidationError):return 'Invalid tool arguments. Check required fields, types, amounts and dates; ask the user for missing information.'
    if isinstance(exc,HTTPException):return exc.detail.get('message','Invalid operation.') if isinstance(exc.detail,dict) else str(exc.detail)
    return 'The financial operation could not be validated. No financial records were saved.'

def current(c,u,d,kind,id):
    if kind=='budget':return budgets.get(c,u,d,id)
    if kind=='goal':return goals.get(c,u,d,id)
    return tx.detail(c,u,d,id)

def monthly_savings(target,saved,deadline):
    remaining=max(0,target-saved)
    if not deadline:return {'remaining_minor':remaining,'required_monthly_minor':None,'months':None}
    due=date.fromisoformat(deadline);today=date.today()
    months=max(1,(due.year-today.year)*12+due.month-today.month+(due.day>today.day))
    return dict(remaining_minor=remaining,required_monthly_minor=(remaining+months-1)//months,months=months)

FIELDS={
 'budget':['name','category','limit_minor','start_date','end_date','reset_period','alert_threshold','notes'],
 'goal':['name','category','target_minor','target_date','monthly_minor','description','icon'],
 'transaction':['kind','amount_minor','wallet_id','title','description','notes','category','occurred_on'],
}
MODELS={'budget':budgets.BudgetInput,'goal':goals.GoalInput,'transaction':tx.Entry}
def normalize(c,u,d,plan,previous=None):
    """Bind update versions on the server; never accept owner, request or version IDs from the model."""
    out=[];seen=set()
    for op in plan.operations:
        kind,action=op.operation.split('.');id=op.record_id
        if (action=='update')!=bool(id):problem('Updates require a record ID; new records must not specify one.')
        if not op.data or set(op.data)-set(FIELDS[kind]):problem('Unsupported or empty financial fields. Ownership and versions are managed by the server.')
        old=current(c,u,d,kind,id) if id else None
        if kind=='goal' and id and c.execute('SELECT 1 FROM planner_occasions WHERE goal_id=?',(id,)).fetchone():problem('Edit occasion-linked savings plans in Planner so their schedules remain consistent.',409)
        if old and kind=='transaction' and (old['kind']=='transfer' or old['linked_transfer_id']):problem('Use Transactions for transfers and linked fees. The agent supports income and expenses only.')
        data={k:old[k] for k in FIELDS[kind] if old and k in old}
        if old and kind=='transaction':data['occurred_on']=old['occurred_at'][:10]
        data.update(op.data)
        version=old['version'] if old else None
        if previous and id:
            prior=next((x for x in previous['operations'] if x['operation']==op.operation and x['record_id']==id),None)
            if prior and prior['record_version']!=version:problem('This record changed after review. Cancel this proposal and request a fresh plan.',409)
        if kind=='transaction':
            if data.get('kind') not in ('income','expense'):problem('Only income and expense records are available to the agent.')
            if not data.get('category') or not data.get('wallet_id') or not data.get('occurred_on'):problem('A transaction needs an explicit date, wallet, category, type and positive amount. Ask the user for missing details.')
            try:day=date.fromisoformat(data.pop('occurred_on'))
            except (ValueError,TypeError):problem('Use an explicit ISO transaction date.')
            if day>date.today():problem('Future transactions must be scheduled in Planner, not recorded as completed activity.')
            data['occurred_at']=old['occurred_at'] if old and day.isoformat()==old['occurred_at'][:10] else day.isoformat()+'T00:00:00'
        p=MODELS[kind].model_validate(data|{'request_key':'agent-validation-only','version':version})
        if kind=='goal' and p.target_date and p.target_date<date.today():problem('Use a goal deadline today or later, or omit the deadline.')
        if kind=='goal' and not old and p.target_date and 'monthly_minor' not in op.data:
            p=p.model_copy(update={'monthly_minor':monthly_savings(p.target_minor,0,p.target_date.isoformat())['required_monthly_minor']})
        clean=p.model_dump(mode='json',exclude={'request_key','version'})
        # Agent transactions record an explicit calendar date, not a fabricated exact time.
        if kind=='transaction':
            clean={k:v for k,v in clean.items() if k in FIELDS[kind] or k=='occurred_at'}
        signature=(op.operation,id) if id else (op.operation,json.dumps(clean,sort_keys=True))
        if signature in seen:problem('The plan contains duplicate operations.')
        seen.add(signature)
        out.append(dict(operation=op.operation,record_id=id,record_version=version,data=clean))
    budget_total=sum(x['data']['limit_minor'] for x in out if x['operation'].startswith('budget.'))
    if budget_total>tx.MAX_MINOR:problem('The total budget exceeds the supported amount.')
    if plan.expected_budget_total_minor is not None and plan.expected_budget_total_minor!=budget_total:problem('Budget allocations do not equal the stated total. Correct the allocations or ask for clarification.')
    payload=dict(operations=out,budget_total_minor=budget_total,expected_budget_total_minor=plan.expected_budget_total_minor)
    Plan.model_validate(client_plan(payload))  # Expanded update defaults must remain editable too.
    return payload

def client_plan(payload):
    operations=[]
    for x in payload['operations']:
        data={k:v for k,v in x['data'].items() if k in FIELDS[x['operation'].split('.')[0]]}
        if x['operation'].startswith('transaction.'):data['occurred_on']=x['data']['occurred_at'][:10]
        operations.append(dict(operation=x['operation'],record_id=x['record_id'],data=data))
    return dict(operations=operations,expected_budget_total_minor=payload.get('expected_budget_total_minor'))

def project(kind,row):
    extra={'budget':['id','version','spent_minor','remaining_minor'],
           'goal':['id','version','saved_minor','status'],
           'transaction':['id','version','wallet_name','occurred_at']}[kind]
    result={k:row[k] for k in set(FIELDS[kind]+extra) if k in row}
    if kind=='goal':result.update(monthly_savings(row['target_minor'],row['saved_minor'],row['target_date']))
    return result

def apply(c,u,d,payload):
    """Caller holds BEGIN IMMEDIATE. Also used under an always-rolled-back validation savepoint."""
    items=[]
    for op in payload['operations']:
        kind,action=op['operation'].split('.');id=op['record_id'];data=op['data']
        old=current(c,u,d,kind,id) if id else None
        if old and old['version']!=op['record_version']:problem('A reviewed record changed. Cancel and request a fresh proposal.',409)
        p=MODELS[kind].model_validate(data|dict(version=op['record_version'],request_key='agent-approved-command'))
        if kind=='goal':
            if p.target_date and p.target_date<date.today():problem('The goal deadline is no longer valid.')
            if id and c.execute('SELECT 1 FROM planner_occasions WHERE goal_id=?',(id,)).fetchone():problem('Edit occasion-linked plans in Planner.',409)
            if not id and c.execute('SELECT 1 FROM financial_goals WHERE user_id=? AND dataset=? AND lower(trim(name))=lower(trim(?))',(u,d,p.name)).fetchone():problem('A goal with this name already exists. Retrieve and update that goal instead.',409)
            result=goals.save_goal(c,u,d,p,id);saved=current(c,u,d,kind,result['id'])
        elif kind=='budget':
            result=budgets.save(c,u,d,p,id);saved=current(c,u,d,kind,result['id'])
        else:
            if p.kind not in ('income','expense') or p.destination_wallet_id or p.fee_minor:problem('Agent transfers are unavailable.')
            if date.fromisoformat(p.occurred_at[:10])>date.today():problem('A transaction cannot be recorded in the future.')
            if not id and c.execute('''SELECT 1 FROM transactions WHERE user_id=? AND dataset=? AND wallet_id=? AND kind=? AND amount_minor=? AND category=? AND substr(occurred_at,1,10)=? AND title=?''',(u,d,p.wallet_id,p.kind,p.amount_minor,p.category,p.occurred_at[:10],p.title or p.category)).fetchone():problem('An identical transaction already exists on this date. Review it in Transactions before adding another.',409)
            saved=tx.save_entry(c,u,d,p,id)
        items.append(dict(operation=op['operation'],before=project(kind,old) if old else None,record=project(kind,saved)))
    return dict(items=items,budget_total_minor=payload['budget_total_minor'],atomic=True)

def validate_preview(c,u,d,payload):
    c.execute('SAVEPOINT agent_validation')
    try:return apply(c,u,d,payload)
    finally:
        c.execute('ROLLBACK TO agent_validation');c.execute('RELEASE agent_validation')

def proposal(c,u,d,cid,request_id,raw):
    payload=normalize(c,u,d,Plan.model_validate(raw));preview=validate_preview(c,u,d,payload)
    id=str(uuid4());now=stamp()
    c.execute('''INSERT INTO assistant_proposals(id,conversation_id,request_id,user_id,dataset,status,payload_json,preview_json,created_at,updated_at,expires_at)
      VALUES (?,?,?,?,?,'pending',?,?,?,?,?)''',(id,cid,request_id,u,d,json.dumps(payload),json.dumps(preview),now,now,expiry()))
    return id

def get_owned(c,u,d,id):
    r=c.execute('SELECT * FROM assistant_proposals WHERE id=? AND user_id=? AND dataset=?',(id,u,d)).fetchone()
    if not r:problem('Proposal not found.',404)
    return dict(r)
def public(r):
    status='expired' if r['status']=='pending' and r['expires_at']<=stamp() else r['status']
    return {k:r[k] for k in ['id','conversation_id','request_id','version','created_at','updated_at','expires_at']}|dict(status=status,plan=client_plan(json.loads(r['payload_json'])),preview=json.loads(r['preview_json']),result=json.loads(r['result_json']) if r['result_json'] else None)
def for_request(c,request_id):
    r=c.execute('SELECT * FROM assistant_proposals WHERE request_id=?',(request_id,)).fetchone()
    return public(dict(r)) if r else None

def action_router(db,current_user,environment):
    router=APIRouter(prefix='/api/assistant/proposals',tags=['AI approvals'])
    def guard(dataset):
        if dataset=='demo' and environment=='production':problem('Sample workspaces are disabled in production.',403)
    def check(r,p):
        if r['version']!=p.version:problem('This proposal has been revised. Reload and review the current version before confirming.',409)
    def pending(r):
        if r['status']!='pending':problem('This proposal is no longer pending.',409)
        if r['expires_at']<=stamp():problem('This proposal expired. Request a new plan; no financial changes were saved.',409)
    @router.get('/options')
    def options(dataset:Literal['live','demo']='live',user=Depends(current_user)):
        guard(dataset)
        from .tools import read
        with db() as c:
            result=read(c,user['id'],dataset,'get_financial_options',{})
            result['budget_categories']=budgets.options(c,user['id'],dataset)
            return result
    @router.get('/{id}')
    def detail(id:UUID,dataset:Literal['live','demo']='live',user=Depends(current_user)):
        guard(dataset)
        with db() as c:return public(get_owned(c,user['id'],dataset,str(id)))
    @router.patch('/{id}')
    def edit(id:UUID,p:Edit,dataset:Literal['live','demo']='live',user=Depends(current_user)):
        guard(dataset)
        try:
            with db() as c:
                c.execute('BEGIN IMMEDIATE');r=get_owned(c,user['id'],dataset,str(id));check(r,p);pending(r)
                payload=normalize(c,user['id'],dataset,p.plan,json.loads(r['payload_json']));preview=validate_preview(c,user['id'],dataset,payload)
                c.execute('UPDATE assistant_proposals SET payload_json=?,preview_json=?,version=version+1,updated_at=?,expires_at=? WHERE id=?',(json.dumps(payload),json.dumps(preview),stamp(),expiry(),str(id)))
                return public(get_owned(c,user['id'],dataset,str(id)))
        except ValidationError:problem('Invalid plan fields. Review amounts, dates and required values.')
        except sqlite3.Error as exc:
            logging.getLogger('fincept.assistant').error('Proposal validation failed (%s)',type(exc).__name__)
            problem('Unable to validate the revised plan. No financial changes were saved; retry safely.',503)
    @router.post('/{id}/cancel')
    def cancel(id:UUID,p:Version,dataset:Literal['live','demo']='live',user=Depends(current_user)):
        guard(dataset)
        with db() as c:
            c.execute('BEGIN IMMEDIATE');r=get_owned(c,user['id'],dataset,str(id));check(r,p)
            if r['status']=='executed':problem('This plan was already saved and cannot be cancelled here.',409)
            c.execute("UPDATE assistant_proposals SET status='cancelled',updated_at=? WHERE id=?",(stamp(),str(id)))
            return public(get_owned(c,user['id'],dataset,str(id)))
    @router.post('/{id}/confirm')
    def confirm(id:UUID,p:Confirm,dataset:Literal['live','demo']='live',user=Depends(current_user)):
        guard(dataset)
        try:
            with db() as c:
                c.execute('BEGIN IMMEDIATE');r=get_owned(c,user['id'],dataset,str(id));check(r,p)
                if r['status']=='executed':return public(r) # Durable receipt; never execute a second time.
                pending(r);result=apply(c,user['id'],dataset,json.loads(r['payload_json']))
                result['saved_at']=stamp()
                c.execute("UPDATE assistant_proposals SET status='executed',result_json=?,updated_at=? WHERE id=?",(json.dumps(result),stamp(),str(id)))
                return public(get_owned(c,user['id'],dataset,str(id)))
        except ValidationError:problem('The saved proposal is invalid. Request a fresh plan; nothing was saved.')
        except sqlite3.Error as exc:
            logging.getLogger('fincept.assistant').error('Approved plan failed (%s)',type(exc).__name__)
            problem('Unable to save this plan. All changes were rolled back; retry safely.',503)
    return router
