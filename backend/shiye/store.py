import json
import secrets
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import Document


def now() -> datetime:
    return datetime.now(timezone.utc)


class Conflict(Exception):
    pass


class Store:
    def __init__(self, settings):
        self.settings = settings
        settings.prepare()
        self.path = settings.data_dir / "shiye.sqlite3"
        with self.db() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, created TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY, owner TEXT NOT NULL, version INTEGER NOT NULL,
                status TEXT NOT NULL, expires TEXT NOT NULL, body TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS documents_owner ON documents(owner);
            CREATE TABLE IF NOT EXISTS exports (
                id TEXT PRIMARY KEY, document_id TEXT NOT NULL, version INTEGER NOT NULL,
                format TEXT NOT NULL, filename TEXT NOT NULL, path TEXT NOT NULL);
            """)

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA secure_delete=ON")
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def new_session(self):
        token = secrets.token_urlsafe(32)
        with self.db() as db:
            db.execute("INSERT INTO sessions VALUES (?, ?)", (token, now().isoformat()))
        return token

    def valid_session(self, token):
        if not token:
            return False
        with self.db() as db:
            return db.execute("SELECT 1 FROM sessions WHERE id=?", (token,)).fetchone() is not None

    def folder(self, doc_id: str) -> Path:
        # Never accept arbitrary paths, even from a stored record.
        if len(doc_id) != 32 or any(c not in "0123456789abcdef" for c in doc_id):
            raise ValueError("非法文档标识")
        folder = (self.settings.data_dir / "documents" / doc_id).resolve()
        if folder.parent != (self.settings.data_dir / "documents").resolve():
            raise ValueError("越界路径")
        return folder

    def create(self, doc, owner):
        with self.db() as db:
            db.execute("INSERT INTO documents VALUES (?,?,?,?,?,?)", (doc.id, owner, doc.version, doc.status, doc.expires_at, doc.model_dump_json()))

    def get(self, doc_id, owner=None):
        with self.db() as db:
            row = db.execute("SELECT * FROM documents WHERE id=?" + (" AND owner=?" if owner else ""), (doc_id, owner) if owner else (doc_id,)).fetchone()
        if not row or row["expires"] < now().isoformat():
            return None
        return Document.model_validate_json(row["body"])

    def list(self, owner):
        with self.db() as db:
            rows = db.execute("SELECT body FROM documents WHERE owner=? AND expires>? ORDER BY rowid DESC", (owner, now().isoformat())).fetchall()
        return [Document.model_validate_json(r[0]) for r in rows]

    def save(self, doc, expected_version):
        doc.version = expected_version + 1
        doc.updated_at = now().isoformat()
        with self.db() as db:
            changed = db.execute("UPDATE documents SET version=?,status=?,body=? WHERE id=? AND version=?", (doc.version, doc.status, doc.model_dump_json(), doc.id, expected_version)).rowcount
            if not changed:
                raise Conflict("文档已发生变化，请刷新后重试，避免覆盖校对结果。")
        return doc

    def pending(self):
        with self.db() as db:
            return [r[0] for r in db.execute("SELECT id FROM documents WHERE status='queued' AND expires>? ORDER BY rowid", (now().isoformat(),))]

    def recover(self):
        with self.db() as db:
            rows = db.execute("SELECT body FROM documents WHERE status IN ('processing','queued')").fetchall()
        for row in rows:
            doc = Document.model_validate_json(row[0])
            doc.status = "cancelled" if doc.provider == "api" else "queued"
            doc.message = "服务已恢复，请重新确认 API 发送范围；不会自动继续付费调用" if doc.provider == "api" else "服务已恢复，将继续未完成的页面"
            for page in doc.pages:
                if page.status == "processing":
                    page.status = "pending"
            self.save(doc, doc.version)

    def delete(self, doc_id, owner=None):
        with self.db() as db:
            query = "DELETE FROM documents WHERE id=?" + (" AND owner=?" if owner else "")
            changed = db.execute(query, (doc_id, owner) if owner else (doc_id,)).rowcount
            if changed:
                db.execute("DELETE FROM exports WHERE document_id=?", (doc_id,))
        if changed:
            folder = self.folder(doc_id)
            if folder.exists():
                shutil.rmtree(folder)
        return bool(changed)

    def cleanup(self):
        with self.db() as db:
            expired = [r[0] for r in db.execute("SELECT id FROM documents WHERE expires<?", (now().isoformat(),))]
        for doc_id in expired:
            self.delete(doc_id)
        with self.db() as db:
            db.execute("DELETE FROM sessions WHERE created<? AND id NOT IN (SELECT owner FROM documents)", ((now()-timedelta(days=30)).isoformat(),))

    def add_export(self, export_id, doc, fmt, filename, path):
        with self.db() as db:
            db.execute("INSERT INTO exports VALUES (?,?,?,?,?,?)", (export_id, doc.id, doc.version, fmt, filename, str(path)))

    def get_export(self, export_id, owner):
        with self.db() as db:
            row = db.execute("SELECT e.* FROM exports e JOIN documents d ON d.id=e.document_id WHERE e.id=? AND d.owner=? AND d.expires>?", (export_id, owner, now().isoformat())).fetchone()
        return dict(row) if row else None
