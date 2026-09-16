import json
import os
import queue
import subprocess
import threading
import time
from pathlib import Path

from .models import Block


class FormulaError(RuntimeError):
    pass


def _area(box: list[float]) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def overlap(a: list[float], b: list[float]) -> float:
    """Intersection divided by the smaller region, useful for OCR line replacement."""
    intersection = max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(
        0.0, min(a[3], b[3]) - max(a[1], b[1])
    )
    return intersection / max(1e-9, min(_area(a), _area(b)))


def clean_latex(value: str) -> str:
    value = (value or "").strip()
    pairs = (("$$", "$$"), (r"\[", r"\]"), (r"\(", r"\)"), ("$", "$"))
    for left, right in pairs:
        if value.startswith(left) and value.endswith(right) and len(value) >= len(left) + len(right):
            return value[len(left) : -len(right)].strip()
    return value


def formula_block(item: dict, width: int, height: int, *, source: str, bbox=None) -> Block:
    raw_box = bbox or item.get("bbox")
    if not raw_box or len(raw_box) != 4:
        raise FormulaError("公式引擎没有返回有效坐标")
    if bbox is None:
        raw_box = [
            max(0.0, min(1.0, raw_box[0] / width)),
            max(0.0, min(1.0, raw_box[1] / height)),
            max(0.0, min(1.0, raw_box[2] / width)),
            max(0.0, min(1.0, raw_box[3] / height)),
        ]
    latex = clean_latex(item.get("latex", ""))
    if not latex:
        raise FormulaError("未识别出公式内容，请把框选范围收紧后重试")
    confidence = item.get("confidence")
    return Block(
        kind="formula",
        bbox=[round(float(v), 7) for v in raw_box],
        text=latex,
        latex=latex,
        original_text=latex,
        confidence=float(confidence) if confidence is not None else None,
        source=source,
        display=True,
        verified=False,
        warning="公式由模型识别，导出前请对照原图核对符号、上下标和括号。",
    )


def merge_formula_blocks(existing: list[Block], additions: list[Block], *, directed=False) -> list[Block]:
    """Merge model formulas while preserving user-verified/manual content."""
    result = []
    for block in existing:
        replaceable_formula = block.kind == "formula" and (
            directed or (not block.verified and block.source.startswith("paddle-formula"))
        )
        # RapidOCR often labels a large display equation as a title.  Once the
        # formula detector covers it, keep the mathematical block instead of
        # showing the OCR gibberish beside it.
        covered_text = block.kind in {"title", "paragraph", "list"} and any(
            overlap(block.bbox, formula.bbox) >= 0.72 for formula in additions
        )
        covered_formula = replaceable_formula and any(
            overlap(block.bbox, formula.bbox) >= 0.58 for formula in additions
        )
        if not covered_text and not covered_formula:
            result.append(block)
    for formula in additions:
        if not any(
            block.kind == "formula" and overlap(block.bbox, formula.bbox) >= 0.72
            for block in result
        ):
            result.append(formula)
    result.sort(key=lambda block: (round(block.bbox[1], 3), block.bbox[0]))
    return result


class FormulaClient:
    """A serialized JSON-lines client for the optional long-lived Paddle process."""

    def __init__(self, settings):
        self.settings = settings
        self.runtime = settings.formula_runtime()
        self.script = Path(__file__).resolve().parents[2] / "scripts" / "formula_engine.py"
        self.process = None
        self.lock = threading.Lock()
        self.log_handle = None
        self.sequence = 0

    @property
    def configured(self) -> bool:
        if self.runtime.get("executable"):
            return Path(self.runtime["executable"]).is_file()
        return bool(self.runtime["python"]) and Path(self.runtime["python"]).is_file() and self.script.is_file()

    def _base_status(self) -> dict:
        cache_model = Path(self.runtime["cache"]) / "official_models" / self.runtime["model"]
        return {
            "available": self.configured,
            "running": bool(self.process and self.process.poll() is None),
            "model_cached": cache_model.is_dir(),
            "model": self.runtime["model"],
            "device": self.runtime["device"],
            "engine": "PaddleOCR · PP-FormulaNet",
            "install_command": "powershell -ExecutionPolicy Bypass -File scripts/install-formula.ps1",
        }

    def peek_status(self) -> dict:
        return self._base_status()

    def status(self) -> dict:
        status = self._base_status()
        if not self.configured:
            status["message"] = "公式增强尚未安装；普通 OCR 不受影响。"
            return status
        try:
            result = self.request("status", timeout=20)
            status.update(result)
            status["available"] = True
            status["running"] = True
            status["message"] = "公式引擎已就绪" if status["model_cached"] else "运行环境已安装，首次识别会下载模型"
        except FormulaError as exc:
            status["available"] = False
            status["message"] = str(exc)
        return status

    def _start(self):
        if self.process and self.process.poll() is None:
            return
        if not self.configured:
            raise FormulaError("公式增强尚未安装，请先运行 scripts/install-formula.ps1")
        self.stop()
        log_path = self.settings.data_dir / "formula-engine.log"
        if log_path.is_file() and log_path.stat().st_size > 5 * 1024 * 1024:
            log_path.replace(log_path.with_suffix(".previous.log"))
        self.log_handle = log_path.open("a", encoding="utf-8")
        env = os.environ.copy()
        env.update(
            {
                "PADDLE_PDX_CACHE_HOME": self.runtime["cache"],
                "PADDLE_PDX_MODEL_SOURCE": "BOS",
                "PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK": "True",
                "PYTHONUTF8": "1",
            }
        )
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        command = [self.runtime["executable"]] if self.runtime.get("executable") else [
                self.runtime["python"],
                str(self.script),
            ]
        self.process = subprocess.Popen(
            command + [
                "--serve",
                "--model",
                self.runtime["model"],
                "--device",
                self.runtime["device"],
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.log_handle,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=str(self.settings.data_dir),
            env=env,
            creationflags=creationflags,
        )

    def _readline(self, timeout: float) -> str:
        output = queue.Queue(maxsize=1)

        def read():
            try:
                output.put(self.process.stdout.readline())
            except Exception as exc:  # pragma: no cover - OS pipe failures
                output.put(exc)

        thread = threading.Thread(target=read, daemon=True)
        thread.start()
        try:
            value = output.get(timeout=timeout)
        except queue.Empty as exc:
            self.stop()
            raise FormulaError(f"公式识别超过 {int(timeout)} 秒，已停止该次任务") from exc
        if isinstance(value, Exception):
            self.stop()
            raise FormulaError("公式引擎通信失败") from value
        if not value:
            code = self.process.poll()
            self.stop()
            raise FormulaError(f"公式引擎提前退出（code={code}），详见 .data/formula-engine.log")
        return value

    def request(self, action: str, timeout=None, **payload) -> dict:
        with self.lock:
            self._start()
            self.sequence += 1
            request_id = str(self.sequence)
            message = {"id": request_id, "action": action, **payload}
            try:
                self.process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
                self.process.stdin.flush()
            except (BrokenPipeError, OSError) as exc:
                self.stop()
                raise FormulaError("公式引擎无法接收任务，请重试") from exc
            line = self._readline(timeout or self.settings.formula_timeout)
            try:
                response = json.loads(line)
            except ValueError as exc:
                self.stop()
                raise FormulaError("公式引擎返回了无效结果") from exc
            if response.get("id") != request_id:
                self.stop()
                raise FormulaError("公式引擎响应顺序异常，请重试")
            if not response.get("ok"):
                raise FormulaError(response.get("error") or "公式识别失败")
            return response.get("result") or {}

    def recognize(self, path: Path, bbox: list[float]) -> dict:
        return self.request("recognize", path=str(path), bbox=bbox)

    def scan(self, path: Path, min_score=0.5) -> dict:
        return self.request("scan", path=str(path), min_score=min_score)

    def stop(self):
        process, self.process = self.process, None
        if process:
            try:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    process.kill()
                except OSError:
                    pass
        if self.log_handle:
            self.log_handle.close()
            self.log_handle = None
