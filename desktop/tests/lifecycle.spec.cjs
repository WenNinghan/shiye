const { test, expect, _electron: electron } = require('@playwright/test');
const fs = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');
test('frozen engine + desktop: local OCR, settings, privacy and clean exit', async () => {
  const root = await fs.mkdtemp(path.join(process.env.SHIYE_TEST_ROOT || os.tmpdir(), 'shiye-desktop-'));
  const app = await electron.launch({ args: process.env.SHIYE_PACKAGED_EXE ? [] : [path.resolve(__dirname, '..')],
    executablePath: process.env.SHIYE_PACKAGED_EXE || undefined,
    env: { ...process.env, SHIYE_DESKTOP_TEST_DATA: root, ELECTRON_DISABLE_SECURITY_WARNINGS: 'false' } });
  let origin;
  try {
    const page = await app.firstWindow();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await expect(page.getByRole('button', { name: '选择文件', exact: true })).toBeEnabled({ timeout: 60000 });
    origin = new URL(page.url()).origin;
    await page.getByRole('button', { name: '使用指南', exact: true }).click();
    await page.getByText('开源许可与源码（离线可读）', { exact: true }).click();
    const licenseFrame = page.frameLocator('iframe[title="开源许可正文"]');
    await expect(licenseFrame.getByRole('heading', { name: '开源许可与源码 · 0.3.1' })).toBeVisible();
    await expect(licenseFrame.locator('body')).toContainText('GNU AFFERO GENERAL PUBLIC LICENSE');
    await page.getByRole('button', { name: '关闭使用指引' }).click();
    await page.getByRole('button', { name: '识别设置', exact: true }).click();
    await expect(page.getByRole('heading', { name: '选择适合你的识别方式' })).toBeVisible();
    await page.getByLabel('完整 API 地址').fill('https://api.example.com/v1/chat/completions');
    await page.getByLabel('模型名', { exact: true }).fill('fake-vision');
    await page.getByLabel('API 密钥', { exact: true }).fill('FAKE-TEST-NOT-A-REAL-KEY');
    await page.getByRole('button', { name: '保存配置，不发送图片' }).click();
    await expect(page.locator('.recognition-dialog').getByRole('status')).toContainText('尚未向 API');
    expect(await fs.readdir(root)).not.toContain('credentials.json');
    await page.getByRole('button', { name: '关闭识别设置' }).click();
    await page.getByRole('button', { name: /用示例体验一下/ }).click();
    await page.getByLabel('识别引擎', { exact: true }).selectOption('api');
    await page.getByRole('button', { name: '开始识别', exact: true }).click();
    await expect(page.getByRole('heading', { name: '确认发送至你的 API' })).toBeVisible();
    await page.getByRole('button', { name: '暂不发送' }).click();
    await page.getByLabel('识别引擎', { exact: true }).selectOption('local');
    await page.getByRole('button', { name: '开始识别', exact: true }).click();
    await expect(page.locator('.block-card').first()).toBeVisible({ timeout: 90000 });
    await page.screenshot({ path: path.join(root, 'desktop-workspace.png'), fullPage: true });
    await page.getByRole('button', { name: '识别设置', exact: true }).click();
    await page.screenshot({ path: path.join(root, 'desktop-settings.png'), fullPage: true });
    await page.getByLabel('API 密钥', { exact: true }).fill('FAKE-ENCRYPTION-TEST-KEY');
    await page.getByRole('checkbox', { name: /使用系统加密记住密钥/ }).check();
    await page.getByRole('button', { name: '保存配置，不发送图片' }).click();
    await expect(page.locator('.recognition-dialog').getByRole('status')).toContainText('尚未向 API');
    const saved = await fs.readFile(path.join(root, 'credentials.json'), 'utf8');
    expect(saved).not.toContain('FAKE-ENCRYPTION');
    const cryptoCheck = await app.evaluate(async ({ safeStorage }, saved) => {
      const { encrypted } = JSON.parse(saved);
      const value = await safeStorage.decryptStringAsync(Buffer.from(encrypted, 'base64'));
      return JSON.parse(value.result).model;
    }, saved);
    expect(cryptoCheck).toBe('fake-vision');
    await page.getByRole('button', { name: '删除 API 配置', exact: true }).click();
    await expect(page.getByRole('button', { name: '删除 API 配置', exact: true })).toBeDisabled();
    await expect.poll(async () => (await fs.readdir(root)).includes('credentials.json')).toBe(false);
    await page.getByRole('button', { name: '关闭识别设置' }).click();
    const fixture = await page.evaluate(async () => {
      const docs = await fetch('/api/documents').then(r => r.json());
      return fetch('/api/documents/' + docs[0].id).then(r => r.json());
    });
    const block = { id: 'c'.repeat(32), kind: 'formula', bbox: [0,0,1,1],
      text: 'x^2+1', latex: 'x^2+1', original_text: 'x^2+1', cells: [],
      source: 'cloud-page', confidence: null, warning: '整页来源', verified: false, display: true };
    fixture.pages[0].candidate_blocks = [block];
    fixture.pages[0].candidate_engine = 'mock-vision';
    await page.route('**/api/documents/' + fixture.id, route => route.fulfill({ json: fixture }));
    await page.route('**/api/documents/' + fixture.id + '/pages/' + fixture.pages[0].id + '/candidate', async route => {
      expect(route.request().postDataJSON().accept).toBe(true);
      fixture.pages[0].blocks = [block]; fixture.pages[0].candidate_blocks = null;
      await route.fulfill({ json: fixture });
    });
    await page.locator('.recent-list button').first().click();
    await expect(page.getByRole('heading', { name: '先审阅，再采用' })).toBeVisible();
    await expect(page.locator('.candidate-preview .katex').first()).toBeVisible();
    await expect(page.locator('.block-card').first()).toBeVisible();
    await page.screenshot({ path: path.join(root, 'api-candidate-mock.png'), fullPage: true });
    await page.getByRole('button', { name: '采用并替换本页' }).click();
    await expect(page.locator('.api-candidate')).toHaveCount(0);
    await expect(page.locator('.block-card .katex').first()).toBeVisible();
    expect(errors).toEqual([]);
    console.log('Evidence directory:', root);
  } finally { await app.close(); }
  if (origin) await expect.poll(async () => {
    try { await fetch(origin + '/api/health', { signal: AbortSignal.timeout(1000) }); return false; }
    catch { return true; }
  }, { timeout: 10000 }).toBe(true);
});

test('abrupt desktop exit releases the private backend', async () => {
  const root = await fs.mkdtemp(path.join(process.env.SHIYE_TEST_ROOT || os.tmpdir(), 'shiye-crash-'));
  const app = await electron.launch({ args: process.env.SHIYE_PACKAGED_EXE ? [] : [path.resolve(__dirname, '..')],
    executablePath: process.env.SHIYE_PACKAGED_EXE || undefined,
    env: { ...process.env, SHIYE_DESKTOP_TEST_DATA: root } });
  const page = await app.firstWindow();
  await expect(page.getByRole('button', { name: '选择文件', exact: true })).toBeEnabled({ timeout: 60000 });
  const origin = new URL(page.url()).origin;
  const mainPid = await app.evaluate(() => process.pid);
  console.log('Crash target pid:', mainPid, 'launcher pid:', app.process().pid);
  process.kill(mainPid, 'SIGKILL');
  await expect.poll(async () => {
    try { await fetch(origin + '/api/health', { signal: AbortSignal.timeout(1000) }); return false; }
    catch { return true; }
  }, { timeout: 15000 }).toBe(true);
});
