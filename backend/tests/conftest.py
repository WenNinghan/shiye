import io
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from shiye.config import Settings
from shiye.main import create_app
from shiye.models import Block, Document, Page
from shiye.store import now


@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=tmp_path/"data", web_dir=tmp_path/"web", worker_enabled=False)


@pytest.fixture
def app(settings):
    return create_app(settings)


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        client.get("/api/session")
        yield client


@pytest.fixture
def png():
    stream = io.BytesIO()
    Image.new("RGB", (700, 900), "white").save(stream, format="PNG")
    return stream.getvalue()


@pytest.fixture
def document(tmp_path):
    page = Page(source_name="中文样例.png", source_page=1, width=700, height=900, status="ready", blocks=[
        Block(kind="title", bbox=[.1,.1,.8,.15], text="识页中文测试", original_text="原始标题", source="rapidocr"),
        Block(bbox=[.1,.2,.85,.3], text="2026年9月12日下午2点参加项目分享活动。", original_text="原始文字"),
        Block(kind="table", bbox=[.1,.4,.9,.6], cells=[["时间","活动"],["14:00","项目展示"]]),
        Block(kind="image", bbox=[.1,.7,.5,.8]),
    ])
    stamp=now()
    doc=Document(title="识页样例", created_at=stamp.isoformat(), updated_at=stamp.isoformat(), expires_at=(stamp+timedelta(hours=24)).isoformat(), pages=[page], status="ready_for_review")
    folder=tmp_path/"assets"
    folder.mkdir()
    Image.new("RGB", (700,900), "#faf9f1").save(folder/f"{page.id}.png")
    return doc, folder
