"""BROWSER TEST ONLY. Scripted native provider, real auth/DB/approval writes.
Not imported by production. Refuses any database except this isolated test-results path.
"""
import json
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'backend'))
from app.main import Settings,create_app
from app.assistant.provider import ProviderTurn
from app.finance.budget_service import month_range
from datetime import date
import uvicorn

class BrowserNativeDouble:
    configured=True;name='browser-test-double';model='scripted-not-live-ai'
    async def generate_tools(self,messages,tools):
        question=next(m['content'] for m in reversed(messages) if m['role']=='user')
        if question=='E2E advice':return ProviderTurn('Test-only advice response. No financial changes requested.',[])
        if messages[-1]['role']!='tool':return ProviderTurn('',[dict(id='options',type='function',function=dict(name='get_financial_options',arguments='{}'))])
        options=json.loads(messages[-1]['content']);a,z=month_range()
        operations=[dict(operation='budget.create',data=dict(name='Reviewed Food Budget',category='Food',limit_minor=800000,start_date=a,end_date=z))]
        if question=='E2E combined plan':
            if not options.get('wallets'):return ProviderTurn('Which wallet should fund the expense? Create a wallet first.',[])
            operations.extend([dict(operation='goal.create',data=dict(name='Reviewed Laptop Goal',category='Electronics',target_minor=6000000,target_date=date.today().replace(year=date.today().year+1).isoformat())),dict(operation='transaction.create',data=dict(kind='expense',amount_minor=50000,category='Food',wallet_id=options['wallets'][0]['id'],occurred_on=date.today().isoformat(),title='Reviewed Groceries'))])
        return ProviderTurn('',[dict(id='proposal',type='function',function=dict(name='propose_changes',arguments=json.dumps(dict(operations=operations,expected_budget_total_minor=800000))))])

if __name__=='__main__':
    path=Path(os.environ['DATABASE_PATH']).resolve()
    assert path==Path(__file__).resolve().parents[2]/'test-results'/'agent-e2e.sqlite3','TEST ONLY: refusing a non-test database'
    uvicorn.run(create_app(Settings(),assistant_provider=BrowserNativeDouble()),host='127.0.0.1',port=8091)
