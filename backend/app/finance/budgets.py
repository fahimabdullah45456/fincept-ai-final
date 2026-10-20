"""Authenticated, versioned, idempotent budget commands over the canonical budget table."""
import calendar
import uuid
from datetime import date,timedelta
from typing import Literal
from fastapi import APIRouter,Depends,Query
from pydantic import Field,StrictInt,model_validator
from .transactions import Command,Delete,MAX_MINOR,fail,now,replay,receipt,workspace,categories
from .budget_service import SELECT,evaluate,month_range

class BudgetInput(Command):
    name:str=Field(min_length=1,max_length=80)
    category:str=Field(min_length=1,max_length=80)
    limit_minor:StrictInt=Field(gt=0,le=MAX_MINOR)
    start_date:date
    end_date:date
    reset_period:Literal['weekly','monthly','custom']='monthly'
    alert_threshold:Literal[50,75,90,100]|None=75
    notes:str=Field(default='',max_length=2000)
    version:StrictInt|None=Field(default=None,ge=1)
    @model_validator(mode='after')
    def dates(self):
        a,z=self.start_date,self.end_date
        if not 1901<=a.year<=z.year<=2100 or z<a or (z-a).days>731:raise ValueError('Use an ordered date range of at most 732 days between 1901 and 2100.')
        if self.reset_period=='weekly' and z!=a+timedelta(days=6):raise ValueError('A weekly period ends six days after its start.')
        if self.reset_period=='monthly' and z!=date(a.year,a.month,calendar.monthrange(a.year,a.month)[1]):raise ValueError('A monthly period ends on the last day of its starting month.')
        return self

def get(c,u,d,id):
    b=c.execute(SELECT+' WHERE b.user_id=? AND b.dataset=? AND b.id=?',(u,d,id)).fetchone()
    if not b:fail('Budget not found.',404)
    return dict(b)
def options(c,u,d):
    names={x['name'] for x in categories(c,u,d) if x['kind']=='expense'}
    names.update(x['category'] for x in c.execute('SELECT category FROM budgets WHERE user_id=? AND dataset=?',(u,d)))
    return sorted(names,key=str.casefold)
def save(c,u,d,p,id=None):
    if p.category not in options(c,u,d):fail('Choose an accessible expense category.',422,'category')
    if c.execute('SELECT 1 FROM budgets WHERE user_id=? AND dataset=? AND category=? AND start_date<=? AND end_date>=? AND id<>?',(u,d,p.category,p.end_date.isoformat(),p.start_date.isoformat(),id or '')).fetchone():fail('A budget already covers this category during these dates. Choose a non-overlapping period or edit the existing budget.',409,'start_date')
    if id:
        old=get(c,u,d,id)
        if old['version']!=p.version:fail('This budget changed. Reload it before retrying.',409)
        c.execute('UPDATE budgets SET name=?,category=?,limit_minor=?,start_date=?,end_date=? WHERE id=?',(p.name,p.category,p.limit_minor,p.start_date.isoformat(),p.end_date.isoformat(),id));version=old['version']+1
    else:
        id=str(uuid.uuid4());version=1;workspace(c,u,d)
        c.execute('INSERT INTO budgets VALUES (?,?,?,?,?,?,?,?)',(id,u,d,p.name,p.category,p.limit_minor,p.start_date.isoformat(),p.end_date.isoformat()))
    c.execute('''INSERT INTO budget_metadata(budget_id,reset_period,alert_threshold,notes,version,created_at,updated_at) VALUES (?,?,?,?,?,?,?) ON CONFLICT(budget_id) DO UPDATE SET reset_period=excluded.reset_period,alert_threshold=excluded.alert_threshold,notes=excluded.notes,version=excluded.version,updated_at=excluded.updated_at''',(id,p.reset_period,p.alert_threshold,p.notes,version,now(),now()))
    return {'id':id,'version':version}

def budget_router(db,current_user,environment):
    r=APIRouter(prefix='/api/budgets',tags=['Budgets'])
    def scope(dataset:Literal['live','demo']='live'):
        if dataset=='demo' and environment=='production':fail('Sample workspaces are disabled in production.',403)
        return dataset
    def window(month):
        try:return month_range(month)
        except ValueError as e:fail(str(e))
    @r.get('/options')
    def choices(dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:return {'categories':options(c,user['id'],dataset)}
    @r.get('')
    def listing(month:str|None=None,search:str=Query('',max_length=200),category:str='',status:Literal['','On Track','Near Limit','Exceeded']='',sort:Literal['highest','name']='highest',dataset=Depends(scope),user=Depends(current_user)):
        first,last=window(month)
        with db() as c:
            data=evaluate(c,user['id'],dataset,first,last);items=data['items'];q=search.strip().casefold()
            filtered=[b for b in items if (not category or b['category']==category) and (not status or b['status']==status) and (not q or q in (b['name']+' '+b['category']+' '+b['notes']).casefold())]
            filtered.sort(key=(lambda b:(-b['spent_minor'],b['name'].casefold(),b['id'])) if sort=='highest' else (lambda b:(b['name'].casefold(),b['id'])))
            return dict(items=filtered,total=len(items),filtered_count=len(filtered),summary=data['summary'],alerts=[b for b in items if b['at_risk']],ambiguous_count=data['ambiguous_count'],categories=options(c,user['id'],dataset),period={'start':first,'end':last})
    @r.get('/{id}')
    def details(id:str,month:str|None=None,page:int=Query(1,ge=1),limit:int=Query(10,ge=1,le=50),dataset=Depends(scope),user=Depends(current_user)):
        first,last=window(month)
        with db() as c:
            b=get(c,user['id'],dataset,id);data=evaluate(c,user['id'],dataset,first,last)
            item=next((x for x in data['items'] if x['id']==id),None)
            if not item:item=b|dict(spent_minor=0,remaining_minor=b['limit_minor'],percentage=0 if b['limit_minor'] else None,status='On Track',at_risk=False,conflicted=False)
            activity=data['activity'].get(id,[]);page=min(page,max(1,(len(activity)+limit-1)//limit))
            return dict(budget=item,items=activity[(page-1)*limit:page*limit],total=len(activity),page=page,limit=limit,period={'start':first,'end':last},ambiguous_count=data['ambiguous_count'])
    @r.post('',status_code=201)
    def create(p:BudgetInput,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];fp,old=replay(c,u,p.request_key,p.model_dump(mode='json'),'budget-create:'+dataset)
            if old:return old
            return receipt(c,u,p.request_key,fp,save(c,u,dataset,p))
    @r.patch('/{id}')
    def update(id:str,p:BudgetInput,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];get(c,u,dataset,id);fp,old=replay(c,u,p.request_key,p.model_dump(mode='json'),'budget-edit:'+dataset+id)
            if old:return old
            return receipt(c,u,p.request_key,fp,save(c,u,dataset,p,id))
    @r.delete('/{id}')
    def delete(id:str,p:Delete,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];fp,old=replay(c,u,p.request_key,p.model_dump(),'budget-delete:'+dataset+id)
            if old:return old
            b=get(c,u,dataset,id)
            if b['version']!=p.version:fail('This budget changed. Reload it before retrying.',409)
            c.execute('DELETE FROM budgets WHERE id=?',(id,))
            return receipt(c,u,p.request_key,fp,{'id':id})
    return r
