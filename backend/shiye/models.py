from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


def uid() -> str:
    return uuid4().hex


class Block(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=uid, pattern=r"^[a-f0-9]{32}$")
    kind: Literal["title", "paragraph", "list", "table", "image", "formula"] = "paragraph"
    bbox: list[float] = Field(min_length=4, max_length=4)
    text: str = Field(default="", max_length=100_000)
    original_text: str = Field(default="", max_length=100_000)
    cells: list[list[str]] = Field(default_factory=list, max_length=100)
    confidence: float | None = None
    source: str = "manual"
    warning: str = ""
    latex: str = Field(default="", max_length=100_000)
    display: bool = True
    verified: bool = False

    @model_validator(mode="after")
    def valid_geometry(self):
        x0, y0, x1, y1 = self.bbox
        if not (0 <= x0 <= x1 <= 1 and 0 <= y0 <= y1 <= 1):
            raise ValueError("坐标须为有序的 0–1 归一化矩形")
        if any(len(row) > 50 or any(len(cell) > 10_000 for cell in row) for row in self.cells):
            raise ValueError("表格过大")
        if self.kind == "formula":
            value = (self.latex or self.text).strip()
            self.latex = value
            self.text = value
        return self


class Page(BaseModel):
    id: str = Field(default_factory=uid)
    source_name: str
    source_page: int
    width: int
    height: int
    rotation: int = 0
    status: Literal["pending", "processing", "ready", "failed"] = "pending"
    engine: str = ""
    error: str = ""
    blocks: list[Block] = Field(default_factory=list, max_length=2000)
    candidate_blocks: list[Block] | None = Field(default=None, max_length=500)
    candidate_engine: str = ""
    candidate_bbox: list[float] | None = None


class TaskItem(BaseModel):
    id: str = Field(default_factory=uid, pattern=r"^[a-f0-9]{32}$")
    title: str = Field(max_length=300)
    source_text: str = Field(max_length=5000)
    page_id: str
    date: str = ""
    time: str = ""
    location: str = ""
    kind: Literal["event", "deadline"] = "event"
    confirmed: bool = False
    note: str = "请核对日期和事项；未确认的条目不会进入日历。"


class Document(BaseModel):
    id: str = Field(default_factory=uid)
    title: str
    version: int = 1
    status: str = "uploaded"
    mode: str = "document"
    provider: Literal["local", "api"] = "local"
    target_pages: list[str] = Field(default_factory=list, max_length=20)
    target_bbox: list[float] | None = None
    created_at: str
    updated_at: str
    expires_at: str
    pages: list[Page]
    message: str = "等待开始识别"
    warnings: list[str] = Field(default_factory=list)
    tasks: list[TaskItem] = Field(default_factory=list, max_length=100)


class EditDocument(BaseModel):
    version: int
    title: str = Field(min_length=1, max_length=160)
    pages: list[Page] = Field(max_length=20)
    tasks: list[TaskItem] | None = Field(default=None, max_length=100)


class Transform(BaseModel):
    version: int
    rotate: Literal[0, 90, 180, 270] = 0
    crop: list[float] | None = None
    redactions: list[list[float]] = Field(default_factory=list, max_length=50)


class ExportRequest(BaseModel):
    version: int
    format: Literal["docx", "md", "txt", "pdf-image", "pdf-searchable", "json"]
