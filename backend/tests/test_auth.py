import sqlite3
import time
from dataclasses import replace
import pytest
from fastapi.testclient import TestClient
from app.main import Settings, create_app

PASSWORD='Fincept!2026'
HEADERS={'X-Fincept-Request':'1','Origin':'http://localhost:5173'}

def registration(**overrides):
    return dict(full_name='Demo User',email='demo@example.com',password=PASSWORD,confirm_password=PASSWORD,accepted_terms=True,**overrides)

@pytest.fixture
def setup(tmp_path):
    settings=Settings(database_path=str(tmp_path/'auth.sqlite3'))
    with TestClient(create_app(settings)) as client:
        client.headers.update(HEADERS)
        yield client, settings

def test_registration_hash_and_session(setup):
    c,s=setup
    r=c.post('/api/auth/register',json=registration())
    assert r.status_code==201
    assert set(r.json()['user'])=={'id','full_name','email'}
    assert PASSWORD not in r.text and 'token' not in r.text
    cookie=r.headers['set-cookie'].lower()
    assert 'httponly' in cookie and 'samesite=lax' in cookie and 'max-age' not in cookie
    assert c.get('/api/auth/me').status_code==200
    with sqlite3.connect(s.database_path) as db:
        hashed=db.execute('SELECT password_hash FROM users').fetchone()[0]
        token_hash=db.execute('SELECT token_hash FROM sessions').fetchone()[0]
    assert hashed.startswith('$argon2id$') and PASSWORD not in hashed
    assert token_hash != c.cookies['fincept_session']

def test_duplicate_and_email_normalization(setup):
    c,_=setup
    assert c.post('/api/auth/register',json=registration()).status_code==201
    v=registration();v['email']='DEMO@EXAMPLE.COM'
    assert c.post('/api/auth/register',json=v).status_code==409

def test_server_validation_and_no_password_echo(setup):
    c,_=setup
    v=registration();v.update(password='weak',confirm_password='different',accepted_terms=False)
    r=c.post('/api/auth/register',json=v)
    assert r.status_code==422
    assert set(r.json()['field_errors'])=={'password','confirm_password','accepted_terms'}
    v=registration();v.update(email='invalid',password='a'*513)
    r=c.post('/api/auth/register',json=v)
    assert r.status_code==422 and 'a'*513 not in r.text
    assert c.post('/api/auth/register',json={}).status_code==422

def test_login_remember_rotation_and_logout(setup):
    c,s=setup
    c.post('/api/auth/register',json=registration())
    before=c.cookies['fincept_session']
    r=c.post('/api/auth/login',json={'email':'demo@example.com','password':PASSWORD,'remember':True})
    assert r.status_code==200 and 'Max-Age=2592000' in r.headers['set-cookie']
    assert before != c.cookies['fincept_session']
    assert c.get('/api/auth/me').status_code==200
    assert c.post('/api/auth/logout').status_code==204
    assert c.get('/api/auth/me').status_code==401
    with sqlite3.connect(s.database_path) as db:
        assert db.execute('SELECT count(*) FROM sessions').fetchone()[0]==0

def test_wrong_credentials_and_unauthorized(setup):
    c,_=setup
    assert c.get('/api/auth/me').status_code==401
    c.post('/api/auth/register',json=registration())
    wrong=c.post('/api/auth/login',json={'email':'demo@example.com','password':'wrong'})
    absent=c.post('/api/auth/login',json={'email':'nobody@example.com','password':'wrong'})
    assert wrong.status_code==absent.status_code==401
    assert wrong.json()==absent.json()

def test_expired_session(setup):
    c,s=setup
    c.post('/api/auth/register',json=registration())
    with sqlite3.connect(s.database_path) as db:
        db.execute('UPDATE sessions SET expires_at=?',(int(time.time())-1,))
    assert c.get('/api/auth/me').status_code==401

def test_csrf_and_cors(setup):
    c,_=setup
    assert c.post('/api/auth/login',json={},headers={'Origin':'https://evil.example'}).status_code==403
    c.headers.pop('X-Fincept-Request')
    assert c.post('/api/auth/register',json=registration()).status_code==403
    r=c.options('/api/auth/login',headers={'Origin':'https://evil.example','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'X-Fincept-Request'})
    assert 'access-control-allow-origin' not in r.headers

def test_google_and_reset_not_faked(setup):
    c,_=setup
    assert c.get('/api/auth/config').json()=={'google_enabled':False,'password_reset_enabled':False}

def test_rate_limit_persisted(setup):
    c,s=setup
    with sqlite3.connect(s.database_path) as db:
        db.execute('INSERT INTO rate_limits VALUES (?,?,?)',('register:ip:testclient',30,int(time.time())+900))
    r=c.post('/api/auth/register',json=registration())
    assert r.status_code==429 and r.headers['retry-after']=='900'

def test_secure_production_cookie(tmp_path):
    settings=Settings(database_path=str(tmp_path/'secure.sqlite3'),cookie_secure=True,environment='production')
    with TestClient(create_app(settings),base_url='https://testserver') as c:
        c.headers.update(HEADERS)
        r=c.post('/api/auth/register',json=registration())
        assert r.status_code==201
        assert '__Host-fincept_session=' in r.headers['set-cookie'] and 'Secure' in r.headers['set-cookie']
        assert c.get('/api/auth/me').status_code==200

def test_production_insecure_refused(tmp_path):
    with pytest.raises(RuntimeError,match='COOKIE_SECURE'):
        create_app(Settings(database_path=str(tmp_path/'bad.sqlite3'),environment='production',cookie_secure=False))
