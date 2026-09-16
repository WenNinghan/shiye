import io
from datetime import timedelta

import pymupdf as fitz
from fastapi.testclient import TestClient
from PIL import Image

from shiye.models import Block
from shiye.store import now


def uploaded(client, png):
    response=client.post("/api/documents", files={"files":("sample.png",png,"image/png")})
    assert response.status_code==201, response.text
    return response.json()


def test_session_cookie_and_health(client):
    assert "shiye_session" in client.cookies
    assert client.get("/api/health").json()["cloud_calls"] is False
    assert client.get("/api/session").headers["cache-control"]=="no-store"


def test_upload_owner_isolation_and_delete(app,client,png):
    doc=uploaded(client,png)
    path=f'/api/documents/{doc["id"]}'
    with TestClient(app) as other:
        assert other.get(path).status_code==401
        other.get('/api/session')
        assert other.get(path).status_code==404
        assert other.delete(path).status_code==404
    assert client.get(path).status_code==200
    folder=app.state.store.folder(doc['id'])
    assert folder.exists()
    assert client.delete(path).status_code==204
    assert not folder.exists()
    assert client.get(path).status_code==404


def test_stale_version_does_not_overwrite(client,png):
    doc=uploaded(client,png)
    path=f'/api/documents/{doc["id"]}'
    body={'version':doc['version'],'title':'新的名字','pages':doc['pages']}
    assert client.put(path,json=body).status_code==200
    body['title']='旧请求'
    assert client.put(path,json=body).status_code==409
    assert client.get(path).json()['title']=='新的名字'


def test_queue_cancel_and_retry(client,png):
    doc=uploaded(client,png)
    path=f'/api/documents/{doc["id"]}'
    started=client.post(path+'/start',json={'version':doc['version']}).json()
    assert started['status']=='queued'
    assert client.put(path,json={'version':started['version'],'title':'x','pages':started['pages']}).status_code==409
    cancelled=client.post(path+'/cancel').json()
    assert cancelled['status']=='cancelled'
    retried=client.post(path+'/start',json={'version':cancelled['version']}).json()
    assert retried['status']=='queued'


def test_image_pdf_before_ocr_and_download_access(app,client,png):
    doc=uploaded(client,png)
    result=client.post(f'/api/documents/{doc["id"]}/exports',json={'version':doc['version'],'format':'pdf-image'})
    assert result.status_code==200,result.text
    url=result.json()['url']
    response=client.get(url)
    assert response.content.startswith(b'%PDF-')
    with fitz.open(stream=response.content,filetype='pdf') as pdf:
        assert len(pdf)==1
        assert not pdf[0].get_text().strip()
    with TestClient(app) as other:
        other.get('/api/session')
        assert other.get(url).status_code==404
    denied=client.post(f'/api/documents/{doc["id"]}/exports',json={'version':doc['version'],'format':'docx'})
    assert denied.status_code==409


def test_transform_redacts_and_invalidates_exports(app,client,png):
    doc=uploaded(client,png)
    base=f'/api/documents/{doc["id"]}'
    url=client.post(base+'/exports',json={'version':doc['version'],'format':'pdf-image'}).json()['url']
    response=client.post(base+f'/pages/{doc["pages"][0]["id"]}/transform',json={'version':doc['version'],'redactions':[[0,0,.5,.5]],'rotate':90})
    assert response.status_code==200,response.text
    updated=response.json()
    assert updated['pages'][0]['width']==900
    assert client.get(url).status_code==404
    image=Image.open(io.BytesIO(client.get(base+f'/pages/{doc["pages"][0]["id"]}/image').content))
    assert image.getpixel((890,10))==(0,0,0)
    assert updated['pages'][0]['blocks']==[]


def test_bad_inputs_and_cross_origin(client,png):
    assert client.post('/api/documents',files={'files':('bad.png',b'bad')}).status_code==400
    assert client.post('/api/documents',files={'files':('empty.png',b'')}).status_code==400
    assert client.post('/api/documents',headers={'Origin':'https://evil.example'},files={'files':('a.png',png)}).status_code==403
    assert client.post('/api/documents',headers={'Content-Length':str(60*1024*1024)}).status_code==413


def test_duplicate_page_and_bbox_rejected(client,png):
    doc=uploaded(client,png)
    assert client.put(f'/api/documents/{doc["id"]}',json={'version':doc['version'],'title':'x','pages':doc['pages']*2}).status_code==400
    page=doc['pages'][0]
    page['blocks']=[{'bbox':[0,0,2,1],'text':'bad'}]
    assert client.put(f'/api/documents/{doc["id"]}',json={'version':doc['version'],'title':'x','pages':[page]}).status_code==422


def test_original_text_preserved_on_save(app,client,png):
    data=uploaded(client,png)
    store=app.state.store
    doc=store.get(data['id'])
    doc.pages[0].blocks=[Block(bbox=[.1,.1,.7,.2],text='原始识别',original_text='原始识别',source='rapidocr')]
    doc.pages[0].status='ready'
    doc.status='ready_for_review'
    store.save(doc,doc.version)
    body=doc.model_dump()
    body['pages'][0]['blocks'][0].update(text='已校对',original_text='伪造原始值')
    result=client.put(f'/api/documents/{doc.id}',json={'version':doc.version,'title':doc.title,'pages':body['pages']}).json()
    assert result['pages'][0]['blocks'][0]['original_text']=='原始识别'
    assert result['pages'][0]['blocks'][0]['text']=='已校对'


def test_expiry_and_recovery(app,client,png):
    data=uploaded(client,png)
    store=app.state.store
    doc=store.get(data['id'])
    doc.status='processing'
    doc.pages[0].status='processing'
    store.save(doc,doc.version)
    store.recover()
    assert store.get(doc.id).status=='queued'
    assert store.get(doc.id).pages[0].status=='pending'
    with store.db() as db:
        db.execute('UPDATE documents SET expires=? WHERE id=?',((now()-timedelta(hours=1)).isoformat(),doc.id))
    assert client.get(f'/api/documents/{doc.id}').status_code==404
    store.cleanup()
    assert not store.folder(doc.id).exists()
