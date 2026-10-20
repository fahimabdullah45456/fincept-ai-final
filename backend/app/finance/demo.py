"""Explicit development-only sample workspace. Never writes live records."""
from datetime import date
import calendar
from .service import month_shift

def seed_demo(conn,user):
    today=date.today();first=today.replace(day=1);last=month_shift(first,1).fromordinal(month_shift(first,1).toordinal()-1)
    existing=conn.execute("SELECT 1 FROM financial_workspaces WHERE user_id=? AND dataset='demo'",(user,)).fetchone()
    if existing:return
    conn.execute("INSERT INTO financial_workspaces VALUES (?,'demo')",(user,))
    prefix=user+':demo:'
    def wid(name):return prefix+name
    def add(key,kind,amount,title,category,day,month=first,dest=None,wallet='bank',linked=None):
        dt=month.replace(day=min(day,calendar.monthrange(month.year,month.month)[1])).isoformat()+'T17:48:00'
        conn.execute('INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(prefix+key,user,'demo',wid(wallet),wid(dest) if dest else None,kind,round(amount*100),title,'Illustrative sample record',category,dt,prefix+linked if linked else None))
    history=[(42000,31000),(45000,34000),(41000,29000),(48000,36000),(46000,33000)]
    # Opening position reconciles the full six-month sample ledger to the illustrative closing balance.
    net=sum(i-e for i,e in history)+13800;opening=61350-net
    for name,balance in [('bank',opening-8000),('cash',0),('savings',8000)]:
        conn.execute('INSERT INTO wallets VALUES (?,?,?,?,?,?)',(wid(name),user,'demo',name.title()+' Wallet',round(balance*100),month_shift(first,-5).isoformat()))
    for i,(income,expense) in enumerate(history):
        month=month_shift(first,i-5);add('history-i'+str(i),'income',income,'Monthly income','Income',1,month);add('history-e'+str(i),'expense',expense,'Monthly expenses','Other',15,month)
    # 48 current-month records: 6 incomes, 38 expenses and 4 transfers.
    for i,(amount,title,day) in enumerate([(40000,'Monthly salary',1),(6000,'Freelance project',12),(2000,'Consulting',2),(2000,'Client payment',2),(1000,'Project bonus',3),(1000,'Other income',3)]):add('i'+str(i),'income',amount,title,'Income',day)
    for i,(amount,title,cat,day) in enumerate([(280,'Uber ride','Transport',16),(420,'Lunch with friends','Food',16),(1850,'Online shopping order','Shopping',14),(800,'Netflix subscription','Entertainment',10),(12000,'Room rent','Housing',5)]):add('e'+str(i),'expense',amount,title,cat,day)
    # Remaining expenses are early-month records so the recent-six composition matches the design.
    remaining=[('Food',7980,8),('Transport',5320,8),('Shopping',3050,6),('Entertainment',2400,5),('Other',4090,5)]
    for category,amount,count in remaining:
        minor=round(amount*100);part=minor//count
        for i in range(count):add(category+str(i),'expense',(part+(minor-part*count if i==0 else 0))/100,category+' purchase',category,1+i%4)
    for i in range(4):add('transfer'+str(i),'transfer',1250,'Transfer to savings','Transfer',2,dest='savings')
    add('fee','expense',10,'Transfer fee','Other',2,linked='transfer3')
    for category,limit in [('Food',10000),('Transport',6000),('Shopping',4500),('Entertainment',5000)]:
        conn.execute('INSERT INTO budgets VALUES (?,?,?,?,?,?,?,?)',(prefix+'budget'+category,user,'demo',category,category,limit*100,first.isoformat(),last.isoformat()))
    for name,saved,target,offset in [('Emergency fund',12000,30000,2),('Laptop purchase',38000,65000,5),('Tuition',20000,25000,1)]:
        conn.execute('INSERT INTO financial_goals VALUES (?,?,?,?,?,?,?)',(prefix+'goal'+name,user,'demo',name,saved*100,target*100,month_shift(first,offset).isoformat()))
