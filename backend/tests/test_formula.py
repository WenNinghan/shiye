import io
import zipfile

from PIL import Image

from shiye.formula import clean_latex, formula_block, merge_formula_blocks
from shiye.models import Block


class FakeFormula:
    def peek_status(self):
        return {"available": True, "running": False, "model_cached": True, "model": "test", "device": "cpu", "engine": "fake", "install_command": ""}

    def status(self):
        return {**self.peek_status(), "message": "ready", "loaded": True}

    def recognize(self, path, bbox):
        assert path.is_file()
        return {"latex": r"\frac{x^2}{2}", "elapsed_ms": 1}

    def scan(self, path, min_score=0.5):
        assert path.is_file()
        return {"formulas": [{"latex": r"\int_0^1 x\,dx", "bbox": [70, 180, 560, 270], "confidence": 0.96}], "elapsed_ms": 2}

    def stop(self):
        pass


def upload(client):
    data = io.BytesIO()
    Image.new("RGB", (700, 900), "white").save(data, "PNG")
    response = client.post("/api/documents", files={"files": ("formula.png", data.getvalue(), "image/png")})
    assert response.status_code == 201
    return response.json()


def test_formula_helpers_preserve_verified_and_replace_ocr():
    assert clean_latex(r"$$ \frac12 $$") == r"\frac12"
    auto = formula_block({"latex": r"x^2", "bbox": [10, 10, 90, 30], "confidence": 0.9}, 100, 100, source="paddle-formula-auto")
    text = Block(kind="title", bbox=[0.1, 0.1, 0.9, 0.3], text="x2", source="rapidocr")
    verified = Block(kind="formula", bbox=[0.1, 0.5, 0.9, 0.6], text="y", latex="y", verified=True, source="manual")
    merged = merge_formula_blocks([text, verified], [auto])
    assert [block.kind for block in merged] == ["formula", "formula"]
    assert any(block.verified for block in merged)


def test_formula_api_region_scan_and_dedup(app, client):
    app.state.formula = FakeFormula()
    doc = upload(client)
    base = f"/api/documents/{doc['id']}"
    page_id = doc["pages"][0]["id"]
    assert client.get("/api/formula/status").json()["available"] is True
    bad = client.post(f"{base}/pages/{page_id}/formula/recognize", json={"version": doc["version"], "bbox": [0, 0, 0, 1]})
    assert bad.status_code == 400
    first = client.post(f"{base}/pages/{page_id}/formula/scan", json={"version": doc["version"], "min_score": 0.5})
    assert first.status_code == 200, first.text
    scanned = first.json()
    formulas = [block for block in scanned["pages"][0]["blocks"] if block["kind"] == "formula"]
    assert len(formulas) == 1 and formulas[0]["latex"].startswith(r"\int")
    second = client.post(f"{base}/pages/{page_id}/formula/scan", json={"version": scanned["version"], "min_score": 0.5})
    assert len([block for block in second.json()["pages"][0]["blocks"] if block["kind"] == "formula"]) == 1
    region = client.post(
        f"{base}/pages/{page_id}/formula/recognize",
        json={"version": second.json()["version"], "bbox": [0.1, 0.2, 0.8, 0.3]},
    )
    assert region.status_code == 200, region.text
    formulas = [block for block in region.json()["pages"][0]["blocks"] if block["kind"] == "formula"]
    assert len(formulas) == 1 and formulas[0]["latex"] == r"\frac{x^2}{2}"
    assert formulas[0]["verified"] is False


def test_academic_start_requires_available_engine(client, png):
    doc = client.post("/api/documents", files={"files": ("sample.png", png, "image/png")}).json()
    response = client.post(f"/api/documents/{doc['id']}/start", json={"version": doc["version"], "mode": "academic"})
    assert response.status_code == 409
