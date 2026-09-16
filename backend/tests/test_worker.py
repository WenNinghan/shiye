import threading
import time

from shiye.models import Block
from shiye.worker import Worker


def test_real_worker_timeout_preserves_uploaded_page(app,client,png):
    data=client.post('/api/documents',files={'files':('test.png',png)}).json()
    store=app.state.store
    doc=store.get(data['id'])
    doc.status='processing'
    store.save(doc,doc.version)
    store.settings.page_timeout=0.01
    worker=Worker(store,threading.RLock())
    result=worker.bounded_ocr(doc.id,doc.pages[0].id)
    assert not result['ok'] and '超时' in result['error']
    assert (store.folder(doc.id)/f'{doc.pages[0].id}.png').is_file()


def test_retry_skips_ready_pages(app,client,png):
    response=client.post('/api/documents',files=[('files',('one.png',png)),('files',('two.png',png))])
    doc=app.state.store.get(response.json()['id'])
    doc.pages[0].status='ready'
    doc.pages[0].blocks=[Block(bbox=[0,0,.8,.1],text='已经校对，不应重新 OCR')]
    doc.pages[1].status='pending'
    doc.pages[1].engine='PDF 原生文字'
    doc.pages[1].blocks=[Block(bbox=[0,0,.8,.1],text='第二页原生文字')]
    doc.status='queued'
    app.state.store.save(doc,doc.version)
    worker=Worker(app.state.store,threading.RLock())
    worker.process(doc.id)
    result=app.state.store.get(doc.id)
    assert result.status=='ready_for_review'
    assert result.pages[0].blocks[0].text=='已经校对，不应重新 OCR'
    assert result.pages[1].status=='ready'
