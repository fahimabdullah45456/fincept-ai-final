"""Purchase planning, not spending. Existing wallet/Planner/EMI sources are read only."""
from datetime import date,datetime,timedelta
from typing import Literal
from uuid import uuid4
from fastapi import APIRouter,Depends,Query
from pydantic import Field,StrictInt,field_validator,model_validator
from ..finance.transactions import Model,Command,Delete,MAX_MINOR,fail,now,replay,receipt,workspace
from ..finance.ledger import wallets
from ..planner.routes import day
from ..debt.routes import enrich
from .fx import rates,CURRENCIES

class Item(Model):
    name:str=Field(min_length=1,max_length=120)
    quantity:StrictInt=Field(default=1,ge=1,le=100000)
    unit_minor:StrictInt=Field(default=0,ge=0,le=MAX_MINOR)
    category:str=Field(default='Other',min_length=1,max_length=80)
    purchased:bool=False
    actual_minor:StrictInt|None=Field(default=None,ge=0,le=MAX_MINOR)
    purchased_date:date|None=None
    notes:str=Field(default='',max_length=2000)
    @field_validator('purchased_date')
    @classmethod
    def valid_date(cls,v):return day(v) if v else v
    @model_validator(mode='after')
    def valid(self):
        if self.quantity*self.unit_minor>MAX_MINOR:raise ValueError('Estimated total is too large.')
        if self.purchased:
            if not self.purchased_date or self.purchased_date>date.today():raise ValueError('Enter a purchase date no later than today.')
        elif self.actual_minor is not None or self.purchased_date:raise ValueError('Actual cost and purchase date require a purchased item.')
        return self
class ItemInput(Item,Command):
    version:StrictInt|None=Field(default=None,ge=1)
class ListInput(Command):
    name:str=Field(min_length=1,max_length=100)
    category:str=Field(default='Other',min_length=1,max_length=80)
    target_date:date|None=None
    notes:str=Field(default='',max_length=2000)
    version:StrictInt|None=Field(default=None,ge=1)
    items:list[Item]=Field(default_factory=list,max_length=200)
    @field_validator('target_date')
    @classmethod
    def valid_day(cls,v):return day(v) if v else v

def owned(c,u,d,id):
    r=c.execute('SELECT * FROM shopping_lists WHERE id=? AND user_id=? AND dataset=?',(id,u,d)).fetchone()
    if not r:fail('Shopping list not found.',404)
    return dict(r)
def detail(c,u,d,id):
    r=owned(c,u,d,id);items=[dict(x) for x in c.execute('SELECT * FROM shopping_items WHERE list_id=? AND user_id=? AND dataset=? ORDER BY rowid',(id,u,d))];p=[x for x in items if x['purchased']];known=[x for x in p if x['actual_minor'] is not None]
    return r|dict(items=items,estimated_minor=sum(x['quantity']*x['unit_minor'] for x in items),remaining_minor=sum(x['quantity']*x['unit_minor'] for x in items if not x['purchased']),purchased_count=len(p),actual_minor=sum(x['actual_minor'] for x in known) if known else None,unknown_actual_count=len(p)-len(known),comparable_estimate_minor=sum(x['quantity']*x['unit_minor'] for x in known),complete=bool(items) and len(p)==len(items))
def check(row,p):
    if p.version!=row['version']:fail('This record changed. Reload before retrying.',409)
def insert_item(c,u,d,id,p):
    c.execute('INSERT INTO shopping_items (id,list_id,user_id,dataset,name,quantity,unit_minor,category,purchased,actual_minor,purchased_date,notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(str(uuid4()),id,u,d,p.name,p.quantity,p.unit_minor,p.category,int(p.purchased),p.actual_minor,p.purchased_date.isoformat() if p.purchased_date else None,p.notes))

def hub_router(db,current_user,environment):
    r=APIRouter(prefix='/api/hub',tags=['hub'])
    def scope(dataset:Literal['live','demo']='live'):
        if dataset=='demo' and environment!='development':fail('Sample workspace unavailable.',403)
        return dataset
    @r.get('')
    def listing(dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            u=user['id'];lists=[detail(c,u,dataset,x['id']) for x in c.execute('SELECT id FROM shopping_lists WHERE user_id=? AND dataset=? ORDER BY created_at DESC,id',(u,dataset))];ws=[x for x in wallets(c,u,dataset) if not x['archived'] and x['status']=='active'];active=[x for x in lists if not x['complete']];today=date.today().isoformat();end=(date.today()+timedelta(days=30)).isoformat();activities=[]
            for x in c.execute("SELECT id,title,due_date,category FROM planner_tasks WHERE user_id=? AND dataset=? AND status IN ('To Do','In Progress') AND due_date>=? AND due_date<=?",(u,dataset,today,end)):activities.append(dict(id=x['id'],title=x['title'],date=x['due_date'],kind='Scheduled task',amount_minor=None,url='/planner?month='+x['due_date'][:7]))
            for x in c.execute("SELECT g.id,g.name,g.target_date,m.monthly_minor,o.planned_minor,o.frequency FROM financial_goals g JOIN planner_occasions o ON o.goal_id=g.id JOIN goal_metadata m ON m.goal_id=g.id WHERE g.user_id=? AND g.dataset=? AND m.archived=0 AND m.state='active' AND g.target_date>=? AND g.target_date<=?",(u,dataset,today,end)):
                amount=x['monthly_minor'] if x['frequency']=='Monthly' else x['planned_minor']
                activities.append(dict(id=x['id'],title=x['name'],date=x['target_date'],kind='Occasion · planned allocation, not a payment',amount_minor=amount or None,url='/planner?tab=plans'))
            for x in c.execute("SELECT * FROM debt_records WHERE user_id=? AND dataset=? AND kind='emi' AND archived=0",(u,dataset)):
                for s in enrich(c,dict(x),today)['schedule']:
                    if s['remaining_minor'] and today<=s['due_date']<=end:activities.append(dict(id=x['id']+':'+str(s['number']),title=x['name'],date=s['due_date'],kind='EMI · scheduled, not paid',amount_minor=s['remaining_minor'],url='/debt-loans?tab=emi&record='+x['id']))
            activities.sort(key=lambda x:(x['date'],x['id']))
            return dict(lists=lists,wallets=ws,total_minor=sum(x['balance_minor'] for x in ws),activities=activities,today=today,summary=dict(active_lists=len(active),estimated_minor=sum(x['estimated_minor'] for x in active),purchased_items=sum(x['purchased_count'] for x in active),remaining_items=sum(len(x['items'])-x['purchased_count'] for x in active)))
    @r.get('/rates')
    def exchange(base:Literal['BDT','USD','EUR','GBP','INR','JPY','CAD','AUD','SAR','AED']='BDT',user=Depends(current_user)):return rates(db,base)
    @r.post('/lists',status_code=201)
    def create(p:ListInput,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];fp,old=replay(c,u,p.request_key,p.model_dump(mode='json'),'shopping-create:'+dataset)
            if old:return old
            workspace(c,u,dataset);id=str(uuid4());c.execute('INSERT INTO shopping_lists (id,user_id,dataset,name,category,target_date,notes,created_at) VALUES (?,?,?,?,?,?,?,?)',(id,u,dataset,p.name,p.category,p.target_date.isoformat() if p.target_date else None,p.notes,now()))
            for item in p.items:insert_item(c,u,dataset,id,item)
            return receipt(c,u,p.request_key,fp,detail(c,u,dataset,id))
    @r.patch('/lists/{id}')
    def edit(id:str,p:ListInput,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];fp,old=replay(c,u,p.request_key,p.model_dump(mode='json'),'shopping-edit:'+dataset+id)
            if old:return old
            check(owned(c,u,dataset,id),p)
            if p.items:fail('Edit items individually to preserve their versions.')
            c.execute('UPDATE shopping_lists SET name=?,category=?,target_date=?,notes=?,version=version+1 WHERE id=?',(p.name,p.category,p.target_date.isoformat() if p.target_date else None,p.notes,id))
            return receipt(c,u,p.request_key,fp,detail(c,u,dataset,id))
    @r.delete('/lists/{id}')
    def remove(id:str,p:Delete,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];fp,old=replay(c,u,p.request_key,p.model_dump(mode='json'),'shopping-delete:'+dataset+id)
            if old:return old
            check(owned(c,u,dataset,id),p);c.execute('DELETE FROM shopping_lists WHERE id=?',(id,));return receipt(c,u,p.request_key,fp,{'deleted':True})
    @r.post('/lists/{id}/items',status_code=201)
    def add_item(id:str,p:ItemInput,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];fp,old=replay(c,u,p.request_key,p.model_dump(mode='json'),'item-create:'+dataset+id)
            if old:return old
            owned(c,u,dataset,id)
            if c.execute('SELECT count(*) FROM shopping_items WHERE list_id=?',(id,)).fetchone()[0]>=200:fail('A list supports up to 200 items.')
            insert_item(c,u,dataset,id,p);c.execute('UPDATE shopping_lists SET version=version+1 WHERE id=?',(id,));return receipt(c,u,p.request_key,fp,detail(c,u,dataset,id))
    @r.patch('/lists/{id}/items/{item_id}')
    def edit_item(id:str,item_id:str,p:ItemInput,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];fp,old=replay(c,u,p.request_key,p.model_dump(mode='json'),'item-edit:'+dataset+id+item_id)
            if old:return old
            owned(c,u,dataset,id);row=c.execute('SELECT * FROM shopping_items WHERE id=? AND list_id=?',(item_id,id)).fetchone()
            if not row:fail('Item not found.',404)
            check(row,p);c.execute('UPDATE shopping_items SET name=?,quantity=?,unit_minor=?,category=?,purchased=?,actual_minor=?,purchased_date=?,notes=?,version=version+1 WHERE id=?',(p.name,p.quantity,p.unit_minor,p.category,int(p.purchased),p.actual_minor,p.purchased_date.isoformat() if p.purchased_date else None,p.notes,item_id));c.execute('UPDATE shopping_lists SET version=version+1 WHERE id=?',(id,))
            return receipt(c,u,p.request_key,fp,detail(c,u,dataset,id))
    @r.delete('/lists/{id}/items/{item_id}')
    def remove_item(id:str,item_id:str,p:Delete,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];fp,old=replay(c,u,p.request_key,p.model_dump(mode='json'),'item-delete:'+dataset+id+item_id)
            if old:return old
            owned(c,u,dataset,id);row=c.execute('SELECT * FROM shopping_items WHERE id=? AND list_id=?',(item_id,id)).fetchone()
            if not row:fail('Item not found.',404)
            check(row,p);c.execute('DELETE FROM shopping_items WHERE id=?',(item_id,));c.execute('UPDATE shopping_lists SET version=version+1 WHERE id=?',(id,));return receipt(c,u,p.request_key,fp,{'deleted':True})
    return r
