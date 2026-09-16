import json
import socket
import pytest
from fastapi.testclient import TestClient
from shiye.main import create_app
from shiye.cloud_ocr import CloudClient, CloudError, endpoint_parts, public_addresses, parse_blocks
from shiye.models import Block

PROFILE = {"endpoint": "https://api.example.com/v1/chat/completions", "model": "test-vision", "key": "FAKE-TEST-KEY"}


def payload(rows, finish="stop"):
    return {"choices": [{"message": {"content": json.dumps({"blocks": rows})}, "finish_reason": finish}]}


@pytest.mark.parametrize("endpoint", ["http://api.example.com", "https://127.0.0.1/x", "https://a.local/x",
    "https://u:p@api.example.com/x", "https://api.example.com/x?key=fake", "https://api.example.com:8443/x"])
def test_endpoint_rejects_unsafe(endpoint):
    with pytest.raises(CloudError):
        endpoint_parts(endpoint)


def test_dns_rejects_mixed_public_private(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kw: [
        (None, None, None, None, ("8.8.8.8", 443)), (None, None, None, None, ("127.0.0.1", 443))])
    with pytest.raises(CloudError):
        public_addresses("api.example.com")


def test_parse_cannot_invent_confidence_coordinates_or_confirmation():
    blocks = parse_blocks(payload([{"kind":"formula","latex":"x^2","confidence":1,"verified":True,"bbox":[.2,.2,.3,.3]}]))
    assert blocks[0].bbox == [0,0,1,1]
    assert blocks[0].confidence is None and blocks[0].verified is False
    assert blocks[0].source == "cloud-page"
    for bad in ({}, payload([], "stop"), payload([{"kind":"paragraph","text":"x"}], "length"),
                payload([{"kind":"script","text":"bad"}])):
        with pytest.raises(CloudError):
            parse_blocks(bad)


def test_authorization_single_use_and_reconfigure_revokes(monkeypatch, tmp_path):
    client = CloudClient()
    status = client.configure(PROFILE)
    monkeypatch.setattr("shiye.cloud_ocr.transcribe", lambda *args: [Block(text="candidate", bbox=[0,0,1,1])])
    client.authorize("doc", ["page"], status["revision"])
    assert client.recognize("doc", "page", tmp_path, lambda: False)
    with pytest.raises(CloudError):
        client.recognize("doc", "page", tmp_path, lambda: False)
    client.authorize("doc", ["page"], status["revision"])
    client.configure(None)
    with pytest.raises(CloudError):
        client.recognize("doc", "page", tmp_path, lambda: False)


def test_cloud_candidates_do_not_replace_original_until_accept(settings, png, monkeypatch):
    settings.desktop_token, settings.control_token, settings.desktop_host = "a"*64, "b"*64, "testserver"
    app = create_app(settings)
    monkeypatch.setattr("shiye.cloud_ocr.transcribe", lambda *args: [Block(text="API candidate", bbox=[0,0,1,1], source="cloud-page")])
    with TestClient(app) as client:
        client.headers["x-shiye-desktop"] = "a"*64
        client.get("/api/session")
        profile = client.put("/internal/desktop/config", json=PROFILE, headers={"x-shiye-control": "b"*64}).json()
        doc = client.post("/api/documents", files={"files": ("test.png", png, "image/png")}).json()
        original = app.state.store.get(doc["id"])
        original.pages[0].blocks = [Block(text="manual original", bbox=[0,0,1,1], verified=True)]
        app.state.store.save(original, original.version)
        doc = client.get("/api/documents/"+doc["id"]).json()
        command = {"version": doc["version"], "provider":"api","consent":False,
                   "provider_revision":profile["revision"],"page_ids":[doc["pages"][0]["id"]]}
        route = "/api/documents/"+doc["id"]
        assert client.post(route+"/start", json=command).status_code == 403
        command["consent"] = True
        assert client.post(route+"/start", json=command).status_code == 200
        app.state.worker.process(doc["id"])
        result = client.get(route).json()
        page = result["pages"][0]
        assert page["blocks"][0]["text"] == "manual original"
        assert page["candidate_blocks"][0]["text"] == "API candidate"
        response = client.post(route+f'/pages/{page["id"]}/candidate', json={"version":result["version"],"accept":True})
        assert response.status_code == 200
        assert response.json()["pages"][0]["blocks"][0]["text"] == "API candidate"
        assert response.json()["pages"][0]["candidate_blocks"] is None
        assert PROFILE["key"] not in response.text


def test_recovery_does_not_restart_paid_jobs(app, client, png):
    doc = client.post("/api/documents", files={"files": ("test.png", png, "image/png")}).json()
    value = app.state.store.get(doc["id"])
    value.provider, value.status = "api", "queued"
    app.state.store.save(value, value.version)
    app.state.store.recover()
    assert app.state.store.get(doc["id"]).status == "cancelled"
