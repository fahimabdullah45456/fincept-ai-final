"""Wallet metadata, auditable non-income balance events and lifecycle commands.
Creation and internal transfers reuse /api/transactions commands, never a second ledger.
"""
import uuid
from datetime import datetime
from typing import Literal
from fastapi import APIRouter,Depends
from pydantic import Field,StrictInt
from .transactions import Model,Command,Entry,MAX_MINOR,fail,now,replay,receipt,guard_balances
from .ledger import wallets,ledger,balance_at,delta

class Metadata(Command):
    name:str=Field(min_length=1,max_length=80)
    kind:Literal['cash','bank','mobile','savings']
    provider:str=Field(default='',max_length=80)
    identifier_last4:str=Field(default='',pattern=r'^([0-9]{4})?$')
    notes:str=Field(default='',max_length=2000)
    status:Literal['active','inactive']='active'
    version:StrictInt=Field(ge=1)
class Lifecycle(Command):
    version:StrictInt=Field(ge=1)
class Event(Command):
    classification:Literal['external','adjustment']
    amount_minor:StrictInt|None=Field(default=None,gt=0,le=MAX_MINOR)
    corrected_minor:StrictInt|None=Field(default=None,ge=0,le=MAX_MINOR)
    expected_balance_minor:StrictInt|None=None
    reason:str=Field(min_length=1,max_length=2000)
    source:Literal['Salary','Freelance Income','Gift','Cash Deposit','Other']='Other'
    occurred_at:str
    version:StrictInt=Field(ge=1)

    # Same local-date validation as canonical transactions (no timezone ambiguity).
    from pydantic import field_validator
    @field_validator('occurred_at')
    @classmethod
    def valid_date(cls,v):return Entry.valid_date(v)

def wallet_router(db,current_user,environment):
    r=APIRouter(prefix='/api/wallets',tags=['Wallets'])
    def scope(dataset:Literal['live','demo']='live'):
        if dataset=='demo' and environment=='production':fail('Sample workspaces are disabled in production.',403)
        return dataset
    def get(c,u,d,id):
        w=next((w for w in wallets(c,u,d) if w['id']==id),None)
        if not w:fail('Wallet not found.',404)
        return w
    def check(w,p):
        if w['version']!=p.version:fail('This wallet changed. Close this dialog and reload before retrying.',409)
    def profile(c,w,**fields):
        c.execute('INSERT OR IGNORE INTO wallet_profiles(wallet_id,created_at,updated_at) VALUES (?,?,?)',(w['id'],now(),now()))
        if fields:
            c.execute('UPDATE wallet_profiles SET '+','.join(k+'=?' for k in fields)+',version=version+1,updated_at=? WHERE wallet_id=?',(*fields.values(),now(),w['id']))
        else:c.execute('UPDATE wallet_profiles SET version=version+1,updated_at=? WHERE wallet_id=?',(now(),w['id']))
    @r.get('')
    def listing(dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            ws=wallets(c,user['id'],dataset)
            active=[w for w in ws if not w['archived'] and w['status']=='active']
            summary={k:{'balance_minor':sum(w['balance_minor'] for w in active if k=='total' or w['kind']==k),'count':sum(1 for w in active if k=='total' or w['kind']==k)} for k in ['total','bank','mobile','cash','savings']}
            return {'items':ws,'summary':summary}
    @r.get('/{id}')
    def details(id:str,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            u=user['id'];w=get(c,u,dataset,id)
            activity=[{'id':x['id'],'kind':x['kind'],'title':x.get('title') or x.get('reason','Transaction'),'occurred_at':x['occurred_at'],'delta_minor':delta(x,id),'source':x.get('source','')} for x in ledger(c,u,dataset) if x['wallet_id']==id or x.get('destination_wallet_id')==id]
            return {'wallet':w,'activity':sorted(activity,key=lambda x:(x['occurred_at'],x['id']),reverse=True)[:50]}
    @r.patch('/{id}')
    def update(id:str,p:Metadata,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];fp,old=replay(c,u,p.request_key,p.model_dump(),'wallet-edit:'+dataset+id)
            if old:return old
            w=get(c,u,dataset,id);check(w,p)
            if c.execute('SELECT 1 FROM wallets WHERE user_id=? AND dataset=? AND lower(name)=lower(?) AND id<>?',(u,dataset,p.name,id)).fetchone():fail('A wallet with this name already exists.',409,'name')
            c.execute('UPDATE wallets SET name=? WHERE id=?',(p.name,id))
            c.execute('INSERT INTO wallet_metadata(wallet_id,kind) VALUES (?,?) ON CONFLICT(wallet_id) DO UPDATE SET kind=excluded.kind',(id,p.kind))
            profile(c,w,provider=p.provider,identifier_last4=p.identifier_last4,notes=p.notes,status=p.status)
            return receipt(c,u,p.request_key,fp,{'id':id})
    @r.post('/{id}/events',status_code=201)
    def event(id:str,p:Event,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];fp,old=replay(c,u,p.request_key,p.model_dump(),'wallet-event:'+dataset+id)
            if old:return old
            w=get(c,u,dataset,id);check(w,p)
            if w['archived'] or w['status']!='active':fail('Choose an active wallet.',422,'wallet_id')
            if p.occurred_at[:10]<w['opening_date']:fail('The event cannot precede the opening date.',422,'occurred_at')
            before=ledger(c,u,dataset)
            if p.corrected_minor is not None:
                if p.classification!='adjustment' or p.amount_minor is not None:fail('Choose either a corrected balance or an added amount.')
                if p.expected_balance_minor is None or p.expected_balance_minor!=w['balance_minor']:fail('The wallet balance changed. Reload before correcting it.',409)
                change=p.corrected_minor-balance_at(w,before,p.occurred_at)
            else:
                if p.amount_minor is None:fail('Enter a positive amount.',422,'amount_minor')
                change=p.amount_minor
            if not change:fail('The corrected balance is unchanged.',422,'corrected_minor')
            eid=str(uuid.uuid4());c.execute('INSERT INTO wallet_events VALUES (?,?,?,?,?,?,?,?,?,?)',(eid,u,dataset,id,change,p.classification,p.reason,p.source,p.occurred_at,now()))
            guard_balances(c,u,dataset,before,ledger(c,u,dataset),{id},p.occurred_at)
            profile(c,w)
            return receipt(c,u,p.request_key,fp,{'id':eid,'wallet_id':id})
    @r.post('/{id}/{action}')
    def lifecycle(id:str,action:Literal['archive','restore','delete'],p:Lifecycle,dataset=Depends(scope),user=Depends(current_user)):
        with db() as c:
            c.execute('BEGIN IMMEDIATE');u=user['id'];fp,old=replay(c,u,p.request_key,p.model_dump(),'wallet-'+action+':'+dataset+id)
            if old:return old
            w=get(c,u,dataset,id);check(w,p)
            if action=='delete':
                # Goal contribution audit links also prevent deleting a wallet with history.
                used=c.execute('SELECT 1 FROM transactions WHERE wallet_id=? OR destination_wallet_id=? LIMIT 1',(id,id)).fetchone() or c.execute('SELECT 1 FROM wallet_events WHERE wallet_id=? LIMIT 1',(id,)).fetchone() or c.execute('SELECT 1 FROM goal_contributions WHERE wallet_id=? LIMIT 1',(id,)).fetchone()
                if used or w['opening_minor']!=0 or w['balance_minor']!=0:fail('Only a zero-balance wallet with no history can be deleted. Archive it instead.',409)
                c.execute('DELETE FROM wallets WHERE id=?',(id,))
            else:
                archived=1 if action=='archive' else 0
                if w['archived']==archived:fail('This wallet already has that archive state.',409)
                if archived and c.execute("SELECT 1 FROM transactions WHERE (wallet_id=? OR destination_wallet_id=?) AND occurred_at>? UNION ALL SELECT 1 FROM wallet_events WHERE wallet_id=? AND occurred_at>? LIMIT 1",(id,id,datetime.now().isoformat(timespec='seconds'),id,datetime.now().isoformat(timespec='seconds'))).fetchone():fail('Remove or reschedule future entries before archiving this wallet.',409)
                c.execute('INSERT INTO wallet_metadata(wallet_id,kind,archived) VALUES (?,?,?) ON CONFLICT(wallet_id) DO UPDATE SET archived=excluded.archived',(id,w['kind'],archived));profile(c,w)
            return receipt(c,u,p.request_key,fp,{'id':id,'message':'Wallet '+action+' completed.'})
    return r
