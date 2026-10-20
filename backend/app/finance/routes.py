from datetime import date
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from .service import dashboard, period_range, recent
from .demo import seed_demo

Period=Literal['this_week','this_month','last_month','this_year','custom']
Dataset=Literal['live','demo']
Grouping=Literal['weekly','monthly','yearly']

def overview_router(db,current_user,environment):
    router=APIRouter(prefix='/api/overview',tags=['Overview'])
    def check(dataset):
        if dataset=='demo' and environment=='production':raise HTTPException(403,'Sample workspaces are disabled in production.')
    @router.post('/demo',status_code=201)
    def enable_demo(user=Depends(current_user)):
        check('demo')
        with db() as conn:seed_demo(conn,user['id'])
        return {'dataset':'demo','message':'Sample workspace ready. Your live records were not changed.'}
    @router.get('/summary')
    def summary(period:Period='this_month',dataset:Dataset='live',grouping:Grouping='monthly',start:date|None=None,end:date|None=None,user=Depends(current_user)):
        check(dataset)
        with db() as conn:
            result=dashboard(conn,user['id'],dataset,period,start,end,grouping)
            result.pop('insight')
            return result
    @router.get('/insights')
    def insights(period:Period='this_month',dataset:Dataset='live',start:date|None=None,end:date|None=None,user=Depends(current_user)):
        check(dataset)
        with db() as conn:result=dashboard(conn,user['id'],dataset,period,start,end,'monthly')
        return {'insight':result['insight'],'method':'deterministic_rules','dataset':dataset}
    @router.get('/recent-transactions')
    def transactions(period:Period='this_month',dataset:Dataset='live',start:date|None=None,end:date|None=None,search:str=Query('',max_length=100),category:str=Query('',max_length=80),kind:Literal['','income','expense','transfer']='',page:int=Query(1,ge=1,le=10000),limit:int=Query(6,ge=1,le=25),user=Depends(current_user)):
        check(dataset);first,last,_,_=period_range(period,start,end)
        with db() as conn:return recent(conn,user['id'],dataset,first,last,search,category,kind,page,limit)
    return router
