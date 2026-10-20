"""Single read model for Budgets and Overview. All accounting uses integer minor units."""
from datetime import date
import calendar

SELECT = '''SELECT b.*,COALESCE(m.reset_period,'custom') reset_period,
 CASE WHEN m.budget_id IS NULL THEN 75 ELSE m.alert_threshold END alert_threshold,
 COALESCE(m.notes,'') notes,COALESCE(m.version,1) version
 FROM budgets b LEFT JOIN budget_metadata m ON m.budget_id=b.id'''

def metrics(limit, spent, threshold=75):
    percentage=round(spent*100/limit,2) if limit else None
    status='Exceeded' if spent>limit else 'Near Limit' if limit and spent*100>=limit*85 else 'On Track'
    risk=spent>limit or (threshold is not None and limit>0 and spent*100>=limit*threshold)
    return dict(spent_minor=spent,remaining_minor=limit-spent,percentage=percentage,status=status,at_risk=bool(risk))

def month_range(month=None):
    try:
        first=date.fromisoformat((month or date.today().strftime('%Y-%m'))+'-01')
        if not 1901<=first.year<=2100:raise ValueError()
    except (ValueError,TypeError):raise ValueError('Choose a month between 1901 and 2100.')
    return first.isoformat(),date(first.year,first.month,calendar.monthrange(first.year,first.month)[1]).isoformat()

def evaluate(c,user,dataset,first,last):
    budgets=[dict(r) for r in c.execute(SELECT+' WHERE b.user_id=? AND b.dataset=? AND b.start_date<=? AND b.end_date>=? ORDER BY b.rowid',(user,dataset,last,first))]
    expenses=[dict(r) for r in c.execute("SELECT * FROM transactions WHERE user_id=? AND dataset=? AND kind='expense' AND category IS NOT NULL AND substr(occurred_at,1,10) BETWEEN ? AND ? ORDER BY occurred_at DESC,id",(user,dataset,first,last))]
    activity={b['id']:[] for b in budgets};ambiguous=set();conflicts=set()
    for t in expenses:
        matches=[b for b in budgets if b['category']==t['category'] and b['start_date']<=t['occurred_at'][:10]<=b['end_date']]
        if len(matches)==1:activity[matches[0]['id']].append(t)
        elif len(matches)>1:
            ambiguous.add(t['id']);conflicts.update(b['id'] for b in matches)
    for b in budgets:
        b.update(metrics(b['limit_minor'],sum(t['amount_minor'] for t in activity[b['id']]),b['alert_threshold']))
        b['conflicted']=b['id'] in conflicts
    total=sum(b['limit_minor'] for b in budgets);spent=sum(b['spent_minor'] for b in budgets)
    return dict(items=budgets,summary=dict(limit_minor=total,**metrics(total,spent),risk_count=sum(b['at_risk'] for b in budgets)),activity=activity,ambiguous_count=len(ambiguous))
