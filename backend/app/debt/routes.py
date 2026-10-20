"""Tracking-only debt ledger. No wallet movements or automatic transactions."""
import calendar
from datetime import date, datetime, timedelta
from typing import Literal
from uuid import uuid4
from zoneinfo import ZoneInfo
from fastapi import APIRouter,Depends,Query
from pydantic import Field,StrictInt,field_validator,model_validator
from ..finance.transactions import Command,Delete,MAX_MINOR,fail,now,replay,receipt,workspace
from ..planner.routes import day,valid_zone

class Obligation(Command):
    kind:Literal['borrowed','lent','emi']
    name:str=Field(min_length=1,max_length=120)
    counterparty:str=Field(min_length=1,max_length=100)
    principal_minor:StrictInt=Field(gt=0,le=MAX_MINOR)
    interest_minor:StrictInt=Field(default=0,ge=0,le=MAX_MINOR)
    opened_date:date
    due_date:date|None=None
    first_date:date|None=None
    frequency:Literal['Monthly','Weekly']='Monthly'
    installment_minor:StrictInt=Field(default=0,ge=0,le=MAX_MINOR)
    installments:StrictInt=Field(default=0,ge=0,le=600)
    purchase_minor:StrictInt=Field(default=0,ge=0,le=MAX_MINOR)
    down_minor:StrictInt=Field(default=0,ge=0,le=MAX_MINOR)
    notes:str=Field(default='',max_length=2000)
    version:StrictInt|None=Field(default=None,ge=1)
    @field_validator('opened_date','due_date','first_date')
    @classmethod
    def dates(cls,v):return day(v) if v else v
    @model_validator(mode='after')
    def terms(self):
        if self.due_date and self.due_date<self.opened_date:raise ValueError('Due date cannot precede the original date.')
        if self.kind=='emi':
            total=self.principal_minor+self.interest_minor
            if not self.first_date or self.first_date<self.opened_date:raise ValueError('Choose a first installment date on or after the purchase date.')
            if not self.installments or not self.installment_minor:raise ValueError('Enter installment amount and count.')
            if self.purchase_minor-self.down_minor!=self.principal_minor:raise ValueError('Financed principal must equal purchase price less down payment.')
            if not self.installment_minor*(self.installments-1)<total<=self.installment_minor*self.installments:raise ValueError('Installment count and amount must cover the balance with a positive final installment no larger than the regular amount.')
            schedule(self.model_dump(mode='json'))
        return self

class Payment(Delete):
    principal_minor:StrictInt=Field(ge=0,le=MAX_MINOR)
    interest_minor:StrictInt=Field(default=0,ge=0,le=MAX_MINOR)
    fee_minor:StrictInt=Field(default=0,ge=0,le=MAX_MINOR)
    paid_date:date
    note:str=Field(default='',max_length=2000)
    _date=field_validator('paid_date')(day)
    @model_validator(mode='after')
    def positive(self):
        if not self.principal_minor+self.interest_minor+self.fee_minor:raise ValueError('Enter a positive payment.')
        return self
class Reversal(Delete):
    reason:str=Field(min_length=3,max_length=500)

def schedule(r):
    if r['kind']!='emi':return []
    first=date.fromisoformat(r['first_date']);p=r['principal_minor'];interest=r['interest_minor'];total=p+interest;result=[];assigned=0
    for i in range(r['installments']):
        if r['frequency']=='Weekly':due=first+timedelta(days=7*i)
        else:
            y=first.year+(first.month-1+i)//12;m=(first.month-1+i)%12+1
            if y>2100:raise ValueError('Schedule must end by 2100.')
            due=date(y,m,min(first.day,calendar.monthrange(y,m)[1]))
        if due.year>2100:raise ValueError('Schedule must end by 2100.')
        amount=min(r['installment_minor'],total-assigned)
        # Cumulative proportional rounding preserves exact principal and interest totals.
        principal=((assigned+amount)*p//total)-(assigned*p//total)
        result.append(dict(number=i+1,due_date=due.isoformat(),principal_minor=principal,interest_minor=amount-principal,amount_minor=amount));assigned+=amount
    return result

def owned(c,u,d,id):
    r=c.execute('SELECT * FROM debt_records WHERE id=? AND user_id=? AND dataset=?',(id,u,d)).fetchone()
    if not r:fail('Debt or loan not found.',404)
    return dict(r)
def history(c,u,d,id=None):
    return [dict(x) for x in c.execute('SELECT p.*,r.name,r.kind FROM debt_payments p JOIN debt_records r ON r.id=p.debt_id WHERE p.user_id=? AND p.dataset=?'+(' AND p.debt_id=?' if id else '')+' ORDER BY p.paid_date DESC,p.created_at DESC,p.id',(u,d,id) if id else (u,d))]
def enrich(c,r,today):
    h=history(c,r['user_id'],r['dataset'],r['id']);reversed_ids={x['reversal_of'] for x in h if x['reversal_of']};valid=[x for x in h if not x['reversal_of'] and x['id'] not in reversed_ids]
    pp=sum(x['principal_minor'] for x in valid);pi=sum(x['interest_minor'] for x in valid);pr=r['principal_minor']-pp;ir=r['interest_minor']-pi
    dues=[];allocp=pp;alloci=pi
    for row in schedule(r):
        a=min(allocp,row['principal_minor']);b=min(alloci,row['interest_minor']);allocp-=a;alloci-=b
        rem=row['amount_minor']-a-b
        dues.append(row|dict(remaining_minor=rem,paid_principal_minor=a,paid_interest_minor=b,status='Paid' if rem==0 else 'Overdue' if row['due_date']<today else 'Due Today' if row['due_date']==today else 'Upcoming'))
    if r['kind']!='emi' and r['due_date'] and pr+ir:dues=[dict(number=1,due_date=r['due_date'],amount_minor=pr+ir,remaining_minor=pr+ir,principal_minor=pr,interest_minor=ir,status='Overdue' if r['due_date']<today else 'Due Today' if r['due_date']==today else 'Upcoming')]
    state='Paid Off' if pr+ir==0 else 'Overdue' if any(x['status']=='Overdue' for x in dues) else 'Active'
    return r|dict(paid_minor=pp,paid_interest_minor=pi,outstanding_minor=pr,interest_remaining_minor=ir,state=state,schedule=dues,history=[x|dict(status='Reversal' if x['reversal_of'] else 'Reversed' if x['id'] in reversed_ids else 'Recorded') for x in h])
def check(r,p):
    if p.version!=r['version']:fail('This record changed. Reload before retrying.',409)

def debt_router(db,current_user,environment):
    r=APIRouter(prefix='/api/debts',tags=['debts'])
    def scope(dataset:Literal['live','demo']='live'):
        if dataset=='demo' and environment!='development':fail('Sample workspace unavailable.',403)
        return dataset
    def zone(timezone:str='UTC'):
        try:return valid_zone(timezone)
        except ValueError:fail('Choose a valid IANA timezone.')
    def today(z):return datetime.now(ZoneInfo(z)).date().isoformat()
    @r.get('')
    def listing(dataset=Depends(scope),timezone=Depends(zone),user=Depends(current_user)):
        with db() as c:
            day=today(timezone);items=[enrich(c,dict(x),day) for x in c.execute('SELECT * FROM debt_records WHERE user_id=? AND dataset=? ORDER BY created_at,id',(user['id'],dataset))];active=[x for x in items if not x['archived']];outgoing=[s|{'debt_id':x['id'],'name':x['name'],'kind':x['kind']} for x in active if x['kind']!='lent' for s in x['schedule'] if s['remaining_minor']>0];end=(date.fromisoformat(day)+timedelta(days=30)).isoformat();soon=[s for s in outgoing if day<s['due_date']<=end];late=[s for s in outgoing if s['due_date']<day]
            return dict(items=items,today=day,summary=dict(borrowed_minor=sum(x['outstanding_minor'] for x in active if x['kind']!='lent'),lent_minor=sum(x['outstanding_minor'] for x in active if x['kind']=='lent'),upcoming_minor=sum(s['remaining_minor'] for s in soon),upcoming_count=len(soon),overdue_minor=sum(s['remaining_minor'] for s in late),overdue_count=len(late)))
    @r.post('/preview')
    def preview(p:Obligation,user=Depends(current_user)):return dict(schedule=schedule(p.model_dump(mode='json')))
    @r.post('',status_code=201)
    def create(p:Obligation,dataset=Depends(scope),timezone=Depends(zone),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];fp,old=replay(c,u,p.request_key,p.model_dump(mode='json'),'debt-create:'+dataset)
            if old:return old
            workspace(c,u,dataset);id=str(uuid4());v=p.model_dump(mode='json');cols=['kind','name','counterparty','principal_minor','interest_minor','opened_date','due_date','first_date','frequency','installment_minor','installments','purchase_minor','down_minor','notes']
            c.execute('INSERT INTO debt_records (id,user_id,dataset,'+','.join(cols)+',created_at) VALUES ('+','.join('?' for _ in range(18))+')',[id,u,dataset]+[v[k] for k in cols]+[now()])
            return receipt(c,u,p.request_key,fp,enrich(c,owned(c,u,dataset,id),today(timezone)))
    @r.patch('/{id}')
    def edit(id:str,p:Obligation,dataset=Depends(scope),timezone=Depends(zone),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];fp,old=replay(c,u,p.request_key,p.model_dump(mode='json'),'debt-edit:'+dataset+id)
            if old:return old
            row=owned(c,u,dataset,id);check(row,p)
            if row['archived']:fail('Archived records cannot be edited.')
            v=p.model_dump(mode='json');terms=['kind','principal_minor','interest_minor','opened_date','due_date','first_date','frequency','installment_minor','installments','purchase_minor','down_minor']
            if history(c,u,dataset,id) and any(row[k]!=v[k] for k in terms):fail('Financial terms are immutable after the first payment. Only name, counterparty and notes can change.')
            if v['kind']!=row['kind']:fail('Record direction cannot be changed.')
            cols=terms+['name','counterparty','notes'];c.execute('UPDATE debt_records SET '+','.join(k+'=?' for k in cols)+',version=version+1 WHERE id=?',[v[k] for k in cols]+[id])
            return receipt(c,u,p.request_key,fp,enrich(c,owned(c,u,dataset,id),today(timezone)))
    @r.post('/{id}/payments',status_code=201)
    def pay(id:str,p:Payment,dataset=Depends(scope),timezone=Depends(zone),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];fp,old=replay(c,u,p.request_key,p.model_dump(mode='json'),'debt-pay:'+dataset+id)
            if old:return old
            row=enrich(c,owned(c,u,dataset,id),today(timezone));check(row,p)
            if row['archived']:fail('Archived records cannot receive payments.')
            if p.paid_date.isoformat()<row['opened_date'] or p.paid_date.isoformat()>today(timezone):fail('Payment date must be between the original date and today.')
            if p.principal_minor>row['outstanding_minor'] or p.interest_minor>row['interest_remaining_minor']:fail('Payment exceeds remaining principal or agreed interest.')
            c.execute('INSERT INTO debt_payments VALUES (?,?,?,?,?,?,?,?,?,?,?)',(str(uuid4()),u,dataset,id,p.principal_minor,p.interest_minor,p.fee_minor,p.paid_date.isoformat(),p.note,None,now()))
            c.execute('UPDATE debt_records SET version=version+1 WHERE id=?',(id,))
            return receipt(c,u,p.request_key,fp,enrich(c,owned(c,u,dataset,id),today(timezone)))
    @r.post('/{id}/payments/{payment_id}/reverse')
    def reverse(id:str,payment_id:str,p:Reversal,dataset=Depends(scope),timezone=Depends(zone),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];fp,old=replay(c,u,p.request_key,p.model_dump(mode='json'),'debt-reverse:'+dataset+id+payment_id)
            if old:return old
            row=owned(c,u,dataset,id);check(row,p)
            if row['archived']:fail('Archived history is immutable.')
            pay=next((x for x in history(c,u,dataset,id) if x['id']==payment_id),None)
            if not pay or pay['reversal_of']:fail('Original payment not found.',404)
            if c.execute('SELECT 1 FROM debt_payments WHERE reversal_of=?',(payment_id,)).fetchone():fail('Payment was already reversed.',409)
            c.execute('INSERT INTO debt_payments VALUES (?,?,?,?,?,?,?,?,?,?,?)',(str(uuid4()),u,dataset,id,pay['principal_minor'],pay['interest_minor'],pay['fee_minor'],today(timezone),p.reason,payment_id,now()))
            c.execute('UPDATE debt_records SET version=version+1 WHERE id=?',(id,))
            return receipt(c,u,p.request_key,fp,enrich(c,owned(c,u,dataset,id),today(timezone)))
    @r.delete('/{id}')
    def archive(id:str,p:Delete,dataset=Depends(scope),timezone=Depends(zone),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];fp,old=replay(c,u,p.request_key,p.model_dump(mode='json'),'debt-archive:'+dataset+id)
            if old:return old
            row=enrich(c,owned(c,u,dataset,id),today(timezone));check(row,p)
            if row['outstanding_minor']+row['interest_remaining_minor']:fail('Settle the balance before archiving.')
            c.execute('UPDATE debt_records SET archived=1,version=version+1 WHERE id=?',(id,))
            return receipt(c,u,p.request_key,fp,{'archived':True})
    return r
