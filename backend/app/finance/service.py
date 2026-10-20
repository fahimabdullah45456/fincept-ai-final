"""Read-side accounting. Integer minor units in storage; no dashboard-only ledger."""
from collections import defaultdict
from datetime import date, timedelta
import calendar
from fastapi import HTTPException

def month_shift(day, offset):
    year, month = divmod(day.year*12+day.month-1+offset,12)
    return date(year,month+1,min(day.day,calendar.monthrange(year,month+1)[1]))

def period_range(period, start=None, end=None, today=None):
    today=today or date.today()
    if period=='this_week':
        first=today-timedelta(days=today.weekday());last=first+timedelta(days=6);previous=(first-timedelta(days=7),first-timedelta(days=1))
    elif period in ('this_month','last_month'):
        first=today.replace(day=1)
        if period=='last_month':first=month_shift(first,-1)
        last=month_shift(first,1)-timedelta(days=1);p=month_shift(first,-1);previous=(p,first-timedelta(days=1))
    elif period=='last_3_months':
        # Rolling three calendar months including the current month (Insights).
        current=today.replace(day=1);first=month_shift(current,-2);last=month_shift(current,1)-timedelta(days=1);previous=(month_shift(first,-3),first-timedelta(days=1))
    elif period=='this_year':
        first=date(today.year,1,1);last=date(today.year,12,31);previous=(date(today.year-1,1,1),date(today.year-1,12,31))
    elif period=='custom' and start and end:
        first,last=start,end
        if last<first or (last-first).days>731:raise HTTPException(422,'Choose a date range of at most 732 days, with the end on or after the start.')
        previous=(first-(last-first)-timedelta(days=1),first-timedelta(days=1))
    else:raise HTTPException(422,'Choose a valid reporting period and provide both custom dates when needed.')
    if first.year<1901 or last.year>2100:raise HTTPException(422,'Reporting dates must fall between 1901 and 2100.')
    return first,last,*previous

def money(value):return round(value/100,2)
def between(row,first,last):return first.isoformat()<=row['occurred_at'][:10]<=last.isoformat()
def totals(rows):
    income=sum(r['amount_minor'] for r in rows if r['kind']=='income');expense=sum(r['amount_minor'] for r in rows if r['kind']=='expense')
    return {'income':money(income),'expenses':money(expense),'net':money(income-expense),'savings_rate':round((income-expense)/income*100,1) if income else None}

def ledger_balance(conn,user,dataset,as_of):
    from .ledger import wallets
    rows=[w for w in wallets(conn,user,dataset,as_of.isoformat()+'T23:59:59') if not w['archived'] and w['status']=='active' and w['opening_date']<=as_of.isoformat()]
    return money(sum(w['balance_minor'] for w in rows)),len(rows)

def dashboard(conn,user,dataset,period,start,end,grouping,today=None):
    first,last,pfirst,plast=period_range(period,start,end,today)
    history_start=month_shift(last.replace(day=1),-5) if grouping=='monthly' else last-timedelta(days=last.weekday()+35) if grouping=='weekly' else date(last.year-5,1,1)
    query_start=min(first,pfirst,history_start)
    rows=conn.execute('SELECT * FROM transactions WHERE user_id=? AND dataset=? AND substr(occurred_at,1,10)>=? AND substr(occurred_at,1,10)<=?',(user,dataset,query_start.isoformat(),last.isoformat())).fetchall()
    current=[r for r in rows if between(r,first,last)];previous=totals([r for r in rows if between(r,pfirst,plast)]);summary=totals(current)
    balance,count=ledger_balance(conn,user,dataset,last);beginning,_=ledger_balance(conn,user,dataset,first-timedelta(days=1))
    def change(key):return round((summary[key]-previous[key])/abs(previous[key])*100,1) if previous[key] else None
    summary.update(available_balance=balance,wallet_count=count,balance_change=round(balance-beginning,2),previous=previous,income_change=change('income'),expense_change=change('expenses'),savings_change=round(summary['savings_rate']-previous['savings_rate'],1) if summary['savings_rate'] is not None and previous['savings_rate'] is not None else None)
    cat=defaultdict(int)
    for r in current:
        if r['kind']=='expense':cat[r['category'] or 'Other']+=r['amount_minor']
    categories=[{'name':name,'amount':money(amount),'percentage':round(money(amount)/summary['expenses']*100,1) if summary['expenses'] else 0} for name,amount in sorted(cat.items(),key=lambda p:-p[1])]
    buckets=[]
    for i in range(6):
        if grouping=='monthly':a=month_shift(history_start,i);b=month_shift(a,1)-timedelta(days=1);label=a.strftime('%b');full=a.strftime('%B %Y')
        elif grouping=='weekly':a=history_start+timedelta(days=i*7);b=a+timedelta(days=6);label=a.strftime('%d %b');full=f'{a.isoformat()} – {b.isoformat()}'
        else:a=date(history_start.year+i,1,1);b=date(a.year,12,31);label=str(a.year);full=label
        bucket_rows=[r for r in rows if between(r,a,min(b,last))];buckets.append({'label':label,'full_label':full,'start':a.isoformat(),'end':min(b,last).isoformat(),'selected':a<=last<=b,**totals(bucket_rows)})
    from .budget_service import evaluate
    budget_data=evaluate(conn,user,dataset,first.isoformat(),last.isoformat())
    statuses={'Exceeded':'Over budget','Near Limit':'Near limit','On Track':'On track'}
    budgets=[{'id':b['id'],'name':b['name'],'category':b['category'],'spent':money(b['spent_minor']),'limit':money(b['limit_minor']),'remaining':money(b['remaining_minor']),'percentage':round(b['percentage'],1) if b['percentage'] is not None else None,'status':statuses[b['status']]} for b in budget_data['items'][:4]]
    from .goal_service import goals as goal_records
    goals=[{'id':g['id'],'name':g['name'],'saved':money(g['saved_minor']),'target':money(g['target_minor']),'remaining':money(g['remaining_minor']),'target_date':g['target_date'],'percentage':round(g['percentage'],1) if g['percentage'] is not None else None} for g in goal_records(conn,user,dataset) if g['status']=='In Progress'][:3]
    # A rule-based observation, not an LLM response. Monetary values stay structured for privacy rendering.
    over=next((b for b in budgets if b['remaining']<0),None)
    near=next((b for b in budgets if b['status']=='Near limit'),None)
    insight={'kind':'budget_over' if over else 'budget_near','budget':over or near} if over or near else {'kind':'negative_cash_flow','net':summary['net']} if summary['net']<0 else None
    return {'dataset':dataset,'reporting_period':{'start':first.isoformat(),'end':last.isoformat(),'previous_start':pfirst.isoformat(),'previous_end':plast.isoformat(),'label':first.strftime('%B %Y') if period in ('this_month','last_month') else f'{first.isoformat()} – {last.isoformat()}','days_left':max(0,(last-(today or date.today())).days)},'summary':summary,'categories':categories,'cash_flow':{'grouping':grouping,'history_start':history_start.isoformat(),'history_end':last.isoformat(),'buckets':buckets},'budgets':budgets,'goals':goals,'insight':insight}

def recent(conn,user,dataset,first,last,search='',category='',kind='',page=1,limit=6):
    clauses=['user_id=?','dataset=?','substr(occurred_at,1,10)>=?','substr(occurred_at,1,10)<=?'];args=[user,dataset,first.isoformat(),last.isoformat()]
    if search:
        # Literal substring matching, not LIKE wildcards or SQL interpolation.
        clauses.append('(instr(lower(title),lower(?))>0 OR instr(lower(description),lower(?))>0)');args.extend([search,search])
    if category:clauses.append("COALESCE(category,'Other')=?");args.append(category)
    if kind:clauses.append('kind=?');args.append(kind)
    where=' AND '.join(clauses);count=conn.execute('SELECT COUNT(*) FROM transactions WHERE '+where,args).fetchone()[0]
    records=conn.execute('SELECT id,title,description,category,kind,amount_minor,occurred_at FROM transactions WHERE '+where+' ORDER BY occurred_at DESC,id DESC LIMIT ? OFFSET ?',(*args,limit,(page-1)*limit)).fetchall()
    return {'items':[{'id':r['id'],'title':r['title'],'description':r['description'],'category':r['category'] or ('Transfer' if r['kind']=='transfer' else 'Other'),'kind':r['kind'],'amount':money(r['amount_minor']),'date':r['occurred_at']} for r in records],'total':count,'page':page,'limit':limit}
