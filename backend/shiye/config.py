import os
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Settings:
    data_dir: Path = field(default_factory=lambda: Path(os.environ.get("SHIYE_DATA_DIR", Path(__file__).resolve().parents[2] / ".data")).resolve())
    web_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parents[2] / "web" / "dist")
    max_bytes: int = 50 * 1024 * 1024
    max_pages: int = 20
    max_pixels: int = 32_000_000
    ttl_hours: int = 24
    worker_enabled: bool = True
    page_timeout: int = 120
    formula_timeout: int = 240
    desktop_token: str = ""
    control_token: str = ""
    desktop_host: str = ""

    def formula_runtime(self) -> dict:
        """Resolve the optional, isolated formula runtime without importing Paddle."""
        config = {}
        path = self.data_dir / "formula-runtime.json"
        if path.is_file():
            try:
                config = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError):
                config = {}
        project = Path(__file__).resolve().parents[2]
        local = project / ".formula-venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        python = os.environ.get("SHIYE_FORMULA_PYTHON") or config.get("python") or (str(local) if local.is_file() else "")
        cache = os.environ.get("SHIYE_FORMULA_CACHE") or config.get("cache") or str(project / ".formula-cache")
        return {
            "executable": str(config.get("executable", "")),
            "python": str(python),
            "cache": str(cache),
            "device": os.environ.get("SHIYE_FORMULA_DEVICE") or config.get("device") or "cpu",
            "model": os.environ.get("SHIYE_FORMULA_MODEL") or config.get("model") or "PP-FormulaNet_plus-M",
        }

    def prepare(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "documents").mkdir(exist_ok=True)
