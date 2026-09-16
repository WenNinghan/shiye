const { app, BrowserWindow, ipcMain, session, dialog, safeStorage } = require('electron');
const path = require('node:path');
const fs = require('node:fs/promises');
const { spawn } = require('node:child_process');
const { randomBytes } = require('node:crypto');
const readline = require('node:readline');
const { assertSender, validateProfile } = require('./security.cjs');
const { CredentialStore } = require('./credentials.cjs');
const { importModelPack } = require('./model-packs.cjs');
app.setName('Shiye');
if (process.env.SHIYE_DESKTOP_TEST_DATA) app.setPath('userData', process.env.SHIYE_DESKTOP_TEST_DATA);
let engine, win, origin, token, control, vault, profile = null, startupMessage = '', importing = false;
const resources = app.isPackaged ? process.resourcesPath : path.resolve(__dirname, '..');
const enginePath = app.isPackaged ? path.join(resources, 'engine', 'shiye-engine.exe') : process.env.SHIYE_ENGINE_EXE;
const dataRoot = () => path.join(app.getPath('userData'), 'data');
function stopEngine() {
  if (engine && engine.exitCode === null && !engine.killed) {
    const killer = spawn('taskkill.exe', ['/PID', String(engine.pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore' });
    killer.on('error', () => engine?.kill());
  }
}
async function controlRequest(method, body) {
  const response = await fetch(origin + '/internal/desktop/config', {
    method, headers: { 'x-shiye-control': control, 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(10000)
  });
  if (!response.ok) throw new Error('本机设置未生效，请重试');
  return response.json();
}
async function startEngine() {
  if (!enginePath) throw new Error('未指定已打包的识别引擎。请先运行构建脚本。');
  token = randomBytes(32).toString('hex'); control = randomBytes(32).toString('hex');
  await fs.mkdir(dataRoot(), { recursive: true });
  engine = spawn(enginePath, [], { windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'], cwd: dataRoot() });
  // Backend never receives secrets in argv, inherited environment, or URL.
  engine.stdin.end(JSON.stringify({ token, control, data_dir: dataRoot() }) + '\n');
  engine.stdin.on('error', () => {});
  engine.stderr.on('data', () => {}); // Do not write unknown provider/engine errors to persistent logs.
  const port = await new Promise((resolve, reject) => {
    const lines = readline.createInterface({ input: engine.stdout });
    const timer = setTimeout(() => reject(new Error('识别引擎启动超时')), 60000);
    const finish = (error, value) => { clearTimeout(timer); lines.close(); error ? reject(error) : resolve(value); };
    engine.once('error', () => finish(new Error('识别引擎无法启动')));
    engine.once('exit', () => finish(new Error('识别引擎提前退出')));
    lines.on('line', line => {
      try {
        const { port } = JSON.parse(line);
        if (Number.isInteger(port) && port > 0 && port < 65536) finish(null, port);
      } catch {}
    });
  });
  origin = 'http://127.0.0.1:' + port;
  let healthy = false;
  for (let i = 0; i < 80; i++) {
    try {
      const response = await fetch(origin + '/api/health', { headers: { 'x-shiye-desktop': token }, signal: AbortSignal.timeout(1000) });
      if (response.ok) { healthy = true; break; }
    } catch {}
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  if (!healthy) throw new Error('识别引擎健康检查失败');
  engine.once('exit', () => {
    if (win && !win.isDestroyed()) dialog.showMessageBox(win, { type: 'error', message: '识别引擎已退出，请关闭后重新打开识页。原文件仍在本机。' });
  });
}
function handle(name, action) {
  ipcMain.handle(name, async (event, value) => {
    assertSender(event, win.webContents, origin);
    try { return await action(value); }
    catch (error) { throw new Error(error.message || '操作失败'); }
  });
}
async function settings() {
  return { desktop: true, configured: !!profile, endpoint: profile?.endpoint || '', model: profile?.model || '',
    remember: !!profile?.remember, message: startupMessage, importing,
    formula: await fetch(origin + '/api/formula/status', { headers: { 'x-shiye-desktop': token } }).then(r => r.json()) };
}
async function boot() {
  await startEngine();
  vault = new CredentialStore(app.getPath('userData'), safeStorage);
  try {
    const saved = await vault.load();
    if (saved) { profile = validateProfile(saved); await controlRequest('PUT', profile); }
  } catch (error) { profile = null; startupMessage = error.message; }
  const desktopSession = session.fromPartition('persist:shiye');
  win = new BrowserWindow({ width: 1400, height: 960, minWidth: 820, minHeight: 620,
    title: '识页 · 文档工作台', show: false, backgroundColor: '#f8f9f5',
    webPreferences: { preload: path.join(__dirname, 'preload.cjs'), contextIsolation: true,
      sandbox: true, nodeIntegration: false, session: desktopSession, spellcheck: false }
  });
  desktopSession.setPermissionRequestHandler((_webContents, _permission, callback) => callback(false));
  desktopSession.setPermissionCheckHandler(() => false);
  desktopSession.webRequest.onBeforeSendHeaders({ urls: [origin + '/*'] }, (details, callback) => {
    const headers = { ...details.requestHeaders };
    delete headers['x-shiye-control']; delete headers['X-Shiye-Control'];
    if (details.webContentsId === win?.webContents.id) headers['x-shiye-desktop'] = token;
    callback({ requestHeaders: headers });
  });
  win.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  win.webContents.on('will-navigate', (event, target) => {
    try { if (new URL(target).origin !== origin) event.preventDefault(); } catch { event.preventDefault(); }
  });
  win.webContents.on('will-attach-webview', event => event.preventDefault());
  desktopSession.on('will-download', (_event, item) => {
    item.setSaveDialogOptions({ title: '保存识页导出文件', defaultPath: path.join(app.getPath('downloads'), path.basename(item.getFilename())) });
  });
  handle('shiye:settings', settings);
  handle('shiye:save-settings', async value => {
    const next = validateProfile(value);
    await vault.save(next);
    try { await controlRequest('PUT', next); profile = next; startupMessage = ''; }
    catch (error) { await vault.clear(); profile = null; await controlRequest('DELETE').catch(() => {}); throw error; }
    return settings();
  });
  handle('shiye:clear-settings', async () => {
    await controlRequest('DELETE'); await vault.clear(); profile = null; startupMessage = ''; return settings();
  });
  handle('shiye:import-model', async () => {
    if (importing) throw new Error('已有模型包正在安装');
    const result = await dialog.showOpenDialog(win, { title: '选择识页公式离线包', properties: ['openFile'],
      filters: [{ name: '识页模型包', extensions: ['shiye-model'] }] });
    if (result.canceled) return settings();
    const location = await dialog.showOpenDialog(win, { title: '选择公式模型保存位置（需约 2 GB 可用空间，可选择 D/G 盘）',
      defaultPath: app.getPath('userData'), properties: ['openDirectory', 'createDirectory'] });
    if (location.canceled) return settings();
    importing = true;
    try {
      await importModelPack(result.filePaths[0], app.getPath('userData'),
        path.join(app.isPackaged ? resources : __dirname, 'trusted-models.json'), location.filePaths[0]);
      startupMessage = '公式包已安装。请关闭并重新打开识页，加载新引擎。';
    } finally { importing = false; }
    return settings();
  });
  await win.loadURL(origin);
  win.show();
}
if (!app.requestSingleInstanceLock()) app.quit();
else {
  app.on('second-instance', () => { win?.show(); win?.focus(); });
  app.whenReady().then(boot).catch(error => {
    dialog.showErrorBox('识页启动失败', error.message);
    app.quit();
  });
  app.on('window-all-closed', () => app.quit());
  app.on('before-quit', () => { win = null; stopEngine(); });
}
