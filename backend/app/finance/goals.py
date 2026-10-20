"""Versioned, owner-scoped goal plans and atomic earmark/deposit contribution commands."""
import uuid
from datetime import date,datetime
from typing import Literal
from fastapi import APIRouter,Depends,Query
from pydantic import Field,StrictInt,StrictBool,field_validator
from .transactions import Command,Delete,MAX_MINOR,fail,now,replay,receipt,workspace
from .goal_service import goals,summary,funding_wallets,CATEGORIES,ICONS
from .ledger import ledger,balance_at

class GoalInput(Command):
    name:str=Field(min_length=1,max_length=80)
    category:Literal['Emergency Fund','Education','Travel','Electronics','Home','Vehicle','Other']
    target_minor:StrictInt=Field(gt=0,le=MAX_MINOR)
    target_date:date|None=None
    monthly_minor:StrictInt=Field(default=0,ge=0,le=MAX_MINOR)
    description:str=Field(default='',max_length=2000)
    icon:Literal['category','shield','laptop','travel','phone','target']='category'
    version:StrictInt|None=Field(default=None,ge=1)
    @field_validator('target_date')
    @classmethod
    def valid_date(cls,v):
        if v and not 1901<=v.year<=2100:raise ValueError('Use a target date between 1901 and 2100.')
        return v
class State(Delete):
    state:Literal['active','paused']
class Contribution(Command):
    version:StrictInt=Field(ge=1)
    method:Literal['allocation','external']='allocation'
    wallet_id:str=Field(min_length=1,max_length=160)
    amount_minor:StrictInt=Field(gt=0,le=MAX_MINOR)
    date:date
    note:str=Field(default='',max_length=2000)
    limit_to_target:StrictBool=True
    expected_balance_minor:StrictInt|None=None
    expected_allocated_minor:StrictInt|None=None
    @field_validator('date')
    @classmethod
    def recorded_date(cls,v):
        if not 1901<=v.year<=2100 or v>date.today():raise ValueError('Use a recorded date between 1901 and today; future contributions are not saved funds.')
        return v

def get(c,u,d,id,archived=False):
    g=next((x for x in goals(c,u,d,include_archived=archived) if x['id']==id),None)
    if not g:fail('Goal not found.',404)
    return g
def version(g,p):
    if g['version']!=p.version:fail('This goal changed. Close and reload it before retrying.',409)
def materialize(c,g):
    if c.execute('SELECT 1 FROM goal_metadata WHERE goal_id=?',(g['id'],)).fetchone():return
    c.execute('INSERT INTO goal_metadata(goal_id,created_at,updated_at) VALUES (?,?,?)',(g['id'],now(),now()))
    if g['saved_minor']:
        c.execute('INSERT INTO goal_contributions VALUES (?,?,?,?,?,?,?,?,?,?,?)',(str(uuid.uuid4()),g['id'],g['user_id'],g['dataset'],None,g['saved_minor'],'legacy',None,now()[:10]+'T00:00:00','Imported saved balance; original funding unavailable',now()))
def bump(c,id):c.execute('UPDATE goal_metadata SET version=version+1,updated_at=? WHERE goal_id=?',(now(),id))

def save_goal(c,u,d,p,id=None):
    """Shared plan command, not a contribution or movement of money."""
    if id:
        g=get(c,u,d,id)
        occasion=c.execute('SELECT start_date FROM planner_occasions WHERE goal_id=?',(id,)).fetchone()
        if occasion and (p.target_date is None or p.target_date.isoformat()<occasion['start_date']):fail('Occasion plans need a target date on or after their saving start date. Edit the occasion dates in Planner.',422,'target_date')
        version(g,p);materialize(c,g)
        c.execute('UPDATE financial_goals SET name=?,target_minor=?,target_date=? WHERE id=?',(p.name,p.target_minor,p.target_date.isoformat() if p.target_date else None,id))
        c.execute('UPDATE goal_metadata SET category=?,description=?,monthly_minor=?,icon=? WHERE goal_id=?',(p.category,p.description,p.monthly_minor,p.icon,id));bump(c,id)
        return dict(id=id,version=g['version']+1)
    workspace(c,u,d);id=str(uuid.uuid4())
    c.execute('INSERT INTO financial_goals VALUES (?,?,?,?,?,?,?)',(id,u,d,p.name,0,p.target_minor,p.target_date.isoformat() if p.target_date else None))
    c.execute('INSERT INTO goal_metadata(goal_id,category,description,monthly_minor,icon,created_at,updated_at) VALUES (?,?,?,?,?,?,?)',(id,p.category,p.description,p.monthly_minor,p.icon,now(),now()))
    return dict(id=id,version=1)

def goal_router(db,current_user,environment):
    r=APIRouter(prefix='/api/goals',tags=['Financial Goals'])
    def scope(dataset:Literal['live','demo']='live'):
        if dataset=='demo' and environment=='production':fail('Sample workspaces are disabled in production.',403)
        return dataset
    @r.get('/options')
    def options(dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:return dict(categories=CATEGORIES,icons=ICONS,wallets=funding_wallets(c,user['id'],dataset))
    @r.get('')
    def listing(search:str=Query('',max_length=200),status:Literal['','In Progress','Paused','Completed']='',category:str='',sort:Literal['recent','date','target','progress']='recent',scope:Literal['all','active','completed','paused','archived']='all',dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            items=goals(c,user['id'],dataset,scope=='archived');all_items=items
            if scope=='archived':items=[g for g in items if g['archived']]
            elif scope!='all':items=[g for g in items if g['status']=={'active':'In Progress','completed':'Completed','paused':'Paused'}[scope]]
            q=search.strip().casefold();filtered=[g for g in items if (not status or g['status']==status) and (not category or g['category']==category) and (not q or q in (g['name']+' '+g['category']+' '+g['description']).casefold())]
            filtered.sort(key={'recent':lambda g:-g['position'],'date':lambda g:(g['target_date'] or '9999',-g['position']),'target':lambda g:(-g['target_minor'],-g['position']),'progress':lambda g:(g['percentage'] if g['percentage'] is not None else -1,-g['position'])}[sort])
            return dict(items=filtered,total=len(items),filtered_count=len(filtered),summary=summary(all_items),categories=CATEGORIES,today=date.today().isoformat(),scope=scope)
    @r.get('/{id}')
    def details(id:str,page:int=Query(1,ge=1),limit:int=Query(10,ge=1,le=50),dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            g=get(c,user['id'],dataset,id,True)
            rows=[dict(x) for x in c.execute('''SELECT a.*,w.name wallet_name FROM goal_contributions a LEFT JOIN wallets w ON w.id=a.wallet_id
            WHERE a.goal_id=? AND a.user_id=? AND a.dataset=? ORDER BY a.occurred_at DESC,a.created_at DESC,a.id''',(id,user['id'],dataset))]
            if not rows and g['saved_minor'] and g['legacy_unlinked_minor']:
                rows=[dict(id='legacy:'+id,amount_minor=g['saved_minor'],method='legacy',wallet_name=None,occurred_at='',note='Imported saved balance; original funding unavailable')]
            page=min(page,max(1,(len(rows)+limit-1)//limit));return dict(goal=g,items=rows[(page-1)*limit:page*limit],total=len(rows),page=page,limit=limit)
    @r.post('',status_code=201)
    def create(p:GoalInput,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];fp,old=replay(c,u,p.request_key,p.model_dump(mode='json'),'goal-create:'+dataset)
            if old:return old
            return receipt(c,u,p.request_key,fp,save_goal(c,u,dataset,p))
    @r.patch('/{id}')
    def update(id:str,p:GoalInput,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];g=get(c,u,dataset,id);fp,old=replay(c,u,p.request_key,p.model_dump(mode='json'),'goal-edit:'+dataset+id)
            if old:return old
            return receipt(c,u,p.request_key,fp,save_goal(c,u,dataset,p,id))
    @r.post('/{id}/state')
    def state(id:str,p:State,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];g=get(c,u,dataset,id);fp,old=replay(c,u,p.request_key,p.model_dump(),'goal-state:'+dataset+id)
            if old:return old
            version(g,p)
            if g['status']=='Completed':fail('Completed goals cannot be paused. Edit the target to reopen the plan if needed.',409)
            materialize(c,g);c.execute('UPDATE goal_metadata SET state=? WHERE goal_id=?',(p.state,id));bump(c,id)
            return receipt(c,u,p.request_key,fp,dict(id=id,version=g['version']+1))
    @r.delete('/{id}')
    def delete(id:str,p:Delete,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];fp,old=replay(c,u,p.request_key,p.model_dump(),'goal-archive:'+dataset+id)
            if old:return old
            g=get(c,u,dataset,id);version(g,p);materialize(c,g);c.execute('UPDATE goal_metadata SET archived=1 WHERE goal_id=?',(id,));bump(c,id)
            return receipt(c,u,p.request_key,fp,dict(id=id,released_minor=g['saved_minor']))
    def prepare(c,u,d,id,p):
        g=get(c,u,d,id);version(g,p)
        if g['status']!='In Progress':fail('Only in-progress goals accept savings. Resume a paused goal or edit a completed target first.',409)
        if p.limit_to_target and p.amount_minor>g['remaining_minor']:fail('Contribution exceeds the remaining target. Reduce it or turn off the target limit.',422,'amount_minor')
        point=p.date.isoformat()+'T'+(datetime.now().strftime('%H:%M:%S') if p.date==date.today() else '23:59:59')
        w=next((x for x in funding_wallets(c,u,d) if x['id']==p.wallet_id),None)
        if not w:fail('Wallet not found.',404)
        if w['archived'] or w['status']!='active' or w['currency']!='BDT':fail('Choose an active BDT wallet.',422,'wallet_id')
        if p.date.isoformat()<w['opening_date']:fail('Contribution cannot precede the wallet opening date.',422,'date')
        if p.expected_balance_minor is not None and (p.expected_balance_minor!=w['balance_minor'] or p.expected_allocated_minor!=w['allocated_minor']):fail('Wallet funds changed since review. Go back and refresh the funding source.',409)
        if g['saved_minor']+p.amount_minor>MAX_MINOR:fail('Saved total exceeds the supported monetary range.',422,'amount_minor')
        if p.method=='allocation':
            # Do not over-allocate at any recorded ledger/allocation point from the chosen date onward.
            rows=ledger(c,u,d);points={point,datetime.now().isoformat(timespec='seconds')}
            points.update(x['occurred_at'] for x in rows if x['occurred_at']>=point)
            points.update(x[0] for x in c.execute('SELECT occurred_at FROM goal_contributions WHERE user_id=? AND dataset=? AND wallet_id=? AND occurred_at>=?',(u,d,w['id'],point)))
            for t in points:
                at=next(x for x in funding_wallets(c,u,d,t) if x['id']==w['id'])
                if at['available_minor']<p.amount_minor:fail('Insufficient unallocated funds, including later recorded movements. Choose another wallet or a smaller amount.',409,'amount_minor')
        return g,w,point
    @r.post('/{id}/contributions/preview')
    def preview(id:str,p:Contribution,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            g,w,point=prepare(c,user['id'],dataset,id,p)
            return dict(goal=g,wallet=w,projected_minor=g['saved_minor']+p.amount_minor,remaining_minor=g['remaining_minor']-p.amount_minor,occurred_at=point)
    @r.post('/{id}/contributions',status_code=201)
    def contribute(id:str,p:Contribution,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];fp,old=replay(c,u,p.request_key,p.model_dump(mode='json'),'goal-contribution:'+dataset+id)
            if old:return old
            if p.expected_balance_minor is None or p.expected_allocated_minor is None:fail('Review this contribution before recording it.',422)
            g,w,point=prepare(c,u,dataset,id,p);materialize(c,g);event=None
            if p.method=='external':
                event=str(uuid.uuid4());c.execute('INSERT INTO wallet_events VALUES (?,?,?,?,?,?,?,?,?,?)',(event,u,dataset,w['id'],p.amount_minor,'external',p.note or 'External savings deposit','Financial goal',point,now()))
                c.execute('INSERT OR IGNORE INTO wallet_profiles(wallet_id,created_at,updated_at) VALUES (?,?,?)',(w['id'],now(),now()));c.execute('UPDATE wallet_profiles SET version=version+1,updated_at=? WHERE wallet_id=?',(now(),w['id']))
            contribution=str(uuid.uuid4());c.execute('INSERT INTO goal_contributions VALUES (?,?,?,?,?,?,?,?,?,?,?)',(contribution,id,u,dataset,w['id'],p.amount_minor,p.method,event,point,p.note,now()))
            c.execute('UPDATE financial_goals SET saved_minor=? WHERE id=?',(g['saved_minor']+p.amount_minor,id));bump(c,id)
            return receipt(c,u,p.request_key,fp,dict(id=contribution,goal_id=id,wallet_event_id=event,version=g['version']+1))
    return r
