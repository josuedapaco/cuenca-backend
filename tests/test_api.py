import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import app, database, attempts

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('DATABASE_PATH',str(tmp_path/'cuenca.sqlite'))
    monkeypatch.setenv('ADMIN_API_KEY','test-admin-secret')
    attempts.clear()
    with TestClient(app) as client: yield client

def payload(**changes):
    return dict(name='Cliente Demo',phone='7185550100',email='demo@example.com',event_date='2099-12-20',guests=30,dishes='Hornado y pollo',notes='Evento de prueba',language='es',consent=True,**changes)

def test_complete_menu_faithful_to_dossier(client):
    result=client.get('/api/menu')
    assert result.status_code==200
    items=[i for c in result.json()['categories'] for i in c['items']]
    assert len(items)==191
    numbered=[i for i in items if i['number'] is not None]
    assert sorted(i['number'] for i in numbered)==list(range(1,142))
    assert len({i['id'] for i in items})==191
    assert next(i for i in items if i['id']=='14')['prices'][0]['amount']==15.5
    assert next(i for i in items if i['id']=='75')['prices']==[]
    assert next(i for i in items if i['id']=='76')['prices']==[]
    assert next(i for i in items if i['id']=='71')['prices']==[{'size':'Small','amount':20.0},{'size':'Large','amount':35.0}]
    assert all(i['name_es'] and i['name_en'] for i in items)

def test_health_and_restaurant(client):
    assert client.get('/api/health').json()['status']=='ok'
    info=client.get('/api/restaurant').json()
    assert info['hours'] is None and info['domain']=='cuencany.com'
    assert info['phones']==['+17188474697','+17188474642']

def test_inquiry_persists_and_private_export_requires_authentication(client):
    result=client.post('/api/catering',json=payload())
    assert result.status_code==201
    ident=result.json()['id']
    with database() as db:
        row=db.execute('SELECT * FROM catering_requests WHERE id=?',(ident,)).fetchone()
        assert row['name']=='Cliente Demo' and row['guests']==30
    assert client.get('/api/admin/catering').status_code==401
    assert client.get('/api/admin/catering',headers={'Authorization':'Bearer wrong'}).status_code==401
    exported=client.get('/api/admin/catering',headers={'Authorization':'Bearer test-admin-secret'})
    assert exported.json()['requests'][0]['id']==ident

@pytest.mark.parametrize('field,value',[('name',' '),('phone','abcdefg'),('email','bad@'),('event_date','2000-01-01'),('guests',0),('guests',2.5),('consent',False),('dishes',''),('language','fr')])
def test_invalid_inquiries_rejected(client,field,value):
    data=payload();data[field]=value
    assert client.post('/api/catering',json=data).status_code in (400,422)
    with database() as db:assert db.execute('SELECT count(*) FROM catering_requests').fetchone()[0]==0

def test_rate_limit_and_origin(client):
    assert client.post('/api/catering',json=payload(),headers={'Origin':'https://example.com'}).status_code==403
    for _ in range(5):assert client.post('/api/catering',json=payload()).status_code==201
    assert client.post('/api/catering',json=payload()).status_code==429

def test_frontend_fallback_catalog_matches_backend(client):
    path=Path(__file__).parents[2]/'frontend/public/menu.json'
    if path.exists():assert json.loads(path.read_text())==client.get('/api/menu').json()
