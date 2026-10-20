"""Owner-scoped transaction commands and queries over the existing canonical ledger.

All commands are serialized in SQLite IMMEDIATE transactions. Metadata extends, rather
than duplicates, canonical records; transfer fees are one linked expense, never income.
"""
import csv
import hashlib
import io
import json
import sqlite3
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from .service import month_shift
from .csv_safety import csv_safe
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator

MAX_MINOR = 100_000_000_000_00
DEFAULTS = {
 'income':['Salary','Freelance','Business','Investment Returns','Gifts Received','Other Income','Income'],
 'expense':['Food','Food & Dining','Transport','Transportation','Shopping','Housing','Bills & Utilities','Utilities','Entertainment','Health','Education','Other','Fees & Charges'],
}
class Model(BaseModel):
    model_config=ConfigDict(extra='forbid', str_strip_whitespace=True)
class Command(Model):
    request_key: str=Field(min_length=16,max_length=100)
class Entry(Command):
    kind: Literal['income','expense','transfer']
    amount_minor: StrictInt=Field(gt=0,le=MAX_MINOR)
    wallet_id: str=Field(min_length=1,max_length=160)
    destination_wallet_id: str|None=Field(default=None,max_length=160)
    fee_minor: StrictInt=Field(default=0,ge=0,le=MAX_MINOR)
    mode: Literal['transfer','withdraw']='transfer'
    title: str=Field(default='',max_length=120)
    description: str=Field(default='',max_length=240)
    notes: str=Field(default='',max_length=2000)
    category: str=Field(default='',max_length=80)
    occurred_at: str
    version: StrictInt|None=Field(default=None,ge=1)
    @field_validator('occurred_at')
    @classmethod
    def valid_date(cls,v):
        try:
            d=datetime.fromisoformat(v)
            if d.tzinfo or not 1901<=d.year<=2100: raise ValueError()
        except ValueError: raise ValueError('Use a local date and time between 1901 and 2100.')
        return d.isoformat(timespec='seconds')
class Delete(Command):
    version: StrictInt=Field(ge=1)
class Wallet(Command):
    name: str=Field(min_length=1,max_length=80)
    kind: Literal['cash','bank','mobile','savings']='bank'
    opening_minor: StrictInt=Field(default=0,ge=0,le=MAX_MINOR)
    opening_date: date
    provider: str=Field(default='',max_length=80)
    currency: Literal['BDT']='BDT'
    identifier_last4: str=Field(default='',pattern=r'^([0-9]{4})?$')
    notes: str=Field(default='',max_length=2000)
    status: Literal['active','inactive']='active'
class Category(Model):
    name: str=Field(min_length=1,max_length=80)
    kind: Literal['income','expense']
    icon: Literal['receipt','wallet','calendar','plus','clock','check']|None=None
    color: Literal['#f9733b','#32865a','#c84c42','#5378c8','#9b6cc3','#777873']|None=None
class RemoveCategory(Model):
    replacement: str=Field(min_length=1,max_length=80)

def fail(message,status=422,field=None):
    raise HTTPException(status,{'message':message,**({'field_errors':{field:message}} if field else {})})
def now():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def workspace(c,u,d):c.execute('INSERT OR IGNORE INTO financial_workspaces VALUES (?,?)',(u,d))
def categories(c,u,d):
    values=[{'id':'default:'+k+':'+n,'kind':k,'name':n,'default':True} for k,names in DEFAULTS.items() for n in names]
    values += [dict(r)|{'default':False} for r in c.execute("SELECT c.id,c.kind,c.name,COALESCE(a.icon,'receipt') icon,COALESCE(a.color,'#f9733b') color FROM custom_categories c LEFT JOIN category_appearance a ON a.category_id=c.id WHERE c.user_id=? AND c.dataset=? ORDER BY c.name COLLATE NOCASE",(u,d))]
    # Imported historical mappings remain valid and visible without rewriting them.
    for r in c.execute("SELECT DISTINCT kind,category name FROM transactions WHERE user_id=? AND dataset=? AND kind!='transfer' AND category IS NOT NULL",(u,d)):
        if not any(x['kind']==r['kind'] and x['name']==r['name'] for x in values):values.append(dict(r)|{'id':'legacy:'+r['kind']+':'+r['name'],'default':True})
    return values

from .ledger import ledger, balance_at, wallets, delta

def guard_balances(c,u,d,before,after,affected,earliest):
    # O(n log n), comparing both timelines at every affected event instant.
    # Legacy deficits may not worsen; new ledgers cannot overdraw at any instant.
    for w in c.execute('SELECT * FROM wallets WHERE user_id=? AND dataset=?',(u,d)):
        if w['id'] not in affected:continue
        def deltas(rows):
            values={}
            for r in rows:
                if r['occurred_at'][:10]<w['opening_date']:continue
                change=delta(r,w['id'])
                if change:values[r['occurred_at']]=values.get(r['occurred_at'],0)+change
            return values
        b,a=deltas(before),deltas(after);old=new=w['opening_minor']
        for point in sorted(set(b)|set(a)|{earliest}):
            old+=b.get(point,0);new+=a.get(point,0)
            if point>=earliest and new<min(0,old):
                fail('Insufficient funds. This change would overdraw a wallet, including later recorded payments.',409,'wallet_id')

SELECT="""SELECT t.*,w.name wallet_name,dw.name destination_wallet_name,
 COALESCE(m.notes,'') notes,COALESCE(m.version,1) version,COALESCE(m.mode,'transfer') mode,
 COALESCE(m.created_at,t.occurred_at) created_at,COALESCE(m.updated_at,t.occurred_at) updated_at,
 COALESCE((SELECT sum(f.amount_minor) FROM transactions f WHERE f.linked_transfer_id=t.id),0) fee_minor
 FROM transactions t JOIN wallets w ON w.id=t.wallet_id
 LEFT JOIN wallets dw ON dw.id=t.destination_wallet_id LEFT JOIN transaction_metadata m ON m.transaction_id=t.id"""
def detail(c,u,d,id):
    r=c.execute(SELECT+' WHERE t.user_id=? AND t.dataset=? AND t.id=?',(u,d,id)).fetchone()
    if not r:fail('Transaction not found.',404)
    return dict(r)
def version_check(r,v):
    if v!=r['version']:fail('This transaction changed in another session. Close this dialog and reload before trying again.',409)
def replay(c,u,key,payload,operation):
    fingerprint=hashlib.sha256((operation+json.dumps(payload,sort_keys=True,default=str)).encode()).hexdigest()
    r=c.execute('SELECT * FROM financial_requests WHERE user_id=? AND request_key=?',(u,key)).fetchone()
    if r:
        if r['fingerprint']!=fingerprint:fail('This request key was already used for a different change.',409)
        return fingerprint,json.loads(r['response'])
    return fingerprint,None
def receipt(c,u,key,fingerprint,result):
    c.execute('INSERT INTO financial_requests VALUES (?,?,?,?)',(u,key,fingerprint,json.dumps(result)))
    return result

def validate_entry(c,u,d,p):
    ws={w['id']:w for w in wallets(c,u,d)}
    ids=[p.wallet_id]+([p.destination_wallet_id] if p.kind=='transfer' else [])
    for id in ids:
        w=ws.get(id)
        if not w or w['archived'] or w['status']!='active' or w['currency']!='BDT':fail('Choose an active BDT wallet belonging to this workspace.',422,'wallet_id')
        if p.occurred_at[:10]<w['opening_date']:fail('The transaction cannot precede the wallet opening date.',422,'occurred_at')
    if p.kind=='transfer':
        if p.wallet_id==p.destination_wallet_id:fail('Choose two different wallets.',422,'destination_wallet_id')
        if p.mode=='withdraw' and ws[p.destination_wallet_id]['kind']!='cash':fail('Withdrawals require a cash destination wallet.',422,'destination_wallet_id')
    else:
        if p.destination_wallet_id or p.fee_minor:fail('Only transfers may have a destination or transfer fee.')
        if not any(x['name']==p.category and x['kind']==p.kind for x in categories(c,u,d)):fail('Select a valid category for this transaction type.',422,'category')

def mutable_wallets(c,u,d,r):
    if any(w['archived'] for w in wallets(c,u,d) if w['id'] in (r['wallet_id'],r['destination_wallet_id'])):
        fail('Restore the archived wallet before changing its transaction history.',409)

def put(c,u,d,id,p,created=None,version=1):
    title=p.title or ('Withdrawal' if p.kind=='transfer' and p.mode=='withdraw' else 'Wallet transfer' if p.kind=='transfer' else p.category)
    c.execute('INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?,?,?,NULL)',(id,u,d,p.wallet_id,p.destination_wallet_id if p.kind=='transfer' else None,p.kind,p.amount_minor,title,p.description,'Transfer' if p.kind=='transfer' else p.category,p.occurred_at))
    c.execute('INSERT INTO transaction_metadata VALUES (?,?,?,?,?,?)',(id,p.notes,version,p.mode,created or now(),now()))
    if p.kind=='transfer' and p.fee_minor:
        c.execute('INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(id+':fee',u,d,p.wallet_id,None,'expense',p.fee_minor,'Transfer fee','Linked transfer fee','Fees & Charges',p.occurred_at,id))

def remove(c,id):
    c.execute('DELETE FROM transactions WHERE linked_transfer_id=?',(id,));c.execute('DELETE FROM transactions WHERE id=?',(id,))

def save_entry(c,u,d,p,id=None):
    """Shared canonical command; caller owns the surrounding transaction."""
    old=detail(c,u,d,id) if id else None
    if old:
        version_check(old,p.version)
        if old['linked_transfer_id']:fail('Edit the parent transfer; its fee is managed atomically.',409)
        if old['kind']!=p.kind:fail('Transaction type cannot change during editing.')
        mutable_wallets(c,u,d,old)
    validate_entry(c,u,d,p);before=ledger(c,u,d)
    if old:remove(c,id)
    else:id=str(uuid.uuid4())
    put(c,u,d,id,p,old['created_at'] if old else None,old['version']+1 if old else 1)
    affected={p.wallet_id,p.destination_wallet_id}
    if old:affected.update([old['wallet_id'],old['destination_wallet_id']])
    guard_balances(c,u,d,before,ledger(c,u,d),affected,min(old['occurred_at'],p.occurred_at) if old else p.occurred_at)
    return detail(c,u,d,id)

def transaction_router(db,current_user,environment):
    r=APIRouter(prefix='/api/transactions',tags=['Transactions'])
    def dataset_check(dataset):
        if dataset not in ('live','demo'):fail('Invalid workspace.')
        if dataset=='demo' and environment=='production':fail('Sample workspaces are disabled in production.',403)
    def scope(dataset:Literal['live','demo']='live'):
        dataset_check(dataset);return dataset
    @r.get('/options')
    def options(dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:return {'wallets':wallets(c,user['id'],dataset),'categories':categories(c,user['id'],dataset)}
    @r.post('/wallets',status_code=201)
    def create_wallet(p:Wallet,dataset=Depends(scope),user=Depends(current_user)):
        if not 1901<=p.opening_date.year<=2100:fail('Choose a valid opening date.')
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];fp,old=replay(c,u,p.request_key,p.model_dump(mode='json'),'wallet:'+dataset)
            if old:return old
            workspace(c,u,dataset)
            if c.execute('SELECT 1 FROM wallets WHERE user_id=? AND dataset=? AND lower(name)=lower(?)',(u,dataset,p.name)).fetchone():fail('A wallet with this name already exists.',409)
            id=str(uuid.uuid4());c.execute('INSERT INTO wallets VALUES (?,?,?,?,?,?)',(id,u,dataset,p.name,p.opening_minor,p.opening_date.isoformat()))
            c.execute('INSERT INTO wallet_metadata(wallet_id,kind) VALUES (?,?)',(id,p.kind))
            c.execute('INSERT INTO wallet_profiles VALUES (?,?,?,?,?,1,?,?)',(id,p.provider,p.identifier_last4,p.notes,p.status,now(),now()))
            return receipt(c,u,p.request_key,fp,{'id':id})
    @r.post('/categories',status_code=201)
    def create_category(p:Category,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];workspace(c,u,dataset)
            if any(x['kind']==p.kind and x['name'].casefold()==p.name.casefold() for x in categories(c,u,dataset)):fail('A category with this name already exists for this type.',409)
            id=str(uuid.uuid4());c.execute('INSERT INTO custom_categories VALUES (?,?,?,?,?)',(id,u,dataset,p.kind,p.name));c.execute('INSERT INTO category_appearance VALUES (?,?,?)',(id,p.icon or 'receipt',p.color or '#f9733b'));return {'id':id}
    @r.patch('/categories/{id}')
    def rename_category(id:str,p:Category,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];old=c.execute('SELECT * FROM custom_categories WHERE id=? AND user_id=? AND dataset=?',(id,u,dataset)).fetchone()
            if not old:fail('Custom category not found. Default categories cannot be changed.',404)
            if p.kind!=old['kind']:fail('Category type cannot be changed.')
            if any(x['id']!=id and x['kind']==p.kind and x['name'].casefold()==p.name.casefold() for x in categories(c,u,dataset)):fail('Category name already exists.',409)
            c.execute('UPDATE custom_categories SET name=? WHERE id=?',(p.name,id))
            if p.icon is not None or p.color is not None:
                existing=c.execute('SELECT icon,color FROM category_appearance WHERE category_id=?',(id,)).fetchone()
                c.execute('INSERT INTO category_appearance VALUES (?,?,?) ON CONFLICT(category_id) DO UPDATE SET icon=excluded.icon,color=excluded.color',(id,p.icon or (existing['icon'] if existing else 'receipt'),p.color or (existing['color'] if existing else '#f9733b')))
            c.execute('UPDATE transaction_metadata SET version=version+1,updated_at=? WHERE transaction_id IN (SELECT id FROM transactions WHERE user_id=? AND dataset=? AND kind=? AND category=?)',(now(),u,dataset,p.kind,old['name']))
            c.execute('UPDATE transactions SET category=? WHERE user_id=? AND dataset=? AND kind=? AND category=?',(p.name,u,dataset,p.kind,old['name']))
            if p.kind=='expense':c.execute('UPDATE budgets SET category=? WHERE user_id=? AND dataset=? AND category=?',(p.name,u,dataset,old['name']))
            return {'message':'Category updated.'}
    @r.delete('/categories/{id}')
    def delete_category(id:str,p:RemoveCategory,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];old=c.execute('SELECT * FROM custom_categories WHERE id=? AND user_id=? AND dataset=?',(id,u,dataset)).fetchone()
            if not old:fail('Custom category not found. Defaults cannot be removed.',404)
            if not any(x['id']!=id and x['kind']==old['kind'] and x['name']==p.replacement for x in categories(c,u,dataset)):fail('Choose another category of the same type.')
            c.execute('UPDATE transaction_metadata SET version=version+1,updated_at=? WHERE transaction_id IN (SELECT id FROM transactions WHERE user_id=? AND dataset=? AND kind=? AND category=?)',(now(),u,dataset,old['kind'],old['name']))
            c.execute('UPDATE transactions SET category=? WHERE user_id=? AND dataset=? AND kind=? AND category=?',(p.replacement,u,dataset,old['kind'],old['name']))
            if old['kind']=='expense':c.execute('UPDATE budgets SET category=? WHERE user_id=? AND dataset=? AND category=?',(p.replacement,u,dataset,old['name']))
            c.execute('DELETE FROM custom_categories WHERE id=?',(id,));return {'message':'Category removed; records reassigned.'}
    def filters(start:date|None=None,end:date|None=None,search:str=Query('',max_length=100),kind:Literal['','income','expense','transfer']='',category:str=Query('',max_length=80),wallet:str=Query('',max_length=160),minimum:int|None=Query(None,ge=0,le=MAX_MINOR),maximum:int|None=Query(None,ge=0,le=MAX_MINOR),sort:Literal['newest','oldest','highest','lowest']='newest'):
        first=start or date.today().replace(day=1);last=end or date(date.today().year+1,1,1)-timedelta(days=1)
        if end is None:
            first_next=(first.replace(day=28)+timedelta(days=4)).replace(day=1);last=first_next-timedelta(days=1)
        if first>last or first.year<1901 or last.year>2100 or ((last-first).days>3660 and not wallet):fail('Choose an ordered date range of no more than ten years.')
        if minimum is not None and maximum is not None and minimum>maximum:fail('Minimum amount must not exceed maximum amount.')
        return dict(start=first.isoformat(),end=last.isoformat(),search=search,kind=kind,category=category,wallet=wallet,minimum=minimum,maximum=maximum,sort=sort)
    def listing(c,u,d,f,page,limit,export=False):
        where='t.user_id=? AND t.dataset=? AND substr(t.occurred_at,1,10)>=? AND substr(t.occurred_at,1,10)<=?';args=[u,d,f['start'],f['end']]
        summary_rows=c.execute('SELECT kind,sum(amount_minor) amount,count(*) count FROM transactions t WHERE '+where+' GROUP BY kind',args).fetchall()
        counts={x['kind']:x['count'] for x in summary_rows};sums={x['kind']:x['amount'] for x in summary_rows}
        summary={'income_minor':sums.get('income',0),'expenses_minor':sums.get('expense',0),'net_minor':sums.get('income',0)-sums.get('expense',0),'count':sum(counts.values())}
        first=date.fromisoformat(f['start']);last=date.fromisoformat(f['end'])
        previous_end=first-timedelta(days=1)
        previous_start=month_shift(first,-1) if first.day==1 and (last+timedelta(days=1)).day==1 else first-timedelta(days=(last-first).days+1)
        previous={x['kind']:x['amount'] for x in c.execute('SELECT kind,sum(amount_minor) amount FROM transactions WHERE user_id=? AND dataset=? AND substr(occurred_at,1,10)>=? AND substr(occurred_at,1,10)<=? GROUP BY kind',(u,d,previous_start.isoformat(),previous_end.isoformat()))}
        summary['previous_income_minor']=previous.get('income',0);summary['previous_expenses_minor']=previous.get('expense',0)
        summary['income_change']=round((summary['income_minor']-previous['income'])/previous['income']*100,1) if previous.get('income') else None
        summary['expense_change']=round((summary['expenses_minor']-previous['expense'])/previous['expense']*100,1) if previous.get('expense') else None
        summary['net_change_minor']=summary['net_minor']-(previous.get('income',0)-previous.get('expense',0))
        for key,condition in [('search',"instr(lower(t.title||' '||t.description||' '||COALESCE(m.notes,'')),lower(?))>0"),('kind','t.kind=?'),('category',"COALESCE(NULLIF(t.category,''),'Other')=?"),('wallet','(t.wallet_id=? OR t.destination_wallet_id=?)')]:
            if f[key]:where+=' AND '+condition;args.extend([f[key]]*(2 if key=='wallet' else 1))
        for key,op in [('minimum','>='),('maximum','<=')]:
            if f[key] is not None:where+=' AND t.amount_minor'+op+'?';args.append(f[key])
        base=SELECT+' WHERE '+where
        total=c.execute('SELECT count(*) FROM ('+base+')',args).fetchone()[0]
        if export and total>50000:fail('Export is limited to 50,000 records. Narrow the date range.',413)
        order={'newest':'t.occurred_at DESC','oldest':'t.occurred_at ASC','highest':'t.amount_minor DESC','lowest':'t.amount_minor ASC'}[f['sort']]+',t.id ASC'
        pages=max(1,(total+limit-1)//limit);page=min(page,pages)
        items=[dict(x) for x in c.execute(base+' ORDER BY '+order+(' LIMIT 50000' if export else ' LIMIT ? OFFSET ?'),args if export else args+[limit,(page-1)*limit])]
        return dict(items=items,total=total,page=page,limit=limit,pages=pages,summary=summary,counts=counts,period={'start':f['start'],'end':f['end']})
    @r.get('')
    def get_list(f=Depends(filters),dataset=Depends(scope),page:int=Query(1,ge=1,le=1000000),limit:int=Query(10,ge=10,le=50),user=Depends(current_user)):
        if limit not in (10,25,50):fail('Choose a page size of 10, 25 or 50.')
        with db() as c:return listing(c,user['id'],dataset,f,page,limit)
    @r.get('/export')
    def export(f=Depends(filters),dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:data=listing(c,user['id'],dataset,f,1,50,True)
        out=io.StringIO(newline='');writer=csv.writer(out);writer.writerow(['Transaction ID','Transaction','Description','Notes','Category','Wallet','Destination','Date','Amount (BDT)','Type','Linked transfer'])
        safe=csv_safe
        for x in data['items']:
            amount=x['amount_minor'];money=f'{amount//100}.{amount%100:02d}'
            writer.writerow([safe(x[k]) for k in ['id','title','description','notes','category','wallet_name','destination_wallet_name','occurred_at']]+[money,x['kind'],safe(x['linked_transfer_id'])])
        return Response('\ufeff'+out.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="fincept-transactions.csv"'})
    @r.get('/{id}')
    def get_one(id:str,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:return detail(c,user['id'],dataset,id)
    @r.post('',status_code=201)
    def create(p:Entry,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];fp,old=replay(c,u,p.request_key,p.model_dump(),'create:'+dataset)
            if old:return old
            return receipt(c,u,p.request_key,fp,save_entry(c,u,dataset,p))
    @r.patch('/{id}')
    def update(id:str,p:Entry,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];fp,repeated=replay(c,u,p.request_key,p.model_dump(),'edit:'+dataset+':'+id)
            if repeated:return repeated
            return receipt(c,u,p.request_key,fp,save_entry(c,u,dataset,p,id))
    @r.delete('/{id}')
    def delete(id:str,p:Delete,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];fp,repeated=replay(c,u,p.request_key,p.model_dump(),'delete:'+dataset+':'+id)
            if repeated:return repeated
            old=detail(c,u,dataset,id);version_check(old,p.version);mutable_wallets(c,u,dataset,old)
            if old['linked_transfer_id']:fail('Delete the parent transfer to reverse its fee together.',409)
            before=ledger(c,u,dataset);remove(c,id)
            guard_balances(c,u,dataset,before,ledger(c,u,dataset),{old['wallet_id'],old['destination_wallet_id']},old['occurred_at'])
            return receipt(c,u,p.request_key,fp,{'message':'Transaction deleted. Wallet balances updated.'})
    return r
