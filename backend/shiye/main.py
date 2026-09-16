import asyncio
import logging
import os
import re
import shutil
import secrets
import sys
import threading
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from PIL import Image, ImageDraw
from pydantic import BaseModel, Field

from .config import Settings
from .exports import export_document
from .formula import FormulaClient, FormulaError, formula_block, merge_formula_blocks
from .models import Document, EditDocument, ExportRequest, TaskItem, Transform, uid
from .recognition import ingest
from .store import Conflict, Store, now
from .tasks import export_ics, extract_tasks
from .worker import Worker
from .cloud_ocr import CloudClient, CloudError
from .desktop_control import install_control

logger = logging.getLogger("shiye")


class Action(BaseModel):
    version: int
    mode: str = "document"
    provider: str = "local"
    consent: bool = False
    provider_revision: int = 0
    page_ids: list[str] = Field(default_factory=list, max_length=20)
    bbox: list[float] | None = Field(default=None, min_length=4, max_length=4)


class CandidateAction(BaseModel):
    version: int
    accept: bool


class TaskRequest(BaseModel):
    reference_date: date


class CalendarRequest(BaseModel):
    tasks: list[TaskItem] = Field(max_length=100)


class FormulaRegionRequest(BaseModel):
    version: int
    bbox: list[float] = Field(min_length=4, max_length=4)


class FormulaScanRequest(BaseModel):
    version: int
    min_score: float = Field(default=0.5, ge=0.2, le=0.95)


class PayloadTooLarge(Exception):
    pass


class BodyLimit:
    def __init__(self, app, limit):
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        count = 0
        async def bounded_receive():
            nonlocal count
            message = await receive()
            count += len(message.get("body", b""))
            if count > self.limit:
                raise PayloadTooLarge()
            return message
        try:
            return await self.app(scope, bounded_receive, send)
        except PayloadTooLarge:
            return await JSONResponse({"detail": "请求超过 50 MB 限制"}, 413)(scope, receive, send)


def create_app(settings: Settings | None = None):
    settings = settings or Settings()
    store = Store(settings)
    lock = threading.RLock()
    formula = FormulaClient(settings)
    cloud = CloudClient()
    worker = Worker(store, lock, formula, cloud)

    @asynccontextmanager
    async def lifespan(app):
        if settings.worker_enabled:
            worker.start()
        yield
        worker.stop()
        formula.stop()

    app = FastAPI(title="识页 API", version="0.2.0", lifespan=lifespan, docs_url="/api/docs", redoc_url=None)
    app.state.store, app.state.worker, app.state.formula = store, worker, formula
    app.state.cloud = cloud
    install_control(app, settings, cloud)
    app.add_middleware(BodyLimit, limit=settings.max_bytes+1024*1024)

    @app.exception_handler(Conflict)
    async def conflict_handler(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request, exc):
        return JSONResponse({"detail": "请求字段格式或长度不正确，请检查输入"}, status_code=422)

    @app.middleware("http")
    async def security(request, call_next):
        if settings.desktop_token:
            if request.headers.get("host") != settings.desktop_host:
                return JSONResponse({"detail": "拒绝非本机地址"}, 403)
            control = request.url.path.startswith("/internal/desktop/")
            expected = settings.control_token if control else settings.desktop_token
            supplied = request.headers.get("x-shiye-control" if control else "x-shiye-desktop", "")
            if not supplied or not secrets.compare_digest(supplied, expected):
                return JSONResponse({"detail": "桌面访问凭证无效"}, 403)
        content_length = request.headers.get("content-length", "0")
        if not content_length.isdigit() or int(content_length) > settings.max_bytes+1024*1024:
            return JSONResponse({"detail": "请求超过 50 MB 限制"}, 413)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if origin:
                origin_url = urlsplit(origin)
                if origin_url.netloc != request.headers.get("host") or origin_url.scheme not in {"http", "https"}:
                    return JSONResponse({"detail": "拒绝跨站写入"}, 403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' blob: data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    def owner(request):
        token = request.cookies.get("shiye_session")
        if not store.valid_session(token):
            raise HTTPException(401, "会话已失效，请刷新页面")
        return token

    def owned(doc_id, request):
        doc = store.get(doc_id, owner(request))
        if doc is None:
            raise HTTPException(404, "文档不存在、已过期或不属于当前会话")
        return doc

    def mutable(doc, version):
        if doc.version != version:
            raise Conflict("文档版本已更新，请先刷新，避免覆盖其他修改。")
        if doc.status in {"processing", "queued"}:
            raise HTTPException(409, "请先取消识别再修改文档")

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": "0.3.0", "engine": "RapidOCR (CPU)", "formula": app.state.formula.peek_status(), "cloud_enabled": cloud.status()["configured"], "cloud_calls": cloud.calls > 0}

    @app.get("/api/recognition/status")
    def recognition_status(request: Request):
        owner(request)
        return {"desktop": bool(settings.desktop_token), **cloud.status()}

    @app.get("/api/formula/status")
    def formula_status():
        return app.state.formula.status()

    @app.get("/api/session")
    def session(request: Request, response: Response):
        token = request.cookies.get("shiye_session")
        if not store.valid_session(token):
            token = store.new_session()
            response.set_cookie("shiye_session", token, httponly=True, samesite="strict", secure=request.url.scheme == "https", max_age=30*24*3600)
        return {"max_mb": settings.max_bytes//1024//1024, "max_pages": settings.max_pages, "retention_hours": settings.ttl_hours, "engine": "RapidOCR 中文 CPU", "privacy": "默认本地处理。桌面版可自选 API；仅明确同意后发送所选图片至填写的第三方地址。临时文档保留 24 小时，请及时导出。"}

    @app.get("/api/documents")
    def documents(request: Request):
        return [{"id": d.id, "title": d.title, "status": d.status, "pages": len(d.pages), "created_at": d.created_at, "expires_at": d.expires_at, "version": d.version} for d in store.list(owner(request))]

    @app.post("/api/documents", status_code=201)
    async def upload(request: Request, files: list[UploadFile] = File(...), title: str = Form(""), page_range: str = Form(""), merge: bool = Form(False), mode: str = Form("document")):
        token = owner(request)
        if len(store.list(token)) >= 10:
            raise HTTPException(429, "当前会话最多保留 10 份文档，请先删除不再需要的文件")
        if not files or len(files) > settings.max_pages:
            raise HTTPException(400, "请选择 1–20 个文件")
        if sum((f.filename or "").lower().endswith(".pdf") for f in files) > 1 and not merge:
            raise HTTPException(400, "多份 PDF 默认独立处理；合成一份时请显式勾选合并")
        doc_id = uid()
        folder = store.folder(doc_id)
        total = 0
        pages = []
        try:
            for file in files:
                data = await file.read(settings.max_bytes+1)
                total += len(data)
                if total > settings.max_bytes:
                    raise ValueError("文件总大小超过 50 MB")
                if not data:
                    raise ValueError("不能上传空文件")
                filename = Path((file.filename or "未命名文件").replace("\\", "/")).name[:160]
                new_pages = await asyncio.to_thread(ingest, data, filename, folder, settings, page_range)
                pages.extend(new_pages)
                if len(pages) > settings.max_pages:
                    raise ValueError("合并后超过 20 页，请减少文件或选取部分 PDF 页码")
            stamp = now()
            title = title.strip()[:160] or Path(pages[0].source_name).stem or "未命名文档"
            doc = Document(id=doc_id, title=title, mode="academic" if mode == "academic" else "document", created_at=stamp.isoformat(), updated_at=stamp.isoformat(), expires_at=(stamp+timedelta(hours=settings.ttl_hours)).isoformat(), pages=pages, warnings=["自动识别不等于准确转录；重要数字、姓名、日期和公式请校对。"])
            store.create(doc, token)
            return doc
        except (ValueError, RuntimeError) as exc:
            if folder.exists():
                shutil.rmtree(folder)
            raise HTTPException(400, str(exc)[:300]) from exc
        except Exception:
            if folder.exists():
                shutil.rmtree(folder)
            raise
        finally:
            for file in files:
                await file.close()

    @app.get("/api/documents/{doc_id}")
    def get_document(doc_id: str, request: Request):
        return owned(doc_id, request)

    @app.get("/api/documents/{doc_id}/pages/{page_id}/image")
    def page_image(doc_id: str, page_id: str, request: Request):
        doc = owned(doc_id, request)
        if not any(p.id == page_id for p in doc.pages):
            raise HTTPException(404, "页面不存在")
        return FileResponse(store.folder(doc.id) / f"{page_id}.png", media_type="image/png")

    @app.post("/api/documents/{doc_id}/start")
    def start(doc_id: str, body: Action, request: Request):
        with lock:
            doc = owned(doc_id, request)
            mutable(doc, body.version)
            if body.provider not in {"local", "api"}:
                raise HTTPException(400, "识别引擎无效")
            if body.provider == "api":
                if not settings.desktop_token or not body.consent:
                    raise HTTPException(403, "请在桌面版明确同意发送至 API")
                selected = set(body.page_ids)
                if not selected or not selected.issubset({p.id for p in doc.pages}):
                    raise HTTPException(400, "请选择有效的发送页面")
                if body.bbox and (len(selected) != 1 or not valid_bbox(body.bbox)):
                    raise HTTPException(400, "框选公式只能发送一页中的有效区域")
                try:
                    cloud.authorize(doc.id, selected, body.provider_revision)
                except CloudError as exc:
                    raise HTTPException(409, str(exc)) from None
                doc.provider, doc.target_pages = "api", list(selected)
                doc.target_bbox = body.bbox
                doc.status, doc.message = "queued", "已同意发送选定页面；API 返回后先审阅候选内容"
                for p in doc.pages:
                    if p.id in selected:
                        p.status, p.error, p.candidate_blocks, p.candidate_engine = "pending", "", None, ""
                return store.save(doc, doc.version)
            cloud.revoke(doc.id)
            doc.provider, doc.target_pages = "local", []
            doc.target_bbox = None
            if body.mode == "academic" and not app.state.formula.peek_status()["available"]:
                raise HTTPException(409, "学术公式模式尚未安装，请先运行 scripts/install-formula.ps1；普通文档模式仍可使用")
            doc.status, doc.mode = "queued", body.mode
            doc.tasks = []
            doc.message = "已加入本机处理队列"
            for page in doc.pages:
                if page.status != "ready":
                    page.status, page.error = "pending", ""
            return store.save(doc, doc.version)

    @app.post("/api/documents/{doc_id}/cancel")
    def cancel(doc_id: str, request: Request):
        with lock:
            doc = owned(doc_id, request)
            cloud.revoke(doc.id)
            if doc.status not in {"queued", "processing"}:
                return doc
            doc.status, doc.message = "cancelled", "已取消；已完成的页面保留，可以继续识别"
            for page in doc.pages:
                if page.status == "processing":
                    page.status = "pending"
            return store.save(doc, doc.version)

    @app.put("/api/documents/{doc_id}")
    def edit(doc_id: str, body: EditDocument, request: Request):
        with lock:
            doc = owned(doc_id, request)
            mutable(doc, body.version)
            old = {p.id: p for p in doc.pages}
            ids = [p.id for p in body.pages]
            if not ids or len(set(ids)) != len(ids) or any(i not in old for i in ids):
                raise HTTPException(400, "页面列表无效")
            blocks = [b.id for p in body.pages for b in p.blocks]
            if len(blocks) != len(set(blocks)):
                raise HTTPException(400, "内容块标识重复")
            revised = []
            for page in body.pages:
                original = old[page.id]
                originals = {b.id: b for b in original.blocks}
                for block in page.blocks:
                    if block.id in originals:
                        block.original_text = originals[block.id].original_text
                        block.source = originals[block.id].source
                        block.confidence = originals[block.id].confidence
                original.blocks = page.blocks
                revised.append(original)
            removed = set(old) - set(ids)
            doc.pages, doc.title = revised, body.title
            doc.tasks = [t for t in (body.tasks if body.tasks is not None else doc.tasks) if t.page_id in ids]
            doc.message = "校对内容已保存"
            saved = store.save(doc, doc.version)
            for page_id in removed:
                (store.folder(doc.id)/f"{page_id}.png").unlink(missing_ok=True)
            invalidate_exports(doc.id)
            return saved

    def invalidate_exports(doc_id):
        with store.db() as db:
            db.execute("DELETE FROM exports WHERE document_id=?", (doc_id,))
        directory = store.folder(doc_id)/"exports"
        if directory.exists():
            shutil.rmtree(directory)

    @app.post("/api/documents/{doc_id}/pages/{page_id}/candidate")
    def resolve_candidate(doc_id: str, page_id: str, body: CandidateAction, request: Request):
        with lock:
            doc = owned(doc_id, request)
            mutable(doc, body.version)
            page = next((p for p in doc.pages if p.id == page_id), None)
            if page is None or page.candidate_blocks is None:
                raise HTTPException(404, "没有待审阅候选")
            if body.accept:
                page.blocks = merge_formula_blocks(page.blocks, page.candidate_blocks, directed=True) if page.candidate_bbox else page.candidate_blocks
                page.engine = "API · " + page.candidate_engine
                doc.tasks = []
                invalidate_exports(doc.id)
            page.candidate_blocks, page.candidate_engine = None, ""
            page.candidate_bbox = None
            page.status = "ready" if page.blocks else "pending"
            doc.message = "已采用 API 候选，请继续核对" if body.accept else "已保留原内容并丢弃候选"
            return store.save(doc, doc.version)

    def formula_page(doc, page_id):
        page = next((item for item in doc.pages if item.id == page_id), None)
        if page is None:
            raise HTTPException(404, "页面不存在")
        return page

    def valid_bbox(rect):
        return len(rect) == 4 and 0 <= rect[0] < rect[2] <= 1 and 0 <= rect[1] < rect[3] <= 1

    @app.post("/api/documents/{doc_id}/pages/{page_id}/formula/recognize")
    def recognize_formula(doc_id: str, page_id: str, body: FormulaRegionRequest, request: Request):
        if not valid_bbox(body.bbox) or (body.bbox[2] - body.bbox[0]) * (body.bbox[3] - body.bbox[1]) < 0.000025:
            raise HTTPException(400, "请选择有效且足够大的公式区域")
        with lock:
            doc = owned(doc_id, request)
            mutable(doc, body.version)
            page = formula_page(doc, page_id)
            path = store.folder(doc.id) / f"{page.id}.png"
            expected_version = doc.version
        try:
            result = app.state.formula.recognize(path, body.bbox)
            addition = formula_block(result, page.width, page.height, source="paddle-formula-region", bbox=body.bbox)
        except FormulaError as exc:
            raise HTTPException(503, str(exc)) from exc
        with lock:
            doc = owned(doc_id, request)
            mutable(doc, expected_version)
            page = formula_page(doc, page_id)
            page.blocks = merge_formula_blocks(page.blocks, [addition], directed=True)
            page.status = "ready"
            if "PP-FormulaNet" not in page.engine:
                page.engine = (page.engine + " + " if page.engine else "") + "PP-FormulaNet"
            doc.status = "ready_for_review"
            doc.message = "公式已识别为 LaTeX，请对照原图核对后标记确认"
            saved = store.save(doc, doc.version)
            invalidate_exports(doc.id)
            return saved

    @app.post("/api/documents/{doc_id}/pages/{page_id}/formula/scan")
    def scan_formulas(doc_id: str, page_id: str, body: FormulaScanRequest, request: Request):
        with lock:
            doc = owned(doc_id, request)
            mutable(doc, body.version)
            page = formula_page(doc, page_id)
            path = store.folder(doc.id) / f"{page.id}.png"
            expected_version = doc.version
            width, height = page.width, page.height
        try:
            result = app.state.formula.scan(path, body.min_score)
            additions = [
                formula_block(item, width, height, source="paddle-formula-auto")
                for item in result.get("formulas", [])
                if item.get("latex")
            ]
        except FormulaError as exc:
            raise HTTPException(503, str(exc)) from exc
        with lock:
            doc = owned(doc_id, request)
            mutable(doc, expected_version)
            page = formula_page(doc, page_id)
            page.blocks = merge_formula_blocks(page.blocks, additions)
            if additions and "PP-FormulaNet" not in page.engine:
                page.engine = (page.engine + " + " if page.engine else "") + "PP-FormulaNet"
            if additions:
                page.status = "ready"
                doc.status = "ready_for_review"
                doc.message = f"本页找到 {len(additions)} 个公式，请逐个核对 LaTeX"
            else:
                doc.message = "本页没有检测到公式；可用框选识别处理漏检区域"
            saved = store.save(doc, doc.version)
            if additions:
                invalidate_exports(doc.id)
            return saved

    @app.post("/api/documents/{doc_id}/pages/{page_id}/transform")
    def transform(doc_id: str, page_id: str, body: Transform, request: Request):
        with lock:
            doc = owned(doc_id, request)
            mutable(doc, body.version)
            page = next((p for p in doc.pages if p.id == page_id), None)
            if page is None:
                raise HTTPException(404, "页面不存在")
            rects = ([body.crop] if body.crop else []) + body.redactions
            for rect in rects:
                if len(rect) != 4 or not (0 <= rect[0] < rect[2] <= 1 and 0 <= rect[1] < rect[3] <= 1):
                    raise HTTPException(400, "请选择有效区域")
            path = store.folder(doc.id)/f"{page.id}.png"
            with Image.open(path) as source:
                img = source.convert("RGB")
            draw = ImageDraw.Draw(img)
            for r in body.redactions:
                draw.rectangle((r[0]*img.width, r[1]*img.height, r[2]*img.width, r[3]*img.height), fill="black")
            if body.crop:
                r = body.crop
                box = tuple(int(v*s) for v, s in zip(r, [img.width, img.height, img.width, img.height]))
                if box[2]-box[0] < 16 or box[3]-box[1] < 16:
                    raise HTTPException(400, "裁剪区域过小，至少保留 16×16 像素")
                img = img.crop(box)
            if body.rotate:
                img = img.rotate(-body.rotate, expand=True)
            temp = path.with_suffix(".new.png")
            img.save(temp)
            os.replace(temp, path)
            page.width, page.height = img.size
            page.blocks, page.engine, page.status, page.error = [], "", "pending", ""
            page.candidate_blocks, page.candidate_engine = None, ""
            doc.tasks = []
            page.rotation = (page.rotation + body.rotate) % 360
            doc.status, doc.message = "uploaded", "图像已更新，本页需要重新识别；旧导出已清理"
            invalidate_exports(doc.id)
            return store.save(doc, doc.version)

    @app.delete("/api/documents/{doc_id}", status_code=204)
    def delete(doc_id: str, request: Request):
        with lock:
            owned(doc_id, request)
            cloud.revoke(doc_id)
            store.delete(doc_id, owner(request))
            return Response(status_code=204)

    @app.post("/api/documents/{doc_id}/exports")
    def export(doc_id: str, body: ExportRequest, request: Request):
        with lock:
            doc = owned(doc_id, request)
            mutable(doc, body.version)
            if body.format not in {"pdf-image", "json"} and not any(p.status == "ready" for p in doc.pages):
                raise HTTPException(409, "请先识别至少一页，再导出文字格式")
            export_id = uid()
            folder = store.folder(doc.id)
            try:
                target, warnings = export_document(doc, folder, folder/"exports"/export_id, body.format)
            except Exception as exc:
                logger.exception("Export failed (%s)", type(exc).__name__)
                raise HTTPException(500, "导出失败，原文档已保留，请重试或改用其他格式") from exc
            safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", doc.title).strip(". ")[:100] or "document"
            filename = safe_name+target.suffix
            store.add_export(export_id, doc, body.format, filename, target)
            return {"id": export_id, "url": f"/api/exports/{export_id}", "filename": filename, "version": doc.version, "warnings": warnings}

    @app.get("/api/exports/{export_id}")
    def download(export_id: str, request: Request):
        result = store.get_export(export_id, owner(request))
        if not result or not Path(result["path"]).is_file():
            raise HTTPException(404, "导出不存在、已过期或在修改文档后失效")
        return FileResponse(result["path"], filename=result["filename"], media_type="application/octet-stream")

    @app.post("/api/documents/{doc_id}/tasks")
    def tasks(doc_id: str, body: TaskRequest, request: Request):
        return extract_tasks(owned(doc_id, request), body.reference_date)

    @app.post("/api/calendar")
    def calendar(body: CalendarRequest, request: Request):
        owner(request)
        try:
            content = export_ics(body.tasks)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return Response(content, media_type="text/calendar; charset=utf-8", headers={"Content-Disposition": 'attachment; filename="shiye-calendar.ics"'})

    if settings.web_dir.exists():
        app.mount("/", StaticFiles(directory=settings.web_dir, html=True), name="web")
    else:
        @app.get("/")
        def unbuilt():
            return {"message": "前端未构建，请在 web 中运行 npm install && npm run build，然后重启服务", "api": "/api/docs"}
    return app


app = None if getattr(sys, "frozen", False) else create_app()
