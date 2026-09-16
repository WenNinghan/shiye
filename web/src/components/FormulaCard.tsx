import { useEffect, useMemo, useRef, useState } from "react";
import type { ComponentType } from "react";
import katex from "katex";
import "katex/dist/katex.min.css";
import {
  Check,
  Copy,
  Download,
  Edit3,
  Expand,
  LoaderCircle,
  RefreshCw,
  X,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import type { Block } from "../types";

function renderFormula(latex: string, display: boolean): string | null {
  if (
    !latex.trim() ||
    /\\(?:placeholder|href|url|includegraphics|html\w+)\b/.test(latex)
  )
    return null;
  try {
    return katex.renderToString(latex, {
      displayMode: display,
      throwOnError: true,
      trust: false,
      strict: "ignore",
      maxExpand: 1000,
      output: "htmlAndMathml",
    });
  } catch {
    return null;
  }
}

function SourceCrop({ src, bbox }: { src: string; bbox: number[] }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const coords = bbox.join(",");
  useEffect(() => {
    let alive = true;
    setLoaded(false);
    setFailed(false);
    const image = new Image();
    image.onload = () => {
      if (!alive || !canvas.current) return;
      const [x0, y0, x1, y1] = coords.split(",").map(Number);
      if (![x0, y0, x1, y1].every(Number.isFinite) || x1 <= x0 || y1 <= y0) {
        setFailed(true);
        return;
      }
      const left = Math.max(0, Math.floor((x0 - 0.006) * image.naturalWidth));
      const top = Math.max(0, Math.floor((y0 - 0.006) * image.naturalHeight));
      const right = Math.min(
        image.naturalWidth,
        Math.ceil((x1 + 0.006) * image.naturalWidth),
      );
      const bottom = Math.min(
        image.naturalHeight,
        Math.ceil((y1 + 0.006) * image.naturalHeight),
      );
      const context = canvas.current.getContext("2d");
      if (!context || right <= left || bottom <= top) {
        setFailed(true);
        return;
      }
      canvas.current.width = right - left;
      canvas.current.height = bottom - top;
      context.drawImage(
        image,
        left,
        top,
        right - left,
        bottom - top,
        0,
        0,
        right - left,
        bottom - top,
      );
      setLoaded(true);
    };
    image.onerror = () => alive && setFailed(true);
    image.src = src;
    return () => {
      alive = false;
    };
  }, [src, coords]);
  return (
    <div className="formula-source-crop">
      {failed ? (
        <p>
          局部原图暂时无法显示。
          <a href={src} target="_blank" rel="noreferrer">
            打开整页原图
          </a>
        </p>
      ) : (
        <>
          <canvas
            ref={canvas}
            role="img"
            aria-label="原图中的公式"
            style={{ display: loaded ? "block" : "none" }}
          />
          {!loaded && <span>正在载入原图…</span>}
        </>
      )}
    </div>
  );
}

type EditorProps = { initialValue: string; onChange: (value: string) => void };
export default function FormulaCard({
  block,
  number,
  imageSrc,
  disabled,
  onChange,
  onRetry,
}: {
  block: Block;
  number: number;
  imageSrc: string;
  disabled: boolean;
  onChange: (patch: Partial<Block>) => void;
  onRetry: () => void;
}) {
  const latex = block.latex || block.text;
  const html = useMemo(
    () => renderFormula(latex, block.display),
    [latex, block.display],
  );
  const [mode, setMode] = useState<"compare" | "edit" | "image" | null>(null);
  const [draft, setDraft] = useState(latex);
  const [zoom, setZoom] = useState(100);
  const [message, setMessage] = useState("");
  const [discarding, setDiscarding] = useState(false);
  const [png, setPng] = useState("");
  const [exporting, setExporting] = useState(false);
  const [Editor, setEditor] = useState<ComponentType<EditorProps> | null>(null);
  const [editorError, setEditorError] = useState("");
  const dialog = useRef<HTMLDialogElement>(null);
  const typeset = useRef<HTMLDivElement>(null);
  const draftHtml = useMemo(
    () => renderFormula(draft, block.display),
    [draft, block.display],
  );
  const unsaved = mode === "edit" && draft !== latex;

  useEffect(() => {
    if (mode) dialog.current?.showModal();
  }, [mode]);
  useEffect(() => {
    if (!unsaved) return;
    const warn = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [unsaved]);
  useEffect(() => {
    if (mode !== "edit" || Editor) return;
    let alive = true;
    setEditorError("");
    import("./VisualFormulaEditor")
      .then((module) => {
        if (alive) setEditor(() => module.default);
      })
      .catch(() => {
        if (alive)
          setEditorError("编辑器加载失败。请关闭后重试，或使用高级源码编辑。");
      });
    return () => {
      alive = false;
    };
  }, [mode, Editor]);
  useEffect(() => {
    setPng("");
  }, [latex, block.display]);
  useEffect(
    () => () => {
      if (png) URL.revokeObjectURL(png);
    },
    [png],
  );
  useEffect(() => {
    if (mode !== "image" || !html || png || !typeset.current) return;
    let alive = true;
    const target = typeset.current;
    setExporting(true);
    setMessage("");
    import("../formula-image")
      .then(({ formulaPng }) => formulaPng(target))
      .then((blob) => {
        if (alive) setPng(URL.createObjectURL(blob));
      })
      .catch((e) => {
        if (alive)
          setMessage(
            e instanceof Error ? e.message : "图片生成失败，请关闭后重试。",
          );
      })
      .finally(() => {
        if (alive) setExporting(false);
      });
    return () => {
      alive = false;
    };
  }, [mode, html, png]);

  function close() {
    if (unsaved) {
      setDiscarding(true);
      return;
    }
    setMode(null);
  }
  function open(next: "compare" | "edit" | "image") {
    setDraft(latex);
    setZoom(100);
    setMessage("");
    setDiscarding(false);
    setMode(next);
  }
  const formulaView = (markup: string | null, ref = false) =>
    markup ? (
      <div
        ref={ref ? typeset : undefined}
        className="formula-typeset"
        dangerouslySetInnerHTML={{ __html: markup }}
      />
    ) : (
      <p className="formula-unreadable">
        {latex.trim()
          ? "这条公式暂时无法正确排版。请对照原图修改，或重新框选识别。"
          : "这里还没有公式。可以点击“修改公式”输入。"}
      </p>
    );

  return (
    <div
      className="formula-editor formula-reading-card"
      onClick={(e) => e.stopPropagation()}
    >
      <div className="formula-reading-meta">
        <strong>公式 {number}</strong>
        <span className={block.verified && html ? "checked" : "unchecked"}>
          {block.verified && html ? "已核对" : "待核对"}
        </span>
      </div>
      <div className="formula-preview" aria-label={`第 ${number} 块公式预览`}>
        {formulaView(html, true)}
      </div>
      {!html && <SourceCrop src={imageSrc} bbox={block.bbox} />}
      <div className="formula-reading-actions">
        <button className="secondary" onClick={() => open("compare")}>
          <Expand size={15} /> 对照 / 放大
        </button>
        <button
          className="primary"
          disabled={disabled}
          onClick={() => open("edit")}
        >
          <Edit3 size={15} /> 修改公式
        </button>
        <button
          className="secondary"
          disabled={disabled || !html}
          onClick={() => open("image")}
        >
          <Download size={15} /> 公式图片
        </button>
      </div>
      <div className="formula-options">
        <label className="checkbox verified-formula">
          <input
            type="checkbox"
            checked={!!block.verified && !!html}
            disabled={disabled || !html}
            onChange={(e) => onChange({ verified: e.target.checked })}
          />
          已对照原图核对
        </label>
        <button className="text-btn" disabled={disabled} onClick={onRetry}>
          <RefreshCw size={13} /> 重新框选
        </button>
      </div>
      <details className="formula-advanced">
        <summary>高级：公式代码与显示设置</summary>
        <label>
          LaTeX 源码
          <textarea
            aria-label={`第 ${number} 块 LaTeX`}
            value={latex}
            rows={3}
            disabled={disabled}
            onChange={(e) =>
              onChange({
                latex: e.target.value,
                text: e.target.value,
                verified: false,
              })
            }
          />
        </label>
        <div className="formula-options">
          <label className="checkbox">
            <input
              type="checkbox"
              checked={block.display}
              disabled={disabled}
              onChange={(e) => onChange({ display: e.target.checked })}
            />
            独立成行
          </label>
          <button
            className="text-btn"
            onClick={() => {
              void navigator.clipboard
                .writeText(latex)
                .then(() => setMessage("公式源码已复制。"))
                .catch(() =>
                  setMessage("浏览器未允许复制，请在源码框中手动选择并复制。"),
                );
            }}
          >
            <Copy size={13} /> 复制 LaTeX
          </button>
        </div>
      </details>
      {message && !mode && (
        <p className="formula-feedback" role="status">
          {message}
        </p>
      )}
      {mode && (
        <dialog
          ref={dialog}
          className="formula-dialog"
          aria-labelledby={`formula-dialog-${block.id}`}
          onClick={(e) => {
            if (e.target === e.currentTarget) close();
          }}
          onCancel={(e) => {
            e.preventDefault();
            close();
          }}
        >
          <section className="formula-modal">
            <header>
              <div>
                <span>公式 {number} · 对照原图，保留数学含义</span>
                <h2 id={`formula-dialog-${block.id}`}>
                  {mode === "edit"
                    ? "像写公式一样，修改公式"
                    : mode === "image"
                      ? "带走一张清晰的公式图片"
                      : "看清每一个符号"}
                </h2>
              </div>
              <button
                className="icon-btn"
                aria-label="关闭公式窗口"
                onClick={close}
              >
                <X size={21} />
              </button>
            </header>
            {mode !== "image" && (
              <div className="formula-compare-grid">
                <section>
                  <h3>原图中的公式</h3>
                  <SourceCrop src={imageSrc} bbox={block.bbox} />
                </section>
                <section>
                  <h3>{mode === "edit" ? "修改后的效果" : "识别后的公式"}</h3>
                  <div
                    className="formula-enlarged"
                    style={{ fontSize: `${(24 * zoom) / 100}px` }}
                  >
                    {formulaView(mode === "edit" ? draftHtml : html)}
                  </div>
                </section>
              </div>
            )}
            {mode === "compare" && (
              <div className="formula-zoom-controls">
                <button
                  className="secondary"
                  disabled={zoom <= 75}
                  onClick={() => setZoom((n) => n - 25)}
                >
                  <ZoomOut size={16} />
                  缩小
                </button>
                <span aria-live="polite">{zoom}%</span>
                <button
                  className="secondary"
                  disabled={zoom >= 250}
                  onClick={() => setZoom((n) => n + 25)}
                >
                  <ZoomIn size={16} />
                  放大
                </button>
                <button
                  className="primary"
                  disabled={disabled}
                  onClick={() => open("edit")}
                >
                  <Edit3 size={15} />
                  修改公式
                </button>
              </div>
            )}
            {mode === "edit" && (
              <>
                {editorError ? (
                  <p role="alert">{editorError}</p>
                ) : Editor ? (
                  <Editor initialValue={latex} onChange={setDraft} />
                ) : (
                  <p role="status">
                    <LoaderCircle size={17} className="spin" />
                    正在加载本机公式编辑器…
                  </p>
                )}
                {!draftHtml && (
                  <p className="formula-feedback" role="status">
                    请补全公式中的空位，并检查符号结构。排版有效后才可以应用。
                  </p>
                )}
                {discarding && (
                  <div className="formula-discard" role="alert">
                    <span>这次修改还未应用，是否放弃？原公式会保留。</span>
                    <button
                      className="secondary"
                      onClick={() => setDiscarding(false)}
                    >
                      继续编辑
                    </button>
                    <button className="secondary" onClick={() => setMode(null)}>
                      放弃本次修改
                    </button>
                  </div>
                )}
                <footer>
                  <span>应用后仍需对照原图核对，再保存文档。</span>
                  <button className="secondary" onClick={close}>
                    取消修改
                  </button>
                  <button
                    className="primary"
                    disabled={
                      disabled || !Editor || !!editorError || !draftHtml
                    }
                    onClick={() => {
                      if (draft !== latex)
                        onChange({
                          latex: draft,
                          text: draft,
                          verified: false,
                        });
                      setMode(null);
                    }}
                  >
                    <Check size={15} />
                    应用修改
                  </button>
                </footer>
              </>
            )}
            {mode === "image" && (
              <div className="formula-image-result">
                {exporting && !png && (
                  <p role="status">
                    <LoaderCircle size={18} className="spin" />
                    正在生成高清 PNG…
                  </p>
                )}
                {message && <p role="alert">{message}</p>}
                {png && (
                  <>
                    <div className="formula-png-preview">
                      <img src={png} alt="将要下载的公式图片" />
                    </div>
                    <p>
                      白色背景 · 2 倍清晰度 ·
                      只包含当前公式。图片不可直接编辑，需继续编辑时请导出
                      Word。
                    </p>
                    {!block.verified && (
                      <p className="formula-feedback">
                        这条公式还未标记为已核对，请先检查符号。
                      </p>
                    )}
                    <a
                      className="download-link"
                      href={png}
                      download={`识页-公式-${number}.png`}
                    >
                      <Download size={17} />
                      下载 PNG
                    </a>
                  </>
                )}
              </div>
            )}
          </section>
        </dialog>
      )}
    </div>
  );
}
