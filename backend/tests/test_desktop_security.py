from fastapi.testclient import TestClient
from shiye.main import create_app


def test_desktop_requires_distinct_tokens_and_exact_host(settings):
    settings.desktop_token, settings.control_token, settings.desktop_host = "a"*64, "b"*64, "testserver"
    app = create_app(settings)
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 403
        client.headers["x-shiye-desktop"] = settings.desktop_token
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/health", headers={"host": "evil.example"}).status_code == 403
        assert client.delete("/internal/desktop/config").status_code == 403
        assert client.delete("/internal/desktop/config", headers={"x-shiye-control": settings.control_token}).status_code == 200
        client.get("/api/session")
        assert client.post("/api/documents", headers={"origin": "https://evil.example"}).status_code == 403


def test_browser_does_not_expose_control(client):
    assert client.delete("/internal/desktop/config").status_code in {404, 405}
    assert client.get("/api/recognition/status").json()["desktop"] is False


def test_invalid_settings_never_echo_key(settings):
    settings.desktop_token, settings.control_token, settings.desktop_host = "a"*64, "b"*64, "testserver"
    with TestClient(create_app(settings)) as client:
        response = client.put("/internal/desktop/config", headers={"x-shiye-control": "b"*64},
            json={"endpoint": ["wrong"], "model": "vision", "key": "FAKE-DO-NOT-ECHO"})
        assert response.status_code == 422
        assert "FAKE-DO-NOT-ECHO" not in response.text
