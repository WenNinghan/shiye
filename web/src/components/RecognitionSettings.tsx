import { useEffect, useRef, useState } from "react";
import { Cloud, HardDrive, KeyRound, X } from "lucide-react";
import { desktop, type DesktopSettings } from "../desktop";

export default function RecognitionSettings({ close, changed }: { close(): void; changed(): void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [settings, setSettings] = useState<DesktopSettings | null>(null);
  const [endpoint, setEndpoint] = useState(""), [model, setModel] = useState(""), [key, setKey] = useState("");
  const [remember, setRemember] = useState(false), [busy, setBusy] = useState(""), [message, setMessage] = useState("");
  useEffect(() => {
    dialog.current?.showModal();
    void desktop?.getSettings().then(value => {
      setSettings(value); setEndpoint(value.endpoint); setModel(value.model); setRemember(value.remember); setMessage(value.message);
    }).catch(e => setMessage(e.message));
  }, []);
  async function run(label: string, action: () => Promise<DesktopSettings>) {
    setBusy(label); setMessage("");
    try { const value = await action(); setSettings(value); setKey(""); setMessage(value.message || "设置已更新。尚未向 API 发送任何图片。"); changed(); }
    catch (e) { setMessage(e instanceof Error ? e.message : "操作失败"); }
    finally { setBusy(""); }
  }
  return <dialog ref={dialog} className="recognition-dialog" onCancel={close}>
    <header><div><span className="eyebrow">RECOGNITION SETTINGS</span><h2>选择适合你的识别方式</h2></div>
      <button aria-label="关闭识别设置" disabled={!!busy} onClick={close}><X /></button></header>
    <p>默认本机处理。API 是可选增强，不是开始使用的门槛。</p>
    <section className="recognition-option"><HardDrive /><div><h3>本地识别 · 不需要密钥</h3>
      <p>文字识别与导出在本机完成。公式扩展包安装后也可以离线使用。</p>
      <p>{settings?.formula.available ? "公式引擎已就绪" : "公式扩展包未就绪；不影响普通 OCR"}</p>
      {desktop && <button className="secondary" disabled={!!busy} onClick={() => void run("正在校验并安装模型包", () => desktop!.importModelPack())}>导入公式离线包</button>}
    </div></section>
    <section className="recognition-option"><Cloud /><div><h3>自己的 API · 按需使用</h3>
      <p>支持图片输入的 Chat Completions 兼容服务。先保存配置，再选择页面并确认发送；供应商可能收费。</p>
      {!desktop ? <p className="inline-warning">API 密钥管理仅在桌面安装版开放。当前浏览器版仍可使用本地引擎。</p> :
        <form onSubmit={event => { event.preventDefault(); void run("正在保存", () => desktop!.saveSettings({ endpoint, model, key, remember })); }}>
          <label>完整 API 地址<input aria-label="完整 API 地址" type="url" required value={endpoint} onChange={e => setEndpoint(e.target.value)} placeholder="https://你的服务商/v1/chat/completions" autoComplete="off" /></label>
          <label>支持图片输入的模型名<input aria-label="模型名" required value={model} onChange={e => setModel(e.target.value)} placeholder="填写服务商提供的模型名" autoComplete="off" /></label>
          <label>API 密钥<input aria-label="API 密钥" required type="password" value={key} onChange={e => setKey(e.target.value)} placeholder={settings?.configured ? "已配置；修改时请重新填写" : "仅你自己的密钥"} autoComplete="new-password" /></label>
          <label className="remember-key"><input type="checkbox" checked={remember} onChange={e => setRemember(e.target.checked)} />使用系统加密记住密钥（默认不保存）</label>
          <div className="recognition-actions"><button className="primary" disabled={!!busy || !key}><KeyRound size={16} /> 保存配置，不发送图片</button>
            <button className="secondary" type="button" disabled={!!busy || !settings?.configured} onClick={() => void run("正在删除配置", () => desktop!.clearSettings())}>删除 API 配置</button></div>
        </form>}
    </div></section>
    {(busy || message) && <p className="inline-warning" role="status">{busy || message}</p>}
    <footer>使用顺序：导入文件 → 选择本地或 API → 识别与校对 → 导出。临时文档保留 24 小时，请及时保存导出文件。</footer>
  </dialog>;
}
