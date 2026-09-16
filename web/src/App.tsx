import { useEffect, useRef, useState } from "react";
import type { ChangeEvent, PointerEvent } from "react";
import FormulaCard from "./components/FormulaCard";
import RecognitionSettings from "./components/RecognitionSettings";
import { desktop, type RecognitionStatus } from "./desktop";
import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  BookOpen,
  Check,
  CheckCheck,
  ChevronRight,
  Clock3,
  Copy,
  Crop,
  Download,
  FileImage,
  FilePlus2,
  FileText,
  Files,
  History,
  ImagePlus,
  Info,
  Layers,
  LayoutGrid,
  LoaderCircle,
  LockKeyhole,
  Plus,
  RotateCw,
  ScanLine,
  Search,
  ShieldCheck,
  Sparkles,
  Sigma,
  Square,
  Trash2,
  UploadCloud,
  X,
  ZoomIn,
  ZoomOut,
  CalendarDays,
  Save,
  PanelRight,
  MoveUp,
  MoveDown,
  RefreshCw,
} from "lucide-react";
import { api, imageUrl, json } from "./api";
import type {
  Block,
  Doc,
  ExportFormat,
  HistoryItem,
  Kind,
  Task,
  FormulaStatus,
} from "./types";

const formats: {
  id: ExportFormat;
  name: string;
  tag: string;
  desc: string;
  icon: typeof FileText;
}[] = [
  {
    id: "docx",
    name: "Word 文档",
    tag: ".docx",
    desc: "可编辑文字与表格",
    icon: FileText,
  },
  {
    id: "md",
    name: "Markdown",
    tag: ".md / .zip",
    desc: "笔记、知识库直接用",
    icon: BookOpen,
  },
  {
    id: "pdf-searchable",
    name: "可搜索 PDF",
    tag: ".pdf",
    desc: "保留画面，增加文字层",
    icon: Search,
  },
  {
    id: "pdf-image",
    name: "图片合并 PDF",
    tag: ".pdf",
    desc: "不识别，直接整理成册",
    icon: Layers,
  },
  {
    id: "txt",
    name: "纯文本",
    tag: ".txt",
    desc: "只保留干净的文字",
    icon: FileText,
  },
  {
    id: "json",
    name: "结构化数据",
    tag: ".json",
    desc: "文字、坐标与校对版本",
    icon: LayoutGrid,
  },
];
const states: Record<string, string> = {
  uploaded: "待识别",
  queued: "排队中",
  processing: "识别中",
  ready_for_review: "待校对",
  partial: "部分完成",
  failed: "识别失败",
  cancelled: "已取消",
  completed: "已完成",
};
const kinds: Record<Kind, string> = {
  title: "标题",
  paragraph: "段落",
  list: "列表",
  table: "表格",
  image: "图片区域",
  formula: "数学公式",
};
const makeId = () => crypto.randomUUID().replaceAll("-", "");
const today = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

export default function App() {
  const [doc, setDoc] = useState<Doc | null>(null),
    [history, setHistory] = useState<HistoryItem[]>([]),
    [view, setView] = useState<"home" | "history" | "workspace">("home");
  const [files, setFiles] = useState<File[]>([]),
    [range, setRange] = useState(""),
    [merge, setMerge] = useState(false),
    [format, setFormat] = useState<ExportFormat>("docx"),
    [processingMode, setProcessingMode] = useState<"document" | "academic">("document");
  const [busy, setBusy] = useState(""),
    [notice, setNotice] = useState(""),
    [error, setError] = useState(""),
    [ready, setReady] = useState(false),
    [dirty, setDirty] = useState(false);
  const [pageId, setPageId] = useState(""),
    [blockId, setBlockId] = useState(""),
    [zoom, setZoom] = useState(100),
    [tab, setTab] = useState<"content" | "tasks">("content");
  const [drawing, setDrawing] = useState<
      "" | "crop" | "redact" | "image" | "paragraph" | "formula"
    >(""),
    [selection, setSelection] = useState<number[] | null>(null),
    [anchor, setAnchor] = useState<number[] | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]),
    [reference, setReference] = useState(today),
    [showHelp, setShowHelp] = useState(false),
    [licenseHtml, setLicenseHtml] = useState(""),
    [dragging, setDragging] = useState(false);
  const [formulaStatus, setFormulaStatus] = useState<FormulaStatus | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [provider, setProvider] = useState<"local" | "api">("local");
  const [cloudRequest, setCloudRequest] = useState<{ doc: Doc; settings: RecognitionStatus; page_ids: string[]; bbox?: number[] } | null>(null);
  const cloudDialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { if (cloudRequest) cloudDialog.current?.showModal(); }, [cloudRequest]);
  const [calendarDownload, setCalendarDownload] = useState("");
  const [exportResult, setExportResult] = useState<{
    url: string;
    filename: string;
    version: number;
    warnings: string[];
  } | null>(null);
  const input = useRef<HTMLInputElement>(null),
    imageRef = useRef<HTMLDivElement>(null);
  const helpDialog = useRef<HTMLDialogElement>(null);
  const [editorPane, setEditorPane] = useState<"both" | "source" | "content">("both");
  const page = doc?.pages.find((p) => p.id === pageId) || doc?.pages[0];
  const selected = page?.blocks.find((b) => b.id === blockId);
  const processing = doc?.status === "processing" || doc?.status === "queued";
  const completed = doc?.pages.filter((p) => p.status === "ready").length || 0;
  const workflowStep = exportResult ? 3 : processing || !completed ? 1 : 2;
  const refreshHistory = async () =>
    setHistory(await api<HistoryItem[]>("/documents"));

  useEffect(() => {
    if (showHelp) helpDialog.current?.showModal();
  }, [showHelp]);
  useEffect(() => {
    if (drawing) setEditorPane("source");
  }, [drawing]);
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "auto" });
  }, [view, doc?.id]);
  useEffect(() => {
    setCalendarDownload("");
  }, [tasks, doc?.id]);
  useEffect(() => {
    return () => { if (calendarDownload) URL.revokeObjectURL(calendarDownload); };
  }, [calendarDownload]);

  useEffect(() => {
    let alive = true;
    api("/session")
      .then(() => {
        if (alive) {
          setReady(true);
          void refreshHistory().catch((e) => setError(e.message));
          void api<FormulaStatus>("/formula/status")
            .then((status) => alive && setFormulaStatus(status))
            .catch(() => alive && setFormulaStatus(null));
        }
      })
      .catch((e) => setError(e.message));
    return () => {
      alive = false;
    };
  }, []);
  useEffect(() => {
    if (!doc || !processing) return;
    let alive = true;
    const id = setInterval(
      () =>
        api<Doc>(`/documents/${doc.id}`)
          .then((next) => {
            if (alive) {
              setDoc(next);
              if (next.status !== "processing" && next.status !== "queued")
                void refreshHistory();
            }
          })
          .catch((e) => {
            if (alive) setError(e.message);
          }),
      1400,
    );
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [doc?.id, processing]);
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => {
      if (dirty) {
        event.preventDefault();
        event.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  useEffect(() => {
    setSelection(null);
    setDrawing("");
    setBlockId("");
  }, [pageId, doc?.id]);
  useEffect(() => {
    if (blockId && tab === "content") {
      document.getElementById(`block-${blockId}`)?.scrollIntoView({block:"nearest", behavior:"smooth"});
    }
  }, [blockId, tab]);
  useEffect(() => {
    if (!notice) return;
    const id = setTimeout(() => setNotice(""), 7000);
    return () => clearTimeout(id);
  }, [notice]);
  useEffect(() => {
    const paste = (event: ClipboardEvent) => {
      if (view !== "home" || busy) return;
      const images = [...(event.clipboardData?.files || [])].filter(file => file.type.startsWith("image/"));
      if (images.length) { event.preventDefault(); addFiles(images); }
    };
    window.addEventListener("paste", paste);
    return () => window.removeEventListener("paste", paste);
  }, [view, busy]);

  async function run(label: string, fn: () => Promise<void>) {
    setBusy(label);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : "操作失败，请重试");
    } finally {
      setBusy("");
    }
  }
  function leave() {
    return !dirty || window.confirm("有尚未保存的校对内容，确定离开吗？");
  }
  function home() {
    if (leave()) {
      setView("home");
      setDoc(null);
      setDirty(false);
      setTasks([]);
      setExportResult(null);
    }
  }
  function install(next: Doc) {
    setDoc(next);
    setView("workspace");
    setPageId(next.pages[0]?.id || "");
    setBlockId("");
    setDirty(false);
    setTasks(next.tasks || []);
    setExportResult(null);
    setZoom(100);
    setEditorPane("both");
    setTab("content");
    setProcessingMode(next.mode === "academic" ? "academic" : "document");
  }
  async function openDocument(id: string) {
    if (!leave()) return;
    await run("打开文档", async () =>
      install(await api<Doc>(`/documents/${id}`)),
    );
  }
  function addFiles(incoming: File[]) {
    const valid = incoming.filter((f) =>
      /\.(png|jpe?g|webp|pdf)$/i.test(f.name),
    );
    if (valid.length !== incoming.length)
      setError("只支持 PNG、JPG、WebP、PDF，其他文件未加入。");
    setFiles((old) => [...old, ...valid].slice(0, 20));
  }
  function changeBlock(id: string, patch: Partial<Block>) {
    if (!doc || !page || processing) return;
    setDoc({
      ...doc,
      pages: doc.pages.map((p) =>
        p.id === page.id
          ? {
              ...p,
              blocks: p.blocks.map((b) =>
                b.id === id ? { ...b, ...patch } : b,
              ),
            }
          : p,
      ),
    });
    setDirty(true);
    setExportResult(null);
    setTasks([]);
  }
  function moveBlock(id: string, delta: number) {
    if (!doc || !page) return;
    const blocks = [...page.blocks],
      index = blocks.findIndex((b) => b.id === id),
      target = index + delta;
    if (target < 0 || target >= blocks.length) return;
    [blocks[index], blocks[target]] = [blocks[target], blocks[index]];
    setDoc({
      ...doc,
      pages: doc.pages.map((p) => (p.id === page.id ? { ...p, blocks } : p)),
    });
    setDirty(true);
    setExportResult(null);
  }
  function removeBlock(id: string) {
    if (!doc || !page) return;
    setDoc({
      ...doc,
      pages: doc.pages.map((p) =>
        p.id === page.id
          ? { ...p, blocks: p.blocks.filter((b) => b.id !== id) }
          : p,
      ),
    });
    setDirty(true);
    setExportResult(null);
    setBlockId("");
    setTasks([]);
  }
  function movePage(id: string, delta: number) {
    if (!doc) return;
    const pages = [...doc.pages],
      index = pages.findIndex((p) => p.id === id),
      target = index + delta;
    if (target < 0 || target >= pages.length) return;
    [pages[index], pages[target]] = [pages[target], pages[index]];
    setDoc({ ...doc, pages });
    setDirty(true);
    setExportResult(null);
  }
  async function save(): Promise<Doc> {
    if (!doc) throw Error("请先上传文档");
    if (!dirty) return doc;
    const next = await api<Doc>(
      `/documents/${doc.id}`,
      json("PUT", { version: doc.version, title: doc.title, pages: doc.pages, tasks }),
    );
    setDoc(next);
    setTasks(next.tasks || []);
    setDirty(false);
    setExportResult(null);
    return next;
  }
  async function uploadGroups(
    incoming: File[],
    options = { mode: processingMode, range, merge },
  ) {
    if (!incoming.length) throw Error("先选择图片或 PDF");
    if (incoming.reduce((n, f) => n + f.size, 0) > 50 * 1024 * 1024)
      throw Error("本次文件总大小超过 50 MB");
    const pdfs = incoming.filter((f) => /\.pdf$/i.test(f.name)),
      images = incoming.filter((f) => !/\.pdf$/i.test(f.name));
    const groups =
      options.merge || !pdfs.length
        ? [incoming]
        : [...pdfs.map((f) => [f]), ...(images.length ? [images] : [])];
    let last: Doc | null = null;
    for (const group of groups) {
      const form = new FormData();
      group.forEach((file) => form.append("files", file));
      form.append("page_range", options.range);
      form.append("merge", String(options.merge));
      form.append("mode", options.mode);
      last = await api<Doc>("/documents", { method: "POST", body: form });
    }
    if (last) {
      install(last);
      setFiles([]);
      await refreshHistory();
      if (groups.length > 1)
        setNotice(`已导入 ${groups.length} 份独立文档，可在“最近文档”中切换。`);
    }
  }
  async function loadExample(kind: "notice" | "formula" | "pdf") {
    const example = {
      notice: { path: "notice.png", name: "校园活动通知.png", type: "image/png" },
      formula: { path: "formula-page.png", name: "数学公式练习.png", type: "image/png" },
      pdf: { path: "native-text.pdf", name: "双页讲义.pdf", type: "application/pdf" },
    }[kind];
    const response = await fetch(`/examples/${example.path}`);
    if (!response.ok) throw Error("示例暂时无法读取，请选择自己的文件重试。");
    await uploadGroups([
      new File([await response.blob()], example.name, { type: example.type }),
    ], { mode: kind === "formula" ? "academic" : "document", range: "", merge: true });
    setFormat("docx");
    setNotice("示例已导入。点击“开始识别”，就能体验真实识别与校对。");
  }
  async function start() {
    const current = await save();
    if (provider === "api") { await requestCloud(current); return; }
    const next = await api<Doc>(
      `/documents/${current.id}/start`,
      json("POST", {
        version: current.version,
        mode: processingMode,
      }),
    );
    setDoc(next);
    setTasks([]);
    setExportResult(null);
  }
  async function requestCloud(current: Doc, bbox?: number[]) {
    const settings = await api<RecognitionStatus>("/recognition/status");
    if (!settings.configured || !settings.desktop) {
      setShowSettings(true);
      throw Error("先在识别设置中配置支持图片的 API，或切换回本地识别。");
    }
    setCloudRequest({ doc: current, settings, page_ids: bbox && page ? [page.id] : current.pages.map(p => p.id), bbox });
  }
  async function confirmCloud() {
    if (!cloudRequest) return;
    const next = await api<Doc>(`/documents/${cloudRequest.doc.id}/start`, json("POST", {
      version: cloudRequest.doc.version, provider: "api", consent: true,
      provider_revision: cloudRequest.settings.revision, page_ids: cloudRequest.page_ids,
      bbox: cloudRequest.bbox || null, mode: processingMode,
    }));
    setDoc(next); setCloudRequest(null); setDrawing(""); setSelection(null); setExportResult(null);
  }
  async function resolveCandidate(accept: boolean) {
    const current = await save();
    if (!page) return;
    setDoc(await api<Doc>(`/documents/${current.id}/pages/${page.id}/candidate`,
      json("POST", { version: current.version, accept })));
    setDirty(false); setExportResult(null); setTasks([]);
  }
  async function doExport() {
    const current = await save();
    const result = await api<{
      url: string;
      filename: string;
      version: number;
      warnings: string[];
    }>(
      `/documents/${current.id}/exports`,
      json("POST", { version: current.version, format }),
    );
    setExportResult(result);
    setNotice("导出文件已就绪，点击“下载文件”保存到电脑。");
  }
  async function transform(payload: Record<string, unknown>) {
    if (!doc || !page) return;
    if (
      page.blocks.length &&
      !window.confirm(
        "修改图像会清除本页识别内容和旧导出，需要重新识别。继续吗？",
      )
    )
      return;
    const current = await save();
    const next = await api<Doc>(
      `/documents/${current.id}/pages/${page.id}/transform`,
      json("POST", { version: current.version, ...payload }),
    );
    setDoc(next);
    setSelection(null);
    setDrawing("");
    setTasks([]);
    setExportResult(null);
  }
  function point(event: PointerEvent) {
    const rect = imageRef.current!.getBoundingClientRect();
    return [
      Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)),
      Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height)),
    ];
  }
  function drawStart(event: PointerEvent) {
    if (!drawing || processing) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    const p = point(event);
    setAnchor(p);
    setSelection([...p, ...p]);
  }
  function drawMove(event: PointerEvent) {
    if (!anchor) return;
    const p = point(event);
    setSelection([
      Math.min(p[0], anchor[0]),
      Math.min(p[1], anchor[1]),
      Math.max(p[0], anchor[0]),
      Math.max(p[1], anchor[1]),
    ]);
  }
  async function applySelection() {
    if (!selection || !doc || !page) return;
    if (
      selection[2] - selection[0] < 0.005 ||
      selection[3] - selection[1] < 0.005
    )
      throw Error("请拖拽选择一个区域");
    if (drawing === "crop") await transform({ crop: selection });
    else if (drawing === "redact") await transform({ redactions: [selection] });
    else if (drawing === "formula") {
      const current = await save();
      if (provider === "api") { await requestCloud(current, selection); return; }
      const next = await api<Doc>(
        `/documents/${current.id}/pages/${page.id}/formula/recognize`,
        json("POST", { version: current.version, bbox: selection }),
      );
      setDoc(next);
      const formulas = next.pages.find((p) => p.id === page.id)?.blocks.filter((b) => b.kind === "formula") || [];
      setBlockId(formulas.at(-1)?.id || "");
      setDirty(false);
      setDrawing("");
      setSelection(null);
      setExportResult(null);
      setNotice("公式已识别并排版。点击“对照 / 放大”检查符号，需要纠正时点击“修改公式”。");
    }
    else {
      const block: Block = {
        id: makeId(),
        kind: drawing === "image" ? "image" : "paragraph",
        bbox: selection,
        text: "",
        original_text: "",
        cells: [],
        confidence: null,
        source: "manual",
        warning: "",
        latex: "",
        display: true,
        verified: false,
      };
      setDoc({
        ...doc,
        pages: doc.pages.map((p) =>
          p.id === page.id ? { ...p, blocks: [...p.blocks, block] } : p,
        ),
      });
      setDirty(true);
      setExportResult(null);
      setBlockId(block.id);
      setDrawing("");
      setSelection(null);
    }
  }
  async function scanFormulas() {
    if (!doc || !page) return;
    const current = await save();
    const next = await api<Doc>(
      `/documents/${current.id}/pages/${page.id}/formula/scan`,
      json("POST", { version: current.version, min_score: 0.5 }),
    );
    setDoc(next);
    setDirty(false);
    setExportResult(null);
    setNotice(next.message);
  }
  async function extract() {
    const current = await save();
    setTasks(
      await api<Task[]>(
        `/documents/${current.id}/tasks`,
        json("POST", { reference_date: reference }),
      ),
    );
    setDirty(true);
    setNotice("已按通知关键词提取候选事项，请逐条补全并确认。");
  }
  async function calendar() {
    await save();
    const response = await fetch("/api/calendar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tasks }),
    });
    if (!response.ok) {
      const body = await response.json();
      throw Error(body.detail);
    }
    const url = URL.createObjectURL(await response.blob());
    setCalendarDownload(url);
    const a = document.createElement("a");
    a.href = url;
    a.download = "识页-待办日历.ics";
    document.body.appendChild(a);
    a.click();
    a.remove();
    setNotice(
      "日历文件已生成；若未自动下载，请点击“下载日历 .ics”。文件需手动导入日历，不会自动创建提醒。",
    );
  }
  function editTask(index: number, patch: Partial<Task>) {
    setTasks(
      tasks.map((t, i) =>
        i === index
          ? { ...t, ...patch, confirmed: patch.confirmed ?? false }
          : t,
      ),
    );
    setDirty(true);
    setExportResult(null);
  }
  const iconButton = (
    title: string,
    Icon: typeof X,
    action: () => void,
    disabled = false,
  ) => (
    <button
      className="icon-btn"
      title={title}
      aria-label={title}
      onClick={action}
      disabled={disabled}
    >
      <Icon size={16} />
    </button>
  );

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <button className="brand" onClick={home} aria-label="识页首页">
          <span className="brand-mark">
            <ScanLine size={25} />
          </span>
          <span>
            识页<small>SHIYE</small>
          </span>
        </button>
        <div className="sidebar-label">你的文档工作台</div>
        <nav>
          <button aria-label="新建转换" className={view !== "history" ? "active" : ""} onClick={home}>
            <FilePlus2 size={18} />
            新建转换<span className="keycap">＋</span>
          </button>
          <button
            aria-label="最近文档"
            className={view === "history" ? "active" : ""}
            onClick={() => {
              if (leave()) {
                setDirty(false);
                setView("history");
                void refreshHistory().catch((e) => setError(e.message));
              }
            }}
          >
            <History size={18} />
            最近文档<span className="count">{history.length}</span>
          </button>
        </nav>
        <div className="sidebar-label recent-heading">最近使用</div>
        <div className="recent-list">
          {history.slice(0, 5).map((item) => (
            <button
              key={item.id}
              className={
                item.id === doc?.id && view === "workspace" ? "selected" : ""
              }
              onClick={() => void openDocument(item.id)}
            >
              <FileText size={15} />
              <span>{item.title}</span>
            </button>
          ))}
          {!history.length && (
            <p>
              导入第一份文件后
              <br />
              就会出现在这里
            </p>
          )}
        </div>
        <div className="sidebar-bottom">
          <div className="local-card">
            <span className="local-dot" />
            <strong>本机识别引擎</strong>
            <p>
              不需要 API 密钥
              <br />
              校对一次，自由导出
            </p>
            <span className="mini-pill">RapidOCR · CPU</span>
            <span className={`mini-pill formula-pill ${formulaStatus?.available ? "ready" : ""}`}>
              {formulaStatus?.available ? "PP-FormulaNet · 就绪" : formulaStatus ? "公式增强 · 未安装" : "公式引擎 · 检测中"}
            </span>
          </div>
          <button className="help-link" onClick={() => setShowHelp(true)}>
            <Info size={16} />
            使用指引与隐私说明
            <ChevronRight size={14} />
          </button>
          <div className="sidebar-footer">
            AIAADC · 学生项目<span>v0.3.1</span>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            <span>工作台</span>
            <ChevronRight size={14} />
            <strong>
              {view === "home"
                ? "新建转换"
                : view === "history"
                  ? "最近文档"
                  : doc?.title}
            </strong>
          </div>
          <div className="top-right">
            <button className="top-help" onClick={() => setShowSettings(true)}><ShieldCheck size={16} />识别设置</button>
            <span className="local-indicator">
              <span /> {provider === "api" ? "API 模式 · 发送前确认" : "本地识别 · 不发送至 API"}
            </span>
            <button className="top-help" onClick={() => setShowHelp(true)}>
              <BookOpen size={16} /> 使用指南
            </button>
          </div>
        </header>
        <main
          className={view === "workspace" ? "workspace-main" : "main-content"}
        >
          {error && (
            <div className="banner error" role="alert">
              <Info size={18} />
              <span>{error}</span>
              <button onClick={() => setError("")} aria-label="关闭错误">
                <X size={16} />
              </button>
              {doc && (
                <button
                  className="text-btn"
                  onClick={() =>
                    void run("刷新文档", async () =>
                      install(await api<Doc>(`/documents/${doc.id}`)),
                    )
                  }
                >
                  重新加载
                </button>
              )}
            </div>
          )}
          {notice && (
            <div className="banner success" role="status">
              <Check size={18} />
              <span>{notice}</span>
              <button onClick={() => setNotice("")} aria-label="关闭提示">
                <X size={16} />
              </button>
            </div>
          )}
          {view === "home" && (
            <>
              <section className="hero">
                <div className="eyebrow">
                  <span /> 识页 · 你的学习资料转换台
                </div>
                <h1>
                  把图片，变成<span>可用的文档。</span>
                </h1>
                <p>
                  课本、论文、课堂截图，都能继续编辑。
                  <br className="desktop-break" />
                  提取文字与公式，校对后带走 Word、Markdown 或 PDF。
                </p>
                <div className="hero-pills">
                  <span>
                    <ShieldCheck size={15} /> 本机处理
                  </span>
                  <span>
                    <CheckCheck size={15} /> 无需注册
                  </span>
                  <span>
                    <Layers size={15} /> 一次识别，多种导出
                  </span>
                </div>
                <div className="hero-art" aria-hidden="true">
                  <div className="art-page art-source">
                    <div className="art-badge">IMG</div>
                    <i />
                    <i />
                    <i />
                    <div className="art-table">
                      <b />
                      <b />
                      <b />
                      <b />
                    </div>
                    <div className="scan-line" />
                  </div>
                  <div className="art-arrow">
                    <ArrowRight size={23} />
                  </div>
                  <div className="art-page art-output">
                    <div className="art-badge green">DOC</div>
                    <strong>让内容自由流动</strong>
                    <i />
                    <i />
                    <i />
                    <span>
                      <Check size={11} /> 可编辑文字
                    </span>
                  </div>
                  <div className="art-star">✦</div>
                </div>
              </section>
              <ol className="workflow home-workflow" aria-label="使用流程">
                {[
                  ["导入文件", "图片或 PDF"],
                  ["开始识别", "普通文档 / 学术公式"],
                  ["对照校对", "文字、表格与公式"],
                  ["导出下载", "任选需要的格式"],
                ].map(([title, detail], index) => (
                  <li key={title} className={index === 0 ? "current" : ""}>
                    <span className="workflow-number">{index + 1}</span>
                    <span><strong>{title}</strong><small>{detail}</small></span>
                    {index < 3 && <ChevronRight size={16} />}
                  </li>
                ))}
              </ol>
              <section className="create-card" aria-label="创建文档转换">
                <div className="section-head">
                  <h2>
                    <span className="step">01</span>导入你的文件
                  </h2>
                  <span>最多 20 页 · 合计 50 MB</span>
                </div>
                <div
                  className={`dropzone ${dragging ? "dragging" : ""}`}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDragging(true);
                  }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setDragging(false);
                    addFiles([...e.dataTransfer.files]);
                  }}
                >
                  <span className="upload-icon">
                    <UploadCloud size={30} strokeWidth={1.5} />
                  </span>
                  <h3>把图片或 PDF 放到这里</h3>
                  <p>拖拽上传，或直接粘贴截图（Ctrl / ⌘ + V）</p>
                  <button
                    className="primary"
                    onClick={() => input.current?.click()}
                    disabled={!!busy || !ready}
                  >
                    <Plus size={17} />
                    选择文件
                  </button>
                  <small className="upload-types">PNG · JPG · WebP · PDF</small>
                  <input
                    ref={input}
                    type="file"
                    multiple
                    accept=".png,.jpg,.jpeg,.webp,.pdf"
                    onChange={(e: ChangeEvent<HTMLInputElement>) => {
                      addFiles([...(e.target.files || [])]);
                      e.target.value = "";
                    }}
                    hidden
                  />
                </div>
                {!files.length && (
                  <div className="sample-shelf">
                    <div><strong>第一次来？先试一份示例</strong><small>真实识别流程，无需准备文件</small></div>
                    <div className="sample-options">
                      <button className="sample-choice" disabled={!!busy || !ready}
                        aria-label="用示例体验一下：校园通知"
                        onClick={() => void run("载入通知示例", () => loadExample("notice"))}>
                        <CalendarDays size={18} /><span>校园通知<small>文字 + 表格 + 待办</small></span><ArrowRight size={15} />
                      </button>
                      <button className="sample-choice formula-sample" disabled={!!busy || !ready || !formulaStatus?.available}
                        onClick={() => void run("载入公式示例", () => loadExample("formula"))}>
                        <Sigma size={19} /><span>数学公式<small>{formulaStatus?.available ? "积分 + 矩阵 · 耗时较长" : "需安装公式引擎"}</small></span><ArrowRight size={15} />
                      </button>
                      <button className="sample-choice" disabled={!!busy || !ready}
                        onClick={() => void run("载入 PDF 示例", () => loadExample("pdf"))}>
                        <Files size={18} /><span>双页讲义<small>原生 PDF · 快速体验</small></span><ArrowRight size={15} />
                      </button>
                    </div>
                  </div>
                )}
                {files.length > 0 && (
                  <div className="file-queue">
                    {files.map((file, index) => (
                      <div
                        className="queued-file"
                        key={`${file.name}-${index}`}
                      >
                        <FileImage size={18} />
                        <span>
                          <strong>{file.name}</strong>
                          <small>
                            {(file.size / 1024 / 1024).toFixed(2)} MB
                          </small>
                        </span>
                        {iconButton(
                          "文件上移",
                          ArrowUp,
                          () =>
                            setFiles((old) => {
                              const next = [...old];
                              [next[index], next[index - 1]] = [
                                next[index - 1],
                                next[index],
                              ];
                              return next;
                            }),
                          index === 0,
                        )}
                        {iconButton(
                          "文件下移",
                          ArrowDown,
                          () =>
                            setFiles((old) => {
                              const next = [...old];
                              [next[index], next[index + 1]] = [
                                next[index + 1],
                                next[index],
                              ];
                              return next;
                            }),
                          index === files.length - 1,
                        )}
                        {iconButton("移除文件", X, () =>
                          setFiles((old) => old.filter((_, i) => i !== index)),
                        )}
                      </div>
                    ))}
                    <div className="upload-options">
                      <label>
                        PDF 页码
                        <input
                          aria-label="PDF 页码"
                          placeholder="全部，或 1-3,5"
                          value={range}
                          onChange={(e) => setRange(e.target.value)}
                        />
                      </label>
                      <label className="checkbox">
                        <input
                          type="checkbox"
                          checked={merge}
                          onChange={(e) => setMerge(e.target.checked)}
                        />
                        将多个 PDF / 图片合为一份文档
                      </label>
                    </div>
                  </div>
                )}
                <div className="section-head mode-heading">
                  <h2>
                    <span className="step">02</span>选择识别方式
                  </h2>
                  <span>论文、课本建议使用学术公式模式</span>
                </div>
                <div className="mode-grid" role="radiogroup" aria-label="识别方式">
                  <button
                    className={`mode-card ${processingMode === "document" ? "chosen" : ""}`}
                    role="radio"
                    aria-checked={processingMode === "document"}
                    onClick={() => setProcessingMode("document")}
                  >
                    <ScanLine size={22} />
                    <span>
                      <strong>普通文档</strong>
                      <small>中文、英文、通知、简单表格；速度更快</small>
                    </span>
                    <i>{processingMode === "document" && <Check size={11} />}</i>
                  </button>
                  <button
                    className={`mode-card academic ${processingMode === "academic" ? "chosen" : ""}`}
                    role="radio"
                    aria-checked={processingMode === "academic"}
                    disabled={formulaStatus !== null && !formulaStatus.available}
                    onClick={() => setProcessingMode("academic")}
                  >
                    <Sigma size={22} />
                    <span>
                      <strong>学术公式</strong>
                      <small>
                        {formulaStatus?.available
                          ? "识别正文与公式 · 直接阅读、可视化修改"
                          : "需先安装本机公式增强环境"}
                      </small>
                    </span>
                    <i>{processingMode === "academic" && <Check size={11} />}</i>
                  </button>
                </div>
                {processingMode === "academic" && (
                  <p className="mode-advice"><Info size={16} /> 学术模式适合印刷公式，CPU 处理可能需要数分钟。识别后请核对上下标、字母和矩阵元素。</p>
                )}
                <div className="section-head format-heading">
                  <h2>
                    <span className="step">03</span>你想得到什么？
                  </h2>
                  <span>稍后仍可切换格式</span>
                </div>
                <div className="format-grid" role="group" aria-label="目标文件格式">
                  {formats.slice(0, 5).map((f) => (
                    <button
                      key={f.id}
                      className={`format-card ${format === f.id ? "chosen" : ""}`}
                      aria-pressed={format === f.id}
                      onClick={() => setFormat(f.id)}
                    >
                      <span className={`format-icon ${f.id}`}>
                        <f.icon size={22} />
                      </span>
                      <strong>{f.name}</strong>
                      <small>{f.desc}</small>
                      <span className="radio-dot">
                        {format === f.id && <Check size={10} />}
                      </span>
                    </button>
                  ))}
                </div>
                <p className="format-advice"><Info size={15} />
                  {format === "docx" ? "想继续修改内容？选 Word。文字与表格可编辑，公式可导出为 Word 公式；不是原版面复刻。"
                    : format === "md" ? "想整理笔记？选 Markdown。保留 LaTeX 公式；含图片时会一起打包为 ZIP。"
                    : format === "pdf-searchable" ? "想保留扫描件外观，又能搜索文字？选可搜索 PDF。可见画面仍是原图。"
                    : format === "pdf-image" ? "只想把图片装订成 PDF？导入后直接导出即可，无需等待识别。"
                    : "只需要复制文字？选纯文本。不保留排版和图片。"}
                </p>
                <div className="create-footer">
                  <p>
                    <LockKeyhole size={15} />
                    {files.length ? `已选 ${files.length} 个文件 · 下一步：导入后开始识别` : "请选择文件，或使用上方示例体验"}
                  </p>
                  <button
                    className="primary"
                    disabled={!files.length || !!busy || !ready}
                    onClick={() =>
                      void run("正在导入文件", () => uploadGroups(files))
                    }
                  >
                    {busy ? (
                      <LoaderCircle className="spin" size={17} />
                    ) : (
                      <ArrowRight size={17} />
                    )}{" "}
                    {busy || "导入并整理"}
                  </button>
                </div>
              </section>
              <section className="use-cases">
                <div>
                  <span className="eyebrow">MADE FOR YOUR EVERYDAY</span>
                  <h2>
                    不止识字，
                    <br />
                    更是把事情往前推进一步。
                  </h2>
                </div>
                <article>
                  <span className="case-icon amber">
                    <BookOpen size={21} />
                  </span>
                  <h3>讲义变笔记</h3>
                  <p>
                    拍下课程重点，整理成 Markdown
                    <br />
                    放回自己的知识库。
                  </p>
                </article>
                <article>
                  <span className="case-icon blue">
                    <FileText size={21} />
                  </span>
                  <h3>扫描件变文档</h3>
                  <p>
                    从不可编辑的图片里
                    <br />
                    拿回文字和简单表格。
                  </p>
                </article>
                <article>
                  <span className="case-icon green">
                    <CalendarDays size={21} />
                  </span>
                  <h3>通知变待办</h3>
                  <p>
                    从群聊里提取候选事项
                    <br />
                    确认日期，再放进日历。
                  </p>
                </article>
                <article>
                  <span className="case-icon violet">
                    <Sigma size={21} />
                  </span>
                  <h3>公式，看得懂也改得动</h3>
                  <p>
                    自动寻找论文与课本公式
                    <br />
                    校对后导出 Markdown / Word。
                  </p>
                </article>
              </section>
              <footer className="page-footer">
                <span>每一页，都值得被好好使用。</span>
                <button onClick={() => setShowHelp(true)}>
                  识别能力与使用说明 <ArrowRight size={13} />
                </button>
              </footer>
            </>
          )}
          {view === "history" && (
            <section className="history-screen">
              <div className="history-title">
                <div className="eyebrow">YOUR RECENT DOCUMENTS</div>
                <h1>最近文档</h1>
                <p>
                  当前浏览器会话可见；文件默认在上传 24 小时后清理。清除浏览器
                  Cookie 后将无法重新访问。
                </p>
              </div>
              <div className="history-grid">
                {history.map((item) => (
                  <article className="history-card" key={item.id}>
                    <FileText size={28} />
                    <h3>{item.title}</h3>
                    <span className={`status ${item.status}`}>
                      {states[item.status] || item.status}
                    </span>
                    <p>
                      {item.pages} 页 ·{" "}
                      {new Date(item.created_at).toLocaleString("zh-CN")}
                    </p>
                    <small>
                      到期：{new Date(item.expires_at).toLocaleString("zh-CN")}
                    </small>
                    <div>
                      <button
                        className="secondary"
                        onClick={() => void openDocument(item.id)}
                      >
                        打开文档 <ArrowRight size={15} />
                      </button>
                      {iconButton("彻底删除文档", Trash2, () => {
                        if (
                          window.confirm(
                            `彻底删除“${item.title}”？图片、识别内容及导出文件将一并删除，不能恢复。`,
                          )
                        )
                          void run("删除文档", async () => {
                            await api(`/documents/${item.id}`, {
                              method: "DELETE",
                            });
                            await refreshHistory();
                            if (doc?.id === item.id) setDoc(null);
                            setNotice("文档及关联文件已彻底删除。");
                          });
                      })}
                    </div>
                  </article>
                ))}
                {!history.length && (
                  <div className="empty-state">
                    <History size={35} />
                    <h3>这里还没有文档</h3>
                    <p>从一份图片或 PDF 开始吧。</p>
                    <button className="primary" onClick={home}>
                      新建转换 <Plus size={15} />
                    </button>
                  </div>
                )}
              </div>
            </section>
          )}
          {view === "workspace" && doc && page && (
            <>
              <div className="workspace-header">
                <div className="workspace-title">
                  <button
                    className="icon-btn"
                    aria-label="返回首页"
                    onClick={home}
                  >
                    <ArrowLeft size={18} />
                  </button>
                  <input
                    aria-label="文档名称"
                    value={doc.title}
                    maxLength={160}
                    disabled={processing || !!busy}
                    onChange={(e) => {
                      setDoc({ ...doc, title: e.target.value });
                      setDirty(true);
                      setExportResult(null);
                    }}
                  />
                  <span className={`status ${doc.status}`}>
                    {states[doc.status]}
                  </span>
                </div>
                <div className="workspace-actions">
                  {desktop && <select aria-label="识别引擎" className="mode-select" value={provider} disabled={processing || !!busy}
                    onChange={event => setProvider(event.target.value as "local" | "api")}>
                    <option value="local">本地识别</option><option value="api">自己的 API</option>
                  </select>}
                  <select
                    className="mode-select"
                    aria-label="识别方式"
                    value={processingMode}
                    disabled={processing || !!busy}
                    onChange={(e) => setProcessingMode(e.target.value as "document" | "academic")}
                  >
                    <option value="document">普通文档</option>
                    <option value="academic" disabled={provider === "local" && formulaStatus !== null && !formulaStatus.available}>
                      学术公式
                    </option>
                  </select>
                  <span className="save-state">
                    {dirty ? "● 未保存" : `v${doc.version} · 已保存`}
                  </span>
                  <button
                    className="secondary"
                    disabled={!dirty || !!busy || processing}
                    onClick={() =>
                      void run("保存校对", async () => {
                        await save();
                        setNotice("校对内容已保存。");
                      })
                    }
                  >
                    <Save size={15} />
                    保存
                  </button>
                  {processing ? (
                    <button
                      className="secondary danger-text"
                      onClick={() =>
                        void run("取消识别", async () =>
                          setDoc(
                            await api<Doc>(`/documents/${doc.id}/cancel`, {
                              method: "POST",
                            }),
                          ),
                        )
                      }
                    >
                      取消识别
                    </button>
                  ) : (
                    <button
                      className="primary"
                      disabled={!!busy || (provider === "local" && completed === doc.pages.length)}
                      onClick={() => void run("加入识别队列", start)}
                    >
                      <ScanLine size={16} />
                      {completed ? "继续 / 重试未完成页" : "开始识别"}
                    </button>
                  )}
                </div>
              </div>
              <ol className="workflow workspace-workflow" aria-label="当前转换进度">
                {["导入文件", "开始识别", "对照校对", "导出下载"].map((title, index) => (
                  <li key={title} className={index < workflowStep ? "done" : index === workflowStep ? "current" : ""}
                    aria-current={index === workflowStep ? "step" : undefined}>
                    <span className="workflow-number">{index < workflowStep ? <Check size={14} /> : index + 1}</span>
                    <strong>{title}</strong>{index < 3 && <ChevronRight size={15} />}
                  </li>
                ))}
              </ol>
              <div className="next-step">
                {processing ? <LoaderCircle size={20} className="spin" /> : <Info size={20} />}
                <div>
                  <strong>{exportResult ? "文件已生成，点击“下载文件”保存到电脑。" : processing ? "正在识别，完成后会自动显示结果。" : format === "pdf-image" ? "只合并图片？现在就可以前往导出。" : completed ? "接下来：对照原图校对，再生成导出文件。" : "文件已就位：点击上方“开始识别”。"}</strong>
                  <p>{processing ? (processingMode === "academic" ? "学术模式在 CPU 上可能需要数分钟。你可以查看原图，也可以取消识别。" : "正在处理文档，不需要重复点击；完成后可直接编辑识别内容。") : completed ? "数字、英文空格、上下标和矩阵元素请重点检查。导出会自动保存当前校对内容。" : "可先旋转、裁剪或遮盖敏感内容。普通文档更快；论文、课本中的公式请选择学术模式。"}</p>
                </div>
                {!processing && (completed > 0 || format === "pdf-image") && <a href="#export-panel">前往导出 <ArrowDown size={15} /></a>}
              </div>
              <div className={`job-strip ${processing ? "working" : ""}`}>
                <span>
                  {processing ? (
                    <LoaderCircle size={15} className="spin" />
                  ) : (
                    <Info size={15} />
                  )}{" "}
                  {doc.message}
                </span>
                <span>
                  {completed} / {doc.pages.length} 页完成{" "}
                  <span className="progress-track">
                    <i
                      style={{
                        width: `${(completed / doc.pages.length) * 100}%`,
                      }}
                    />
                  </span>
                </span>
              </div>
              <div className="editor-pane-nav" role="group" aria-label="手机阅读视图">
                {([ ["both", "对照阅读"], ["source", "只看原图"], ["content", "只看校对"] ] as const).map(([value, label]) => (
                  <button key={value} aria-pressed={editorPane === value} onClick={() => setEditorPane(value)}>{label}</button>
                ))}
              </div>
              <div className={`editor-layout mobile-${editorPane}`}>
                <aside className="page-rail">
                  <div className="rail-title">
                    页面 <span>{doc.pages.length}</span>
                  </div>
                  {doc.pages.map((p, index) => (
                    <div
                      className={`page-thumb ${p.id === page.id ? "current" : ""}`}
                      key={p.id}
                    >
                      <button
                        className="thumb-open"
                        aria-label={`选择第 ${index + 1} 页`}
                        onClick={() => setPageId(p.id)}
                      >
                        <img
                          src={imageUrl(doc.id, p.id, doc.version)}
                          alt={`第 ${index + 1} 页预览`}
                        />
                        <span>
                          {index + 1}
                          <i className={p.status} />
                        </span>
                      </button>
                      <div className="page-tools">
                        {iconButton(
                          "页面上移",
                          ArrowUp,
                          () => movePage(p.id, -1),
                          index === 0 || processing || !!busy,
                        )}
                        {iconButton(
                          "页面下移",
                          ArrowDown,
                          () => movePage(p.id, 1),
                          index === doc.pages.length - 1 ||
                            processing ||
                            !!busy,
                        )}
                        {iconButton(
                          "移除这一页",
                          X,
                          () => {
                            if (
                              window.confirm("移除本页？保存后会删除该页图像。")
                            ) {
                              setDoc({
                                ...doc,
                                pages: doc.pages.filter((x) => x.id !== p.id),
                              });
                              setDirty(true);
                              setExportResult(null);
                            }
                          },
                          doc.pages.length <= 1 || processing || !!busy,
                        )}
                      </div>
                    </div>
                  ))}
                </aside>
                <section className="source-panel">
                  <div className="panel-toolbar">
                    <strong>
                      <FileImage size={15} />
                      原图
                    </strong>
                    <div>
                      {iconButton(
                        "缩小",
                        ZoomOut,
                        () => setZoom((v) => Math.max(60, v - 20)),
                        zoom <= 60,
                      )}
                      <span className="zoom-label">{zoom}%</span>
                      {iconButton(
                        "放大",
                        ZoomIn,
                        () => setZoom((v) => Math.min(200, v + 20)),
                        zoom >= 200,
                      )}
                      <span className="tool-divider" />
                      {iconButton(
                        "顺时针旋转 90 度",
                        RotateCw,
                        () =>
                          void run("旋转页面", () => transform({ rotate: 90 })),
                        processing || !!busy,
                      )}
                      {iconButton(
                        "选择裁剪区域",
                        Crop,
                        () => {
                          setDrawing(drawing === "crop" ? "" : "crop");
                          setSelection(null);
                        },
                        processing || !!busy,
                      )}
                      {iconButton(
                        "遮盖敏感内容",
                        Square,
                        () => {
                          setDrawing(drawing === "redact" ? "" : "redact");
                          setSelection(null);
                        },
                        processing || !!busy,
                      )}
                    </div>
                  </div>
                  {drawing && (
                    <div className="drawing-hint">
                      <span>
                        {drawing === "crop"
                          ? "拖拽框选要保留的区域"
                          : drawing === "redact"
                            ? "框选要永久遮盖的敏感内容"
                            : drawing === "image"
                              ? "框选要作为图片导出的区域"
                              : drawing === "formula"
                                ? "尽量贴紧公式边缘框选；首次识别会加载本机模型"
                                : "框选新文字对应的原图区域"}
                      </span>
                      <button
                        className="text-btn"
                        disabled={!selection || !!busy}
                        onClick={() => void run("应用区域", applySelection)}
                      >
                        {drawing === "formula" ? "识别公式" : "应用"}
                      </button>
                      <button
                        className="icon-btn"
                        aria-label="取消框选"
                        onClick={() => {
                          setDrawing("");
                          setSelection(null);
                        }}
                      >
                        <X size={14} />
                      </button>
                    </div>
                  )}
                  <div className="image-scroller">
                    <div
                      className={`page-image ${drawing ? "drawing" : ""}`}
                      ref={imageRef}
                      style={{ width: `${zoom}%` }}
                      onPointerDown={drawStart}
                      onPointerMove={drawMove}
                      onPointerUp={() => setAnchor(null)}
                      onPointerCancel={() => setAnchor(null)}
                    >
                      <img
                        src={imageUrl(doc.id, page.id, doc.version)}
                        alt="当前页面原图"
                        draggable={false}
                      />
                      {!drawing &&
                        page.blocks.filter(block => block.source !== "cloud-page").map((block, index) => (
                          <button
                            key={block.id}
                            className={`ocr-box ${block.kind} ${block.id === blockId ? "selected" : ""} ${block.warning ? "uncertain" : ""}`}
                            style={{
                              left: `${block.bbox[0] * 100}%`,
                              top: `${block.bbox[1] * 100}%`,
                              width: `${(block.bbox[2] - block.bbox[0]) * 100}%`,
                              height: `${(block.bbox[3] - block.bbox[1]) * 100}%`,
                            }}
                            aria-label={`校对内容块 ${index + 1}`}
                            onClick={() => {
                              setBlockId(block.id);
                              setTab("content");
                            }}
                          >
                            <span>{index + 1}</span>
                          </button>
                        ))}
                      {selection && (
                        <div
                          className={`selection-box ${drawing === "redact" ? "redaction" : drawing === "formula" ? "formula" : ""}`}
                          style={{
                            left: `${selection[0] * 100}%`,
                            top: `${selection[1] * 100}%`,
                            width: `${(selection[2] - selection[0]) * 100}%`,
                            height: `${(selection[3] - selection[1]) * 100}%`,
                          }}
                        />
                      )}
                    </div>
                  </div>
                  <div className="source-footer">
                    <span>
                      {page.width} × {page.height} px
                    </span>
                    <span>
                      {page.engine || "等待识别"} · 原文件第 {page.source_page}{" "}
                      页
                    </span>
                  </div>
                </section>
                <section className="content-panel">
                  <div className="content-tabs">
                    <button
                      className={tab === "content" ? "active" : ""}
                      onClick={() => setTab("content")}
                    >
                      <PanelRight size={15} />
                      内容校对 <span>{page.blocks.length}</span>
                    </button>
                    <button
                      className={tab === "tasks" ? "active" : ""}
                      onClick={() => setTab("tasks")}
                    >
                      <CalendarDays size={15} />
                      通知转待办
                    </button>
                  </div>
                  {tab === "content" ? (
                    <>
                      <div className="content-tip">
                        点击左侧识别框，或直接选择内容块。数字、姓名、日期请重点核对。
                      </div>
                      <div className={`formula-toolbar ${formulaStatus?.available ? "ready" : "unavailable"}`}>
                        <span>
                          <Sigma size={17} />
                          <span>
                            <strong>公式增强</strong>
                            <small>
                              {formulaStatus?.available
                                ? `${formulaStatus.model} · ${formulaStatus.device.toUpperCase()} · 本机`
                                : "未安装；普通 OCR 仍可正常使用"}
                            </small>
                          </span>
                        </span>
                        <div>
                          <button
                            className="secondary"
                            disabled={processing || !!busy || (provider === "local" && !formulaStatus?.available)}
                            onClick={() => void run("正在扫描本页公式", provider === "api" ? async () => { const current = await save(); await requestCloud(current); } : scanFormulas)}
                          >
                            <Sparkles size={14} /> 自动找本页公式
                          </button>
                          <button
                            className="secondary"
                            disabled={processing || !!busy || (provider === "local" && !formulaStatus?.available)}
                            onClick={() => {
                              setDrawing(drawing === "formula" ? "" : "formula");
                              setSelection(null);
                            }}
                          >
                            <Sigma size={14} /> 框选识别
                          </button>
                        </div>
                      </div>
                      <div className="blocks-scroll">
                        {page.candidate_blocks && !processing && <section className="api-candidate">
                          <span className="eyebrow">API RESULT · REVIEW FIRST</span>
                          <h3>先审阅，再采用</h3>
                          <p>模型：{page.candidate_engine}。原内容仍保留在下方。{page.candidate_bbox ? "采用后更新框选公式。" : "采用会替换本页现有内容；不确定时选择保留原内容。"}</p>
                          <div className="candidate-preview">
                            {page.candidate_blocks.map((block, index) => block.kind === "formula" ?
                              <FormulaCard key={block.id} block={block} number={index + 1} imageSrc={imageUrl(doc.id, page.id, doc.version)} disabled={true} onChange={() => {}} onRetry={() => {}} /> :
                              block.kind === "table" ? <table key={block.id}><tbody>{block.cells.map((row, i) => <tr key={i}>{row.map((cell, j) => <td key={j}>{cell}</td>)}</tr>)}</tbody></table> :
                              <p key={block.id}>{block.text}</p>)}
                          </div>
                          <div className="recognition-actions">
                            <button className="primary" disabled={!!busy} onClick={() => void run("采用候选", () => resolveCandidate(true))}>采用{page.candidate_bbox ? "框选公式" : "并替换本页"}</button>
                            <button disabled={!!busy} onClick={() => void run("保留原内容", () => resolveCandidate(false))}>保留原内容，丢弃候选</button>
                          </div>
                        </section>}
                        {page.error && (
                          <div className="inline-warning">{page.error}</div>
                        )}
                        {!page.blocks.length ? (
                          <div className="empty-editor">
                            {processing ? (
                              <LoaderCircle size={32} className="spin" />
                            ) : (
                              <ScanLine size={34} />
                            )}
                            <h3>
                              {processing
                                ? "正在把图像变成文字"
                                : "这页还没有识别内容"}
                            </h3>
                            <p>
                              {processing
                                ? "完成后会显示带坐标的内容块。"
                                : "先旋转、裁剪或遮盖敏感内容，再点击“开始识别”。图片合并 PDF 可以直接导出。"}
                            </p>
                          </div>
                        ) : (
                          page.blocks.map((block, index) => (
                            <article
                              key={block.id}
                              id={`block-${block.id}`}
                              className={`block-card ${block.id === blockId ? "selected" : ""}`}
                              onClick={() => setBlockId(block.id)}
                            >
                              <div className="block-heading">
                                <span className="block-number">
                                  {String(index + 1).padStart(2, "0")}
                                </span>
                                <select
                                  aria-label={`第 ${index + 1} 块类型`}
                                  value={block.kind}
                                  disabled={processing || !!busy}
                                  onChange={(e) =>
                                    changeBlock(block.id, {
                                      kind: e.target.value as Kind,
                                      ...(e.target.value === "table" &&
                                      !block.cells.length
                                        ? {
                                            cells: [
                                              [block.text, ""],
                                              ["", ""],
                                            ],
                                          }
                                        : {}),
                                      ...(e.target.value === "formula"
                                        ? {
                                            latex: block.latex || block.text,
                                            text: block.latex || block.text,
                                            display: true,
                                            verified: false,
                                          }
                                        : {}),
                                    })
                                  }
                                >
                                  {Object.entries(kinds).map(([key, label]) => (
                                    <option key={key} value={key}>
                                      {label}
                                    </option>
                                  ))}
                                </select>
                                <span className="block-confidence">
                                  {block.confidence !== null
                                    ? `${Math.round(block.confidence * 100)}%`
                                    : block.source === "manual"
                                      ? "手动"
                                      : "结构"}
                                </span>
                                <div className="block-actions">
                                  {iconButton(
                                    "内容块上移",
                                    MoveUp,
                                    () => moveBlock(block.id, -1),
                                    index === 0 || processing || !!busy,
                                  )}
                                  {iconButton(
                                    "内容块下移",
                                    MoveDown,
                                    () => moveBlock(block.id, 1),
                                    index === page.blocks.length - 1 ||
                                      processing ||
                                      !!busy,
                                  )}
                                  {iconButton(
                                    "删除内容块",
                                    Trash2,
                                    () => removeBlock(block.id),
                                    processing || !!busy,
                                  )}
                                </div>
                              </div>
                              {block.kind === "table" ? (
                                <>
                                  <div className="table-editor">
                                    <table>
                                      <tbody>
                                        {block.cells.map((row, i) => (
                                          <tr key={i}>
                                            {row.map((cell, j) => (
                                              <td key={j}>
                                                <textarea
                                                  aria-label={`表格第 ${i + 1} 行第 ${j + 1} 列`}
                                                  value={cell}
                                                  disabled={
                                                    processing || !!busy
                                                  }
                                                  rows={2}
                                                  onChange={(e) =>
                                                    changeBlock(block.id, {
                                                      cells: block.cells.map(
                                                        (r, ri) =>
                                                          ri === i
                                                            ? r.map((c, ci) =>
                                                                ci === j
                                                                  ? e.target
                                                                      .value
                                                                  : c,
                                                              )
                                                            : r,
                                                      ),
                                                    })
                                                  }
                                                />
                                              </td>
                                            ))}
                                          </tr>
                                        ))}
                                      </tbody>
                                    </table>
                                  </div>
                                  <div className="table-tools">
                                    <button
                                      disabled={
                                        processing ||
                                        !!busy ||
                                        block.cells.length >= 100
                                      }
                                      onClick={() =>
                                        changeBlock(block.id, {
                                          cells: [
                                            ...block.cells,
                                            Array(
                                              block.cells[0]?.length || 2,
                                            ).fill(""),
                                          ],
                                        })
                                      }
                                    >
                                      ＋ 行
                                    </button>
                                    <button
                                      disabled={
                                        processing ||
                                        !!busy ||
                                        (block.cells[0]?.length || 0) >= 50
                                      }
                                      onClick={() =>
                                        changeBlock(block.id, {
                                          cells: block.cells.map((r) => [
                                            ...r,
                                            "",
                                          ]),
                                        })
                                      }
                                    >
                                      ＋ 列
                                    </button>
                                    <button
                                      disabled={
                                        processing ||
                                        !!busy ||
                                        block.cells.length <= 1
                                      }
                                      onClick={() =>
                                        changeBlock(block.id, {
                                          cells: block.cells.slice(0, -1),
                                        })
                                      }
                                    >
                                      － 末行
                                    </button>
                                    <button
                                      disabled={
                                        processing ||
                                        !!busy ||
                                        (block.cells[0]?.length || 0) <= 1
                                      }
                                      onClick={() =>
                                        changeBlock(block.id, {
                                          cells: block.cells.map((r) =>
                                            r.slice(0, -1),
                                          ),
                                        })
                                      }
                                    >
                                      － 末列
                                    </button>
                                  </div>
                                </>
                              ) : block.kind === "image" ? (
                                <div className="image-block-note">
                                  <FileImage size={22} />
                                  <span>
                                    按左侧框选区域保留图片
                                    <br />
                                    <small>Word 插图 / Markdown 附件</small>
                                  </span>
                                </div>
                              ) : block.kind === "formula" ? (
                                <FormulaCard
                                  block={block}
                                  number={index + 1}
                                  imageSrc={imageUrl(doc.id, page.id, doc.version)}
                                  disabled={processing || !!busy}
                                  onChange={(patch) => changeBlock(block.id, patch)}
                                  onRetry={() => {
                                    setBlockId(block.id);
                                    setDrawing("formula");
                                    setSelection(block.bbox);
                                    setNotice("请在原图上调整选区，再点击“识别公式”。已核对公式不会自动覆盖；需要替换时请先取消核对。");
                                  }}
                                />
                              ) : (
                                <textarea
                                  aria-label={`第 ${index + 1} 块内容`}
                                  className={
                                    block.kind === "title" ? "title-text" : ""
                                  }
                                  value={block.text}
                                  rows={Math.min(
                                    8,
                                    Math.max(
                                      2,
                                      Math.ceil(block.text.length / 24),
                                    ),
                                  )}
                                  disabled={processing || !!busy}
                                  onChange={(e) =>
                                    changeBlock(block.id, {
                                      text: e.target.value,
                                    })
                                  }
                                />
                              )}{" "}
                              {block.warning && (
                                <div className="block-warning">
                                  <Info size={12} />
                                  {block.warning}
                                </div>
                              )}
                              {block.id === blockId &&
                                block.original_text &&
                                block.original_text !== block.text &&
                                block.kind !== "table" && (
                                  <details className="original-text">
                                    <summary>查看原始识别文字</summary>
                                    <p>{block.original_text}</p>
                                    <button
                                      className="text-btn"
                                      disabled={processing || !!busy}
                                      onClick={() =>
                                        changeBlock(block.id, {
                                          text: block.original_text,
                                          ...(block.kind === "formula"
                                            ? {
                                                latex: block.original_text,
                                                verified: false,
                                              }
                                            : {}),
                                        })
                                      }
                                    >
                                      恢复原始文字
                                    </button>
                                  </details>
                                )}
                            </article>
                          ))
                        )}
                      </div>
                      <div className="content-bottom">
                        <button
                          className="secondary"
                          disabled={processing || !!busy}
                          onClick={() => {
                            setDrawing("paragraph");
                            setSelection(null);
                          }}
                        >
                          <Plus size={15} />
                          添加文字
                        </button>
                        <button
                          className="secondary"
                          disabled={processing || !!busy}
                          onClick={() => {
                            setDrawing("image");
                            setSelection(null);
                          }}
                        >
                          <ImagePlus size={15} />
                          保留图片区域
                        </button>
                      </div>
                    </>
                  ) : (
                    <div className="tasks-panel">
                      <div className="inline-info">
                        规则提取适合常见通知，不会自动理解所有语义。修改事项后请重新确认；时间统一按北京时间（UTC+8）。
                      </div>
                      <label className="reference-field">
                        通知的参考日期
                        <input
                          type="date"
                          value={reference}
                          onChange={(e) => {
                            setReference(e.target.value);
                            setTasks([]);
                            setDirty(true);
                          }}
                        />
                      </label>
                      <button
                        className="secondary full"
                        disabled={!completed || processing || !!busy}
                        onClick={() => void run("提取候选事项", extract)}
                      >
                        <Sparkles size={16} />
                        从整份文档提取候选事项
                      </button>
                      {tasks.map((task, index) => (
                        <article className="task-card" key={task.id}>
                          <textarea
                            aria-label={`事项 ${index + 1} 名称`}
                            value={task.title}
                            onChange={(e) =>
                              editTask(index, { title: e.target.value })
                            }
                          />
                          <div className="task-fields">
                            <input
                              type="date"
                              aria-label={`事项 ${index + 1} 日期`}
                              value={task.date}
                              onChange={(e) =>
                                editTask(index, { date: e.target.value })
                              }
                            />
                            <input
                              type="time"
                              aria-label={`事项 ${index + 1} 时间`}
                              value={task.time}
                              onChange={(e) =>
                                editTask(index, { time: e.target.value })
                              }
                            />
                            <select
                              aria-label={`事项 ${index + 1} 类型`}
                              value={task.kind}
                              onChange={(e) =>
                                editTask(index, {
                                  kind: e.target.value as Task["kind"],
                                })
                              }
                            >
                              <option value="event">活动 / 日程</option>
                              <option value="deadline">截止 / 待办</option>
                            </select>
                            <input
                              aria-label={`事项 ${index + 1} 地点`}
                              placeholder="地点（可选）"
                              value={task.location}
                              onChange={(e) =>
                                editTask(index, { location: e.target.value })
                              }
                            />
                          </div>
                          <details>
                            <summary>查看原文</summary>
                            <p>{task.source_text}</p>
                            <small>{task.note}</small>
                          </details>
                          <label className="checkbox">
                            <input
                              type="checkbox"
                              checked={task.confirmed}
                              onChange={(e) =>
                                editTask(index, { confirmed: e.target.checked })
                              }
                            />
                            已核对，加入日历导出
                          </label>
                        </article>
                      ))}
                      {!tasks.length && (
                        <div className="empty-tasks">
                          <CalendarDays size={30} />
                          <p>
                            先识别通知，再提取候选事项。
                            <br />
                            也可以手动添加一条。
                          </p>
                        </div>
                      )}
                      <button
                        className="text-btn"
                        disabled={processing || !!busy || tasks.length >= 100}
                        onClick={() => {
                          setDirty(true);
                          setExportResult(null);
                          setTasks([
                            ...tasks,
                            {
                              id: makeId(),
                              title: "",
                              source_text: selected?.text || "",
                              page_id: page.id,
                              date: "",
                              time: "",
                              location: "",
                              kind: "event",
                              confirmed: false,
                              note: "手动添加，请核对。",
                            },
                          ]);
                        }}
                      >
                        <Plus size={15} />
                        手动添加事项
                      </button>
                      <button
                        className="primary full"
                        disabled={!tasks.some((t) => t.confirmed) || !!busy}
                        onClick={() => void run("导出日历", calendar)}
                      >
                        <Download size={16} />
                        导出已确认事项 .ics
                      </button>
                      {calendarDownload && (
                        <a className="download-link full" href={calendarDownload} download="识页-待办日历.ics">
                          <Download size={16} /> 下载日历 .ics
                        </a>
                      )}
                      <small className="calendar-note">
                        这是文件导出，不会自动同步或创建系统提醒。VTODO
                        需使用支持待办的日历客户端。点击顶部“保存”可保留待办草稿；导出日历前也会自动保存。
                      </small>
                    </div>
                  )}
                </section>
              </div>
              <section className="export-bar" id="export-panel" aria-label="导出与下载">
                <div className="export-label">
                  <span className="export-symbol">
                    <Download size={20} />
                  </span>
                  <div>
                    <strong>最后一步：生成文件 → 下载到电脑</strong>
                    <small>
                      {format === "pdf-image"
                        ? "直接合并图像，无需 OCR"
                        : format === "pdf-searchable"
                          ? "原图保持不变，校对文字进入隐藏文字层"
                          : "使用当前校对版本，不会重新识别"}
                    </small>
                  </div>
                </div>
                <div className="export-controls">
                  <select
                    aria-label="导出格式"
                    value={format}
                    onChange={(e) => {
                      setFormat(e.target.value as ExportFormat);
                      setExportResult(null);
                    }}
                  >
                    {formats.map((f) => (
                      <option key={f.id} value={f.id}>
                        {f.name} {f.tag}
                      </option>
                    ))}
                  </select>
                  <button
                    className="primary"
                    disabled={
                      !!busy ||
                      processing ||
                      (!completed && !["pdf-image", "json"].includes(format))
                    }
                    onClick={() => void run("生成导出文件", doExport)}
                  >
                    {busy ? (
                      <LoaderCircle className="spin" size={16} />
                    ) : (
                      <Download size={16} />
                    )}{" "}
                    {busy || "生成导出文件"}
                  </button>
                  {exportResult && (
                    <a
                      className="download-link"
                      href={exportResult.url}
                      download={exportResult.filename}
                    >
                      <Download size={16} />
                      下载文件
                    </a>
                  )}
                </div>
              </section>
              {exportResult && (
                <div className="export-notes">
                  <strong>
                    {exportResult.filename} · 校对版本 v{exportResult.version}
                  </strong>
                  {exportResult.warnings.map((w) => (
                    <span key={w}>{w}</span>
                  ))}
                </div>
              )}
            </>
          )}
        </main>
      </div>
      {showSettings && <RecognitionSettings close={() => setShowSettings(false)} changed={() => {
        void api<FormulaStatus>("/formula/status").then(setFormulaStatus).catch(() => {});
      }} />}
      {cloudRequest && <dialog ref={cloudDialog} className="recognition-dialog" onCancel={() => setCloudRequest(null)}>
        <header><div><span className="eyebrow">YOUR CHOICE · YOUR DATA</span><h2>确认发送至你的 API</h2></div>
          <button aria-label="取消 API 发送" onClick={() => setCloudRequest(null)}><X /></button></header>
        <p>目标：<strong>{cloudRequest.settings.endpoint}</strong></p>
        <p>模型：{cloudRequest.settings.model}。图片将发送至该第三方，可能产生费用；识页不会代付或自动重试。</p>
        <p>{cloudRequest.bbox ? "只发送当前框选区域，不发送整页。" : "勾选要发送的页面。图片最长边将缩放至不超过 2400 像素。"}</p>
        {!cloudRequest.bbox && <div className="cloud-page-list">{cloudRequest.doc.pages.map((p, index) =>
          <label key={p.id}><input type="checkbox" checked={cloudRequest.page_ids.includes(p.id)} onChange={e => {
            setCloudRequest({ ...cloudRequest, page_ids: e.target.checked ? [...cloudRequest.page_ids, p.id] : cloudRequest.page_ids.filter(id => id !== p.id) });
          }} />第 {index + 1} 页 · {p.source_name}</label>)}</div>}
        <p className="inline-warning">返回后先预览候选，不会直接覆盖原内容。取消不能撤销供应商已开始的处理和费用。</p>
        <div className="recognition-actions"><button className="primary" disabled={!!busy || !cloudRequest.page_ids.length} onClick={() => void run("确认发送", confirmCloud)}>同意发送并识别（{cloudRequest.page_ids.length} 页{cloudRequest.bbox ? "中的选区" : ""}）</button>
          <button disabled={!!busy} onClick={() => setCloudRequest(null)}>暂不发送</button></div>
        {error && <p role="alert" className="inline-warning">{error}</p>}
      </dialog>}
      {showHelp && (
        <dialog className="help-dialog" ref={helpDialog} aria-labelledby="help-title"
          onCancel={() => setShowHelp(false)}
          onClick={(e) => { if (e.target === e.currentTarget) setShowHelp(false); }}>
          <section
            className="help-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="close-modal icon-btn"
              aria-label="关闭使用指引"
              onClick={() => setShowHelp(false)}
            >
              <X size={20} />
            </button>
            <span className="eyebrow">新手指南 · 随时回来查看</span>
            <h2 id="help-title">第一次使用，跟着这四步。</h2>
            <ol>
              <li>
                <strong>导入并整理</strong>
                <p>
                  选择图片或 PDF，可输入页码范围。多份 PDF
                  默认分开，图片批次默认合并。导入后支持调整页序、旋转和框选裁剪。
                </p>
              </li>
              <li>
                <strong>选择模式，开始识别</strong>
                <p>
                  先遮盖不希望保留的内容，再开始识别。论文或课本选择“学术公式”，也可在原图上框选单个公式；文字、表格和数学公式都能继续校对。
                </p>
              </li>
              <li>
                <strong>对照原图，逐块校对</strong>
                <p>点击原图上的识别框会定位到对应内容。公式默认像课本一样显示：点“对照 / 放大”检查符号，点“修改公式”直接改字母、分式或矩阵，再点“应用修改”。核对无误后勾选“已对照原图核对”并保存。手机可切换“只看原图 / 只看校对”；需要代码时再展开“高级”。</p>
              </li>
              <li>
                <strong>选择格式，生成并下载</strong>
                <p>
                  Word 是可编辑的重排版；Markdown 有图片时打包 ZIP；可搜索 PDF
                  保留画面并加入校对后的文字层。纯图片 PDF 不需要 OCR。
                </p>
              </li>
            </ol>
            <div className="help-note">
              <ShieldCheck size={20} />
              <div>
                <strong>关于隐私和保存</strong>
                <p>
                  文件发送到运行识页的服务器。本机启动时，数据就在你的电脑；如果部署到他人的服务器，文件会发送到那里。桌面版可选自己的 API，仅明确同意后发送所选页面或框选图像；供应商可能收费。本地模式不会自动切换云端。文件默认保留 24 小时，可在最近文档中彻底删除。浏览器
                  Cookie 是访问凭证，请勿共享。
                </p>
              </div>
            </div>
            <p className="muted">
              当前主要支持清晰印刷中文、英文、原生 PDF、简单有线表格和印刷数学公式。
              手写、模糊长公式、合并单元格、多栏版面和特殊字体仍可能识别不准；模型结果不是论文定稿，重要内容务必对照原图核对。
            </p>
            <details className="help-note" style={{ display: "block" }} onToggle={async (event) => {
              if (event.currentTarget.open && !licenseHtml) {
                try {
                  const response = await fetch("/licenses/index.html");
                  if (!response.ok) throw new Error("License page unavailable");
                  setLicenseHtml(await response.text());
                } catch {
                  setLicenseHtml("<p>许可正文暂未载入，请关闭使用指南后重试，或查看安装目录/Release 的 Notices 材料。</p>");
                }
              }
            }}>
              <summary style={{ cursor: "pointer" }}>开源许可与源码（离线可读）</summary>
              <p className="muted">识页自有代码采用 MIT；包含 PyMuPDF 的核心组合遵循适用 AGPL 条件，第三方组件保留各自许可。</p>
              <iframe title="开源许可正文" srcDoc={licenseHtml} sandbox=""
                style={{ width: "100%", height: 350, border: "1px solid #ccd9c8", borderRadius: 8 }} />
            </details>
            <button className="primary full" onClick={() => setShowHelp(false)}>
              知道了，开始使用 <ArrowRight size={16} />
            </button>
          </section>
        </dialog>
      )}
    </div>
  );
}
