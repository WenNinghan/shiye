import { useEffect, useRef } from "react";
import { MathfieldElement } from "mathlive";
import "mathlive/fonts.css";

// Fonts are bundled by Vite, never fetched from a CDN. Editing is not calculation.
MathfieldElement.fontsDirectory = null;
MathfieldElement.soundsDirectory = null;
MathfieldElement.computeEngine = null;
MathfieldElement.locale = "zh-CN";

const templates = [
  ["分式", String.raw`\frac{#0}{#?}`],
  ["根号", String.raw`\sqrt{#0}`],
  ["上标", String.raw`{#0}^{#?}`],
  ["下标", String.raw`{#0}_{#?}`],
  ["积分", String.raw`\int_{#?}^{#?} #0 \,dx`],
  ["求和", String.raw`\sum_{#?}^{#?} #0`],
  ["2×2 矩阵", String.raw`\begin{bmatrix}#?&#?\\#?&#?\end{bmatrix}`],
] as const;

export default function VisualFormulaEditor({
  initialValue,
  onChange,
}: {
  initialValue: string;
  onChange: (value: string) => void;
}) {
  const host = useRef<HTMLDivElement>(null);
  const keyboardHost = useRef<HTMLDivElement>(null);
  const field = useRef<MathfieldElement | null>(null);
  const initial = useRef(initialValue);
  const notify = useRef(onChange);
  notify.current = onChange;

  useEffect(() => {
    const mf = new MathfieldElement();
    field.current = mf;
    mf.setAttribute("aria-label", "可视化公式编辑器");
    mf.mathVirtualKeyboardPolicy = "manual";
    mf.smartMode = false;
    mf.smartFence = false;
    mf.value = initial.current;
    const update = () => notify.current(mf.value);
    mf.addEventListener("input", update);
    host.current!.appendChild(mf);
    mf.menuItems = [];
    const keyboard = window.mathVirtualKeyboard;
    keyboard.container = keyboardHost.current;
    keyboard.layouts = ["numeric", "symbols", "alphabetic", "greek"];
    mf.focus();
    return () => {
      keyboard.hide({ animate: false });
      keyboard.container = null;
      mf.removeEventListener("input", update);
      mf.remove();
      field.current = null;
    };
  }, []);

  return (
    <div className="visual-formula-editor">
      <p className="math-editor-instructions">
        点击公式里的字母、分子、分母或矩阵格子直接修改。也可以用下面的按钮插入结构。
      </p>
      <div className="math-template-bar" role="group" aria-label="插入公式结构">
        {templates.map(([name, value]) => (
          <button
            key={name}
            type="button"
            onPointerDown={(e) => e.preventDefault()}
            onClick={() => {
              field.current?.focus();
              field.current?.insert(value, { selectionMode: "placeholder" });
            }}
          >
            {name}
          </button>
        ))}
      </div>
      <div className="math-field-host" ref={host} />
      <div className="math-edit-actions">
        <button
          type="button"
          onClick={() => {
            field.current?.focus();
            field.current?.executeCommand("undo");
          }}
        >
          撤销
        </button>
        <button
          type="button"
          onClick={() => {
            field.current?.focus();
            field.current?.executeCommand("redo");
          }}
        >
          重做
        </button>
        <button
          type="button"
          onClick={() => {
            field.current?.focus();
            window.mathVirtualKeyboard.visible =
              !window.mathVirtualKeyboard.visible;
          }}
        >
          数学键盘
        </button>
      </div>
      <div className="math-keyboard-host" ref={keyboardHost} />
    </div>
  );
}
