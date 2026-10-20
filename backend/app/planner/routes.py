"""Owned, versioned, replay-safe Planner operations; never writes transactions."""
import calendar
from datetime import date,datetime,timedelta
from typing import Literal
from uuid import uuid4
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from fastapi import APIRouter,Depends,Query
from pydantic import Field,StrictInt,field_validator,model_validator
from ..finance.transactions import Command,Delete,MAX_MINOR,fail,now,replay,receipt,workspace
from ..finance.goal_service import goals

Category=Literal['Personal','Financial','Bill Payment','Occasion Preparation','Other']
Status=Literal['To Do','In Progress','Completed','Cancelled']

def valid_zone(v):
    try:ZoneInfo(v)
    except (ZoneInfoNotFoundError,ValueError):raise ValueError('Choose a valid IANA timezone.')
    return v

def day(v):
    if not 1901<=v.year<=2100:raise ValueError('Choose a date between 1901 and 2100.')
    return v

class TaskInput(Command):
    title:str=Field(min_length=1,max_length=120)
    description:str=Field(default='',max_length=2000)
    due_date:date
    due_time:str|None=Field(default=None,pattern=r'^([01]\d|2[0-3]):[0-5]\d$')
    timezone:str=Field(default='Asia/Dhaka',max_length=100)
    category:Category='Personal'
    priority:Literal['Low','Medium','High']='Medium'
    status:Status='To Do'
    plan_id:str|None=Field(default=None,max_length=160)
    version:StrictInt|None=Field(default=None,ge=1)
    _date=field_validator('due_date')(day)
    _zone=field_validator('timezone')(valid_zone)

class TaskState(Delete):
    status:Status

class PlanInput(Command):
    name:str=Field(min_length=1,max_length=80)
    occasion_type:Literal['Birthday','Wedding','Anniversary','Festival','Celebration','Travel','Custom']
    custom_type:str=Field(default='',max_length=80)
    occasion_date:date
    start_date:date
    target_minor:StrictInt=Field(gt=0,le=MAX_MINOR)
    frequency:Literal['Weekly','Monthly']='Monthly'
    planned_minor:StrictInt=Field(default=0,ge=0,le=MAX_MINOR)
    description:str=Field(default='',max_length=2000)
    version:StrictInt|None=Field(default=None,ge=1)
    _dates=field_validator('occasion_date','start_date')(day)
    @model_validator(mode='after')
    def ordered(self):
        if self.start_date>self.occasion_date:raise ValueError('Saving start date must be on or before the occasion date.')
        if self.occasion_type=='Custom' and not self.custom_type:raise ValueError('Enter a custom occasion type.')
        return self

def estimate(g,today):
    end=date.fromisoformat(g['target_date']);start=max(today,date.fromisoformat(g['start_date']))
    days=(end-today).days;available=max(0,(end-start).days)
    months=max(0,(end.year-start.year)*12+end.month-start.month-(end.day<start.day))
    weeks=available//7;remaining=max(0,g['target_minor']-g['saved_minor'])
    def installment(n):return ((remaining+100*max(1,n)-1)//(100*max(1,n)))*100
    weekly=0 if not remaining else None if days<0 else installment(weeks)
    monthly=0 if not remaining else None if days<0 else installment(months)
    required=weekly if g['frequency']=='Weekly' else monthly
    state='Archived' if g['archived'] else 'Paused' if g['state']=='paused' else 'Goal Reached' if not remaining else 'Past Deadline' if days<0 else 'Pace not set' if not g['planned_minor'] else 'On Track' if g['planned_minor']>=required else 'Needs Attention'
    return dict(remaining_minor=remaining,days_remaining=days,weeks=weeks,months=months,weekly_minor=weekly,monthly_estimate_minor=monthly,plan_status=state)

def planner_router(db,current_user,environment):
    r=APIRouter(prefix='/api/planner',tags=['Planner'])
    def scope(dataset:Literal['live','demo']='live'):
        if dataset=='demo' and environment=='production':fail('Sample workspaces are disabled in production.',403)
        return dataset
    def tz(timezone:str=Query('Asia/Dhaka',max_length=100)):
        try:return valid_zone(timezone)
        except ValueError:fail('Choose a valid IANA timezone.',422,'timezone')
    def plans(c,u,d,today):
        meta={x['goal_id']:dict(x) for x in c.execute('SELECT * FROM planner_occasions WHERE user_id=? AND dataset=?',(u,d))}
        items=[]
        for g in goals(c,u,d,True):
            if g['id'] not in meta:continue
            entry=g|meta[g['id']]
            if entry['frequency']=='Monthly':entry['planned_minor']=g['monthly_minor']
            items.append(entry|estimate(entry,today))
        return items
    def plan(c,u,d,id):
        g=next((g for g in plans(c,u,d,date.today()) if g['id']==id),None)
        if not g:fail('Occasion plan not found.',404)
        return g
    def owned(c,u,d,id):
        row=c.execute('SELECT * FROM planner_tasks WHERE id=? AND user_id=? AND dataset=?',(id,u,d)).fetchone()
        if not row:fail('Task not found.',404)
        return dict(row)
    def check_version(row,p):
        if p.version!=row['version']:fail('This record changed. Close and reload before retrying.',409)
    def link(c,u,d,id):
        if id and plan(c,u,d,id)['archived']:fail('Choose an active occasion plan.',422,'plan_id')
    @r.get('')
    def listing(month:str=Query(pattern=r'^\d{4}-(0[1-9]|1[0-2])$'),search:str=Query('',max_length=120),category:Category|Literal['']='',status:Literal['All','Upcoming','Overdue','Completed','Cancelled']='All',timezone=Depends(tz),dataset=Depends(scope),user=Depends(current_user)):
        y,m=map(int,month.split('-'))
        if not 1901<=y<=2100:fail('Choose a month between 1901 and 2100.',422)
        first=date(y,m,1);last=date(y,m,calendar.monthrange(y,m)[1]);start=first-timedelta(days=first.weekday());end=last+timedelta(days=6-last.weekday());today=datetime.now(ZoneInfo(timezone)).date();u=user['id']
        with db() as c:
            all_plans=plans(c,u,dataset,today);active=[g for g in all_plans if not g['archived'] and g['state']=='active']
            counts={x['bucket']:x['n'] for x in c.execute("""SELECT CASE WHEN due_date<? THEN 'overdue' ELSE 'upcoming' END bucket,count(*) n FROM planner_tasks WHERE user_id=? AND dataset=? AND status IN ('To Do','In Progress') GROUP BY bucket""",(today.isoformat(),u,dataset))}
            q=search.casefold().strip()
            candidates=[dict(x) for x in c.execute('SELECT * FROM planner_tasks WHERE user_id=? AND dataset=? AND due_date>=? AND due_date<=? ORDER BY due_date,COALESCE(due_time,\'\'),created_at,id',(u,dataset,start.isoformat(),end.isoformat()))]
            def match(t):
                return (not q or q in (t['title']+' '+t['description']).casefold()) and (not category or t['category']==category) and (status=='All' or status in ('Completed','Cancelled') and t['status']==status or status in ('Upcoming','Overdue') and t['status'] in ('To Do','In Progress') and ((t['due_date']>=today.isoformat()) if status=='Upcoming' else (t['due_date']<today.isoformat())))
            items=[t for t in candidates if match(t)]
            return dict(items=items,plans=all_plans,today=today.isoformat(),timezone=timezone,month=month,range_start=start.isoformat(),range_end=end.isoformat(),total=len(candidates),summary=dict(upcoming_tasks=counts.get('upcoming',0),overdue_tasks=counts.get('overdue',0),upcoming_occasions=sum(g['target_date']>=today.isoformat() for g in active),target_minor=sum(g['target_minor'] for g in active),saved_minor=sum(g['saved_minor'] for g in active),remaining_minor=sum(g['remaining_minor'] for g in active)))
    @r.get('/tasks/{id}')
    def detail(id:str,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:return owned(c,user['id'],dataset,id)
    @r.post('/tasks',status_code=201)
    def create(p:TaskInput,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];fp,old=replay(c,u,p.request_key,p.model_dump(mode='json'),'planner-task-create:'+dataset)
            if old:return old
            workspace(c,u,dataset);link(c,u,dataset,p.plan_id);id=str(uuid4());stamp=now()
            c.execute('INSERT INTO planner_tasks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(id,u,dataset,p.title,p.description,p.due_date.isoformat(),p.due_time,p.timezone,p.category,p.priority,p.status,p.plan_id,1,stamp,stamp))
            return receipt(c,u,p.request_key,fp,owned(c,u,dataset,id))
    @r.patch('/tasks/{id}')
    def update(id:str,p:TaskInput,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];fp,old=replay(c,u,p.request_key,p.model_dump(mode='json'),'planner-task-edit:'+dataset+id)
            if old:return old
            row=owned(c,u,dataset,id);check_version(row,p)
            if p.plan_id!=row['plan_id']:link(c,u,dataset,p.plan_id)
            c.execute('UPDATE planner_tasks SET title=?,description=?,due_date=?,due_time=?,timezone=?,category=?,priority=?,status=?,plan_id=?,version=version+1,updated_at=? WHERE id=?',(p.title,p.description,p.due_date.isoformat(),p.due_time,p.timezone,p.category,p.priority,p.status,p.plan_id,now(),id))
            return receipt(c,u,p.request_key,fp,owned(c,u,dataset,id))
    @r.post('/tasks/{id}/status')
    def state(id:str,p:TaskState,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];fp,old=replay(c,u,p.request_key,p.model_dump(),'planner-task-state:'+dataset+id)
            if old:return old
            row=owned(c,u,dataset,id);check_version(row,p)
            c.execute('UPDATE planner_tasks SET status=?,version=version+1,updated_at=? WHERE id=?',(p.status,now(),id))
            return receipt(c,u,p.request_key,fp,owned(c,u,dataset,id))
    @r.delete('/tasks/{id}')
    def delete(id:str,p:Delete,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];fp,old=replay(c,u,p.request_key,p.model_dump(),'planner-task-delete:'+dataset+id)
            if old:return old
            row=owned(c,u,dataset,id);check_version(row,p);c.execute('DELETE FROM planner_tasks WHERE id=?',(id,))
            return receipt(c,u,p.request_key,fp,dict(id=id,deleted=True))
    @r.get('/plans/{id}')
    def plan_detail(id:str,timezone=Depends(tz),dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            g=plan(c,user['id'],dataset,id);return g|estimate(g,datetime.now(ZoneInfo(timezone)).date())
    def save_plan(c,u,d,p,id=None):
        fp,old=replay(c,u,p.request_key,p.model_dump(mode='json'),('planner-plan-edit:'+d+id) if id else 'planner-plan-create:'+d)
        if old:return old
        if id:
            g=plan(c,u,d,id);check_version(g,p)
            if g['archived']:fail('Archived occasion plans cannot be edited.',409)
            c.execute('UPDATE financial_goals SET name=?,target_minor=?,target_date=? WHERE id=?',(p.name,p.target_minor,p.occasion_date.isoformat(),id))
            c.execute('UPDATE goal_metadata SET description=?,monthly_minor=?,version=version+1,updated_at=? WHERE goal_id=?',(p.description,p.planned_minor if p.frequency=='Monthly' else 0,now(),id))
            c.execute('UPDATE planner_occasions SET occasion_type=?,custom_type=?,start_date=?,frequency=?,planned_minor=? WHERE goal_id=?',(p.occasion_type,p.custom_type,p.start_date.isoformat(),p.frequency,p.planned_minor,id))
        else:
            workspace(c,u,d);id=str(uuid4());stamp=now()
            c.execute('INSERT INTO financial_goals VALUES (?,?,?,?,?,?,?)',(id,u,d,p.name,0,p.target_minor,p.occasion_date.isoformat()))
            c.execute('INSERT INTO goal_metadata(goal_id,category,description,monthly_minor,icon,created_at,updated_at) VALUES (?,?,?,?,?,?,?)',(id,'Travel' if p.occasion_type=='Travel' else 'Other',p.description,p.planned_minor if p.frequency=='Monthly' else 0,'target',stamp,stamp))
            c.execute('INSERT INTO planner_occasions VALUES (?,?,?,?,?,?,?,?)',(id,u,d,p.occasion_type,p.custom_type,p.start_date.isoformat(),p.frequency,p.planned_minor))
        return receipt(c,u,p.request_key,fp,dict(id=id))
    @r.post('/plans',status_code=201)
    def new_plan(p:PlanInput,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');return save_plan(c,user['id'],dataset,p)
    @r.patch('/plans/{id}')
    def edit_plan(id:str,p:PlanInput,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');return save_plan(c,user['id'],dataset,p,id)
    return r
