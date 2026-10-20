"""Settings tests use real authentication and isolated SQLite, not mocked persistence."""
import csv
import io
import json
import sqlite3
import zipfile
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.main import Settings, create_app
PASSWORD='Fincept!2026'
H={'X-Fincept-Request':'1','Origin':'http://localhost:5173'}
def register(c):
    r=c.post('/api/auth/register',json={'full_name':'Settings User','email':str(uuid4())+'@example.com','password':PASSWORD,'confirm_password':PASSWORD,'accepted_terms':True})
    assert r.status_code==201,r.text
    return r.json()['user']
@pytest.fixture
def env(tmp_path):
    path=str(tmp_path/'settings.sqlite3');app=create_app(Settings(database_path=path))
    with TestClient(app,headers=H) as c:yield c,path,app

def wallet(c,name='Main wallet'):
    r=c.post('/api/transactions/wallets',json={'request_key':str(uuid4()),'name':name,'kind':'bank','opening_minor':500000,'opening_date':'2026-01-01'})
    assert r.status_code==201,r.text
    return r.json()
def prefs(c):
    r=c.get('/api/settings').json();return r['preferences']|{'version':r['version']}

def test_auth_defaults_and_migration(env):
    c,path,_=env
    for method,url,body in [('GET','',None),('GET','/security',None),('GET','/export',None),('PATCH','/profile',{'full_name':'No auth'}),('PATCH','/preferences',{}),('POST','/password',{}),('POST','/sessions/revoke-others',{}),('POST','/demo/clear',{'confirmation':'CLEAR DEMO DATA'})]:
        assert c.request(method,'/api/settings'+url,json=body).status_code==401
    register(c);r=c.get('/api/settings').json()
    assert r['version']==0 and r['currency']=='BDT' and not r['notification_delivery']
    assert r['preferences']['financial']=={'number_grouping':True,'decimal_style':'flexible'}
    assert set(r['preferences']['notifications'].values())=={False}
    assert not r['capabilities']['restore'] and not r['capabilities']['delete_account']
    assert all(i['status'] in ('unavailable','not_configured') for i in r['integrations'])
    with sqlite3.connect(path) as db:assert db.execute('PRAGMA user_version').fetchone()[0]==12

def test_profile_validation_persistence_ownership(env):
    c,_,_=env;owner=register(c)
    r=c.patch('/api/settings/profile',json={'full_name':'  Updated   Person  '})
    assert r.status_code==200 and r.json()['user']['full_name']=='Updated Person'
    for name in ('x',' '*8,'a'*101):assert c.patch('/api/settings/profile',json={'full_name':name}).status_code==422
    assert c.patch('/api/settings/profile',json={'full_name':'New Name','email':'changed@example.com'}).status_code==422
    register(c)
    assert c.patch('/api/settings/profile',json={'full_name':'Attacker','user_id':owner['id']}).status_code==422
    c.patch('/api/settings/profile',json={'full_name':'Other Name'})
    c.post('/api/auth/login',json={'email':owner['email'],'password':PASSWORD})
    assert c.get('/api/auth/me').json()['user']['full_name']=='Updated Person'

def test_preferences_persistence_conflicts_and_strict_validation(env):
    c,path,_=env;owner=register(c);original=prefs(c);changed=json.loads(json.dumps(original))
    changed['notifications']['budget_alerts']=True;changed['financial']={'number_grouping':False,'decimal_style':'fixed'}
    assert c.patch('/api/settings/preferences',json=changed).status_code==200
    assert prefs(c)==changed|{'version':1}
    assert c.patch('/api/settings/preferences',json=original).status_code==409
    invalid=prefs(c);invalid['notifications']['budget_alerts']='yes'
    assert c.patch('/api/settings/preferences',json=invalid).status_code==422
    invalid=prefs(c);invalid['financial']['decimal_style']='converted'
    assert c.patch('/api/settings/preferences',json=invalid).status_code==422
    assert c.patch('/api/settings/preferences',json=prefs(c)|{'user_id':owner['id']}).status_code==422
    register(c);assert prefs(c)==original
    with TestClient(create_app(Settings(database_path=path)),headers=H) as other:
        other.post('/api/auth/login',json={'email':owner['email'],'password':PASSWORD})
        assert prefs(other)['financial']==changed['financial']
    with sqlite3.connect(path) as db:assert db.execute('PRAGMA foreign_key_check').fetchall()==[]

def test_csrf_and_sensitive_validation_redaction(env):
    c,_,_=env;register(c)
    assert c.patch('/api/settings/profile',json={'full_name':'Forbidden'},headers={'Origin':'https://evil.example'}).status_code==403
    c.headers.pop('X-Fincept-Request')
    assert c.patch('/api/settings/preferences',json=prefs(c)).status_code==403
    c.headers.update(H);secret='PRIVATE-VALUE-'*60
    r=c.post('/api/settings/password',json={'current_password':secret,'new_password':secret,'confirm_password':secret})
    assert r.status_code==422 and secret not in r.text

def test_password_change_rotates_and_revokes_other_sessions(env):
    c,path,app=env;owner=register(c)
    with TestClient(app,headers=H) as other:
        other.post('/api/auth/login',json={'email':owner['email'],'password':PASSWORD})
        r=c.get('/api/settings/security');assert r.json()['active_sessions']==2
        assert 'token' not in r.text and 'password' not in r.text
        old=c.cookies['fincept_session'];new='Updated!2026'
        assert c.post('/api/settings/password',json={'current_password':'wrong','new_password':new,'confirm_password':new}).status_code==422
        assert other.get('/api/auth/me').status_code==200
        assert c.post('/api/settings/password',json={'current_password':PASSWORD,'new_password':new,'confirm_password':'Mismatch!2'}).status_code==422
        r=c.post('/api/settings/password',json={'current_password':PASSWORD,'new_password':new,'confirm_password':new})
        assert r.status_code==200,r.text
        assert c.cookies['fincept_session']!=old and c.get('/api/auth/me').status_code==200
        assert other.get('/api/auth/me').status_code==401
        assert c.post('/api/auth/login',json={'email':owner['email'],'password':PASSWORD}).status_code==401
        assert c.post('/api/auth/login',json={'email':owner['email'],'password':new}).status_code==200
        with sqlite3.connect(path) as db:assert new not in db.execute('SELECT password_hash FROM users').fetchone()[0]

def test_revoke_others_requires_password_and_preserves_current(env):
    c,_,app=env;owner=register(c)
    with TestClient(app,headers=H) as other:
        other.post('/api/auth/login',json={'email':owner['email'],'password':PASSWORD})
        assert c.post('/api/settings/sessions/revoke-others',json={'current_password':'bad'}).status_code==422
        assert c.post('/api/settings/sessions/revoke-others',json={'current_password':PASSWORD}).json()=={'revoked':1}
        assert other.get('/api/auth/me').status_code==401 and c.get('/api/auth/me').status_code==200
        assert c.post('/api/settings/sessions/revoke-others',json={'current_password':PASSWORD}).json()=={'revoked':0}

def test_exports_real_scoped_safe_no_secrets_or_mutations(env):
    c,path,_=env;owner=register(c);w=wallet(c,'=HYPERLINK("evil","x"),\nquoted')
    r=c.post('/api/transactions',json={'request_key':str(uuid4()),'kind':'expense','amount_minor':1234,'wallet_id':w['id'],'title':'=1+1','category':'Food','occurred_at':'2026-01-02T10:00:00'})
    assert r.status_code==201,r.text
    c.post('/api/overview/demo');r=c.get('/api/settings/export?format=csv')
    assert r.status_code==200 and 'attachment;' in r.headers['content-disposition']
    z=zipfile.ZipFile(io.BytesIO(r.content))
    assert {'wallets.csv','transactions.csv','debt_records.csv','manifest.json'}<=set(z.namelist())
    assert not any(n in z.namelist() for n in ('users.csv','sessions.csv','financial_requests.csv'))
    rows=list(csv.DictReader(io.StringIO(z.read('transactions.csv').decode('utf-8-sig'))))
    assert len(rows)==1 and rows[0]['amount_minor']=='1234' and rows[0]['title']=="'=1+1"
    rows=list(csv.DictReader(io.StringIO(z.read('wallets.csv').decode('utf-8-sig'))))
    assert len(rows)==1 and rows[0]['name'].startswith("'") and '\n' in rows[0]['name']
    manifest=json.loads(z.read('manifest.json'));assert manifest['dataset']=='live' and manifest['restorable'] is False
    snapshot=c.get('/api/settings/export?format=json&scope=transactions').json()
    assert set(snapshot['data'])=={'transactions','transaction_metadata'}
    assert snapshot['data']['transactions'][0]['amount_minor']==1234
    assert snapshot['data']['transactions'][0]['title']=='=1+1'
    assert 'password_hash' not in json.dumps(snapshot) and 'token_hash' not in json.dumps(snapshot)
    register(c);other=c.get('/api/settings/export?format=json').json()
    assert all(rows==[] for rows in other['data'].values()) and owner['id'] not in json.dumps(other)
    assert c.get('/api/settings/export?scope=users').status_code==422
    assert c.get('/api/settings/export?format=sqlite').status_code==422
    with sqlite3.connect(path) as db:assert db.execute('SELECT amount_minor FROM transactions WHERE dataset="live"').fetchone()[0]==1234

def test_empty_csv_has_headers(env):
    c,_,_=env;register(c)
    z=zipfile.ZipFile(io.BytesIO(c.get('/api/settings/export?scope=transactions').content))
    text=z.read('transactions.csv').decode('utf-8-sig');assert 'amount_minor' in text and len(text.splitlines())==1

def test_clear_demo_confirmation_and_owner_dataset_isolation(env):
    c,path,_=env;owner=register(c);wallet(c,'Real live wallet');c.post('/api/overview/demo')
    with sqlite3.connect(path) as db:before=db.execute('SELECT count(*) FROM transactions WHERE user_id=? AND dataset="demo"',(owner['id'],)).fetchone()[0]
    assert before>0
    assert c.post('/api/settings/demo/clear',json={'confirmation':'clear'}).status_code==422
    other=register(c);c.post('/api/overview/demo');c.post('/api/auth/login',json={'email':owner['email'],'password':PASSWORD})
    r=c.post('/api/settings/demo/clear',json={'confirmation':'CLEAR DEMO DATA'})
    assert r.status_code==200,r.text
    assert r.json()['deleted']['transactions']==before
    assert c.post('/api/settings/demo/clear',json={'confirmation':'CLEAR DEMO DATA'}).json()['deleted']['transactions']==0
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT count(*) FROM wallets WHERE user_id=? AND dataset="live"',(owner['id'],)).fetchone()[0]==1
        assert db.execute('SELECT count(*) FROM transactions WHERE user_id=? AND dataset="demo"',(other['id'],)).fetchone()[0]>0
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]

def test_clear_demo_transaction_rolls_back_on_failure(env):
    c,path,app=env;owner=register(c);c.post('/api/overview/demo')
    with sqlite3.connect(path) as db:
        db.execute("CREATE TRIGGER fail_clear BEFORE DELETE ON wallets BEGIN SELECT RAISE(ABORT,'test failure'); END")
        before=db.execute('SELECT count(*) FROM transactions').fetchone()[0]
    with TestClient(app,headers=H,raise_server_exceptions=False) as other:
        other.post('/api/auth/login',json={'email':owner['email'],'password':PASSWORD})
        assert other.post('/api/settings/demo/clear',json={'confirmation':'CLEAR DEMO DATA'}).status_code==500
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT count(*) FROM transactions').fetchone()[0]==before
        assert db.execute('PRAGMA foreign_key_check').fetchall()==[]

def test_unsupported_restore_delete_and_production_demo(tmp_path):
    with TestClient(create_app(Settings(database_path=str(tmp_path/'production.sqlite3'),cookie_secure=True,environment='production')),base_url='https://testserver',headers=H) as c:
        register(c);assert c.get('/api/settings').json()['capabilities']['clear_demo'] is False
        assert c.post('/api/settings/demo/clear',json={'confirmation':'CLEAR DEMO DATA'}).status_code==403
        assert c.get('/api/settings/export?dataset=demo').status_code==403
        for body in ({},{'format':'unsupported','data':'malformed'}):assert c.post('/api/settings/restore',json=body).status_code==404
        assert c.delete('/api/settings/account').status_code==404 and c.get('/api/auth/me').status_code==200

def test_pending_sample_ai_request_prevents_partial_clear(env):
    c,path,_=env;owner=register(c);c.post('/api/overview/demo')
    with sqlite3.connect(path) as db:
        db.execute('INSERT INTO assistant_conversations VALUES (?,?,?,?,?,?)',('conversation',owner['id'],'demo','Sample','2026-10-20','2026-10-20'))
        db.execute('INSERT INTO assistant_requests VALUES (?,?,?,?,?,?,?,?,?,?)',('request','conversation',owner['id'],'demo','Question','pending','attempt',None,'2026-10-20','2026-10-20'))
        before=db.execute('SELECT count(*) FROM transactions').fetchone()[0]
    assert c.post('/api/settings/demo/clear',json={'confirmation':'CLEAR DEMO DATA'}).status_code==409
    with sqlite3.connect(path) as db:assert db.execute('SELECT count(*) FROM transactions').fetchone()[0]==before


def test_export_cannot_select_another_user_via_query(env):
    c,_,_=env;owner=register(c);wallet(c);register(c)
    export=c.get('/api/settings/export?format=json&user_id='+owner['id']).json()
    assert all(rows==[] for rows in export['data'].values())
