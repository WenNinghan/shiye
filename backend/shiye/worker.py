import multiprocessing
import threading
import time

from .formula import FormulaError, formula_block, merge_formula_blocks
from .models import Block
from .recognition import recognize_child
from .store import Conflict
from .cloud_ocr import CloudError


class Worker:
    """One persistent SQLite queue, one bounded OCR child at a time."""
    def __init__(self, store, lock, formula=None, cloud=None):
        self.store = store
        self.lock = lock
        self.formula = formula
        self.cloud = cloud
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        self.store.recover()
        self.thread = threading.Thread(target=self.run, daemon=True, name="shiye-worker")
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)

    def run(self):
        last_cleanup = 0
        while not self.stop_event.is_set():
            if time.monotonic() - last_cleanup > 60:
                with self.lock:
                    self.store.cleanup()
                last_cleanup = time.monotonic()
            for doc_id in self.store.pending():
                if self.stop_event.is_set():
                    break
                try:
                    self.process(doc_id)
                except Conflict:
                    pass  # A cancel/delete/revision is authoritative, never overwrite it.
                except Exception as exc:
                    with self.lock:
                        doc = self.store.get(doc_id)
                        if doc and doc.status == "processing":
                            doc.status = "failed"
                            doc.message = f"处理失败：{type(exc).__name__}。可重试未完成页。"
                            self.store.save(doc, doc.version)
            self.stop_event.wait(0.4)

    def process(self, doc_id):
        with self.lock:
            doc = self.store.get(doc_id)
            if not doc or doc.status != "queued":
                return
            cloud_mode = doc.provider == "api"
            if not cloud_mode:
                doc.status = "processing"
                self.store.save(doc, doc.version)
                page_ids = [p.id for p in doc.pages if p.status != "ready"]
        if cloud_mode:
            return self.process_cloud(doc_id)
        for page_id in page_ids:
            with self.lock:
                doc = self.store.get(doc_id)
                if not doc or doc.status != "processing" or self.stop_event.is_set():
                    return
                page = next(p for p in doc.pages if p.id == page_id)
                page.status = "processing"
                doc.message = f"正在处理第 {doc.pages.index(page)+1} / {len(doc.pages)} 页"
                self.store.save(doc, doc.version)
                native = page.engine == "PDF 原生文字" and bool(page.blocks)
            if native:
                result = {"ok": True, "result": ([b.model_dump() for b in page.blocks], page.engine)}
            else:
                result = self.bounded_ocr(doc_id, page_id)
                if result is None:
                    return
            formula_additions = []
            formula_error = ""
            if result["ok"] and self.formula:
                with self.lock:
                    current = self.store.get(doc_id)
                    academic = bool(current and current.status == "processing" and current.mode == "academic")
                    if academic:
                        current.message = f"第 {current.pages.index(next(p for p in current.pages if p.id == page_id))+1} 页：正在检测并识别公式"
                        self.store.save(current, current.version)
                if academic:
                    try:
                        scan = self.formula.scan(self.store.folder(doc_id) / f"{page_id}.png")
                        for item in scan.get("formulas", []):
                            try:
                                formula_additions.append(
                                    formula_block(item, page.width, page.height, source="paddle-formula-auto")
                                )
                            except FormulaError:
                                continue
                    except FormulaError as exc:
                        formula_error = str(exc)
            with self.lock:
                doc = self.store.get(doc_id)
                if not doc or doc.status != "processing":
                    return
                page = next(p for p in doc.pages if p.id == page_id)
                if result["ok"]:
                    page.blocks = [Block.model_validate(b) for b in result["result"][0]]
                    page.engine = result["result"][1]
                    if formula_additions:
                        page.blocks = merge_formula_blocks(page.blocks, formula_additions)
                        page.engine += " + PP-FormulaNet"
                    if formula_error:
                        warning = f"第 {doc.pages.index(page)+1} 页公式增强未完成：{formula_error}"
                        if warning not in doc.warnings:
                            doc.warnings.append(warning)
                    page.status, page.error = "ready", ""
                else:
                    page.status, page.error = "failed", result["error"]
                self.store.save(doc, doc.version)
        with self.lock:
            doc = self.store.get(doc_id)
            if doc and doc.status == "processing":
                failed = sum(p.status == "failed" for p in doc.pages)
                doc.status = "partial" if failed and failed < len(doc.pages) else "failed" if failed else "ready_for_review"
                formula_count = sum(b.kind == "formula" for p in doc.pages for b in p.blocks)
                if failed:
                    doc.message = f"{failed} 页未完成，可单独重试；已完成页可以校对和导出"
                elif doc.mode == "academic":
                    doc.message = f"学术识别完成，共找到 {formula_count} 个公式；请对照原图逐个核对"
                else:
                    doc.message = "识别完成，请校对后导出"
                self.store.save(doc, doc.version)

    def process_cloud(self, doc_id):
        with self.lock:
            doc = self.store.get(doc_id)
            if not doc or doc.status != "queued":
                return
            doc.status = "processing"
            self.store.save(doc, doc.version)
            targets = list(doc.target_pages)
        errors = 0
        for page_id in targets:
            with self.lock:
                doc = self.store.get(doc_id)
                if not doc or doc.status != "processing" or self.stop_event.is_set():
                    return
                page = next(p for p in doc.pages if p.id == page_id)
                page.status = "processing"
                doc.message = f"API 识别第 {doc.pages.index(page)+1} 页；原校对内容保留"
                self.store.save(doc, doc.version)
                engine_name = self.cloud.status()["model"]
            def cancelled():
                current = self.store.get(doc_id)
                return self.stop_event.is_set() or not current or current.status != "processing"
            try:
                result = self.cloud.recognize(doc_id, page_id, self.store.folder(doc_id) / f"{page_id}.png", cancelled, doc.target_bbox)
                error = ""
            except Exception as exc:
                result = None
                error = str(exc) if isinstance(exc, CloudError) else "API 处理失败；原内容保留"
            with self.lock:
                doc = self.store.get(doc_id)
                if not doc or doc.status != "processing":
                    return
                page = next(p for p in doc.pages if p.id == page_id)
                if result:
                    page.candidate_blocks = result
                    page.candidate_engine = engine_name
                    page.candidate_bbox = doc.target_bbox
                    page.status, page.error = ("ready" if page.blocks else "pending"), ""
                else:
                    page.status, page.error = ("ready" if page.blocks else "failed"), error
                    errors += 1
                self.store.save(doc, doc.version)
        with self.lock:
            doc = self.store.get(doc_id)
            if doc and doc.status == "processing":
                doc.status = "ready_for_review" if errors == 0 else "partial"
                doc.message = "API 候选已返回；请逐页预览并选择采用，原校对内容未覆盖" if errors == 0 else "部分 API 页面失败，成功候选和原内容均保留"
                self.store.save(doc, doc.version)
        self.cloud.revoke(doc_id)

    def bounded_ocr(self, doc_id, page_id):
        ctx = multiprocessing.get_context("spawn")
        receive, send = ctx.Pipe(duplex=False)
        process = ctx.Process(target=recognize_child, args=(str(self.store.folder(doc_id) / f"{page_id}.png"), send), daemon=True)
        process.start()
        send.close()
        started = time.monotonic()
        try:
            while not receive.poll(0.2):
                doc = self.store.get(doc_id)
                if self.stop_event.is_set() or not doc or doc.status != "processing":
                    return None
                if time.monotonic() - started > self.store.settings.page_timeout:
                    return {"ok": False, "error": f"本页识别超时（{self.store.settings.page_timeout} 秒），请裁剪、缩小图片后重试。"}
                if not process.is_alive():
                    return {"ok": False, "error": "OCR 进程提前结束，请重试本页。"}
            try:
                return receive.recv()
            except EOFError:
                return {"ok": False, "error": "OCR 进程未返回结果。"}
        finally:
            receive.close()
            process.join(timeout=0.5)
            if process.is_alive():
                process.terminate()
                process.join(timeout=2)
