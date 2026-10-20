"""Goals are earmarks, never additional assets. Single shared read model with legacy compatibility."""
from datetime import date,datetime
from .ledger import wallets

CATEGORIES=['Emergency Fund','Education','Travel','Electronics','Home','Vehicle','Other']
ICONS=['category','shield','laptop','travel','phone','target']
SELECT='''SELECT g.*,COALESCE(m.category,'Other') category,COALESCE(m.description,'') description,
 COALESCE(m.monthly_minor,0) monthly_minor,COALESCE(m.icon,'category') icon,
 COALESCE(m.state,'active') state,COALESCE(m.archived,0) archived,COALESCE(m.version,1) version,
 COALESCE(m.created_at,'') created_at,COALESCE(m.updated_at,'') updated_at,m.goal_id managed,g.rowid position
 FROM financial_goals g LEFT JOIN goal_metadata m ON m.goal_id=g.id'''

def metrics(target,saved,state='active'):
    return dict(saved_minor=saved,remaining_minor=target-saved,percentage=round(saved*100/target,2) if target else None,
        status='Completed' if target>0 and saved>=target else 'Paused' if state=='paused' else 'In Progress')

def goals(c,u,d,include_archived=False):
    out=[]
    for row in c.execute(SELECT+' WHERE g.user_id=? AND g.dataset=? ORDER BY g.rowid',(u,d)):
        g=dict(row)
        if g['archived'] and not include_archived:continue
        saved=c.execute('SELECT COALESCE(sum(amount_minor),0) FROM goal_contributions WHERE goal_id=?',(g['id'],)).fetchone()[0] if g['managed'] else g['saved_minor']
        g.update(metrics(g['target_minor'],saved,g['state']));g['legacy_unlinked_minor']=c.execute("SELECT COALESCE(sum(amount_minor),0) FROM goal_contributions WHERE goal_id=? AND method='legacy'",(g['id'],)).fetchone()[0] if g['managed'] else saved
        g.pop('managed',None);out.append(g)
    return out

def summary(items):
    active=[g for g in items if not g['archived'] and g['status']=='In Progress']
    target=sum(g['target_minor'] for g in active);saved=sum(g['saved_minor'] for g in active)
    return dict(target_minor=target,saved_minor=saved,remaining_minor=target-saved,percentage=round(saved*100/target,2) if target else None,active_count=len(active))

def funding_wallets(c,u,d,point=None):
    point=point or datetime.now().isoformat(timespec='seconds');out=[]
    for w in wallets(c,u,d,point):
        reserved=c.execute('''SELECT COALESCE(sum(a.amount_minor),0) FROM goal_contributions a
          JOIN goal_metadata m ON m.goal_id=a.goal_id WHERE a.user_id=? AND a.dataset=? AND a.wallet_id=?
          AND m.archived=0 AND a.occurred_at<=?''',(u,d,w['id'],point)).fetchone()[0]
        out.append({k:w[k] for k in ['id','name','version','status','archived','opening_date','balance_minor','currency']}|dict(allocated_minor=reserved,available_minor=max(0,w['balance_minor']-reserved),coverage_shortfall_minor=max(0,reserved-w['balance_minor'])))
    return out
