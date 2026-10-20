"""Single integer-minor-unit balance timeline for Overview, Wallets and transaction guards."""
from datetime import datetime

def ledger(c,u,d):
    rows=[dict(r) for r in c.execute('SELECT * FROM transactions WHERE user_id=? AND dataset=?',(u,d))]
    rows += [dict(r)|{'kind':r['classification'],'destination_wallet_id':None} for r in c.execute('SELECT * FROM wallet_events WHERE user_id=? AND dataset=?',(u,d))]
    return rows

def delta(r,wallet_id):
    if r['wallet_id']==wallet_id:
        return r['delta_minor'] if 'delta_minor' in r else r['amount_minor'] if r['kind']=='income' else -r['amount_minor']
    return r.get('amount_minor',0) if r.get('destination_wallet_id')==wallet_id else 0

def balance_at(w,rows,point):
    if w['opening_date']>point[:10]:return 0
    return w['opening_minor']+sum(delta(r,w['id']) for r in rows if w['opening_date']<=r['occurred_at'][:10] and r['occurred_at']<=point)

def wallets(c,u,d,point=None):
    rows=ledger(c,u,d);point=point or datetime.now().isoformat(timespec='seconds')
    sql="""SELECT w.*,COALESCE(m.kind,CASE WHEN lower(w.name) LIKE '%cash%' THEN 'cash' ELSE 'bank' END) kind,
    COALESCE(m.currency,'BDT') currency,COALESCE(m.archived,0) archived,
    COALESCE(p.provider,'') provider,COALESCE(p.identifier_last4,'') identifier_last4,COALESCE(p.notes,'') notes,
    COALESCE(p.status,'active') status,COALESCE(p.version,1) version,
    COALESCE(p.created_at,w.opening_date) created_at,COALESCE(p.updated_at,w.opening_date) updated_at,w.rowid position
    FROM wallets w LEFT JOIN wallet_metadata m ON m.wallet_id=w.id LEFT JOIN wallet_profiles p ON p.wallet_id=w.id
    WHERE w.user_id=? AND w.dataset=? ORDER BY w.rowid"""
    return [dict(r)|{'balance_minor':balance_at(r,rows,point)} for r in c.execute(sql,(u,d))]
