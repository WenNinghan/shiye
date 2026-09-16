from shiye.models import TaskItem


def test_task_draft_survives_reload_and_redaction_clears_it(client, png):
    doc=client.post('/api/documents',files={'files':('test.png',png)}).json()
    task=TaskItem(title='参加项目交流',source_text='明天参加项目交流',page_id=doc['pages'][0]['id'],date='2026-09-12',confirmed=True)
    saved=client.put(f'/api/documents/{doc["id"]}',json={'version':doc['version'],'title':doc['title'],'pages':doc['pages'],'tasks':[task.model_dump()]}).json()
    assert client.get(f'/api/documents/{doc["id"]}').json()['tasks'][0]['confirmed'] is True
    transformed=client.post(f'/api/documents/{doc["id"]}/pages/{doc["pages"][0]["id"]}/transform',json={'version':saved['version'],'redactions':[[.1,.1,.5,.5]]})
    assert transformed.status_code==200
    assert transformed.json()['tasks']==[]
