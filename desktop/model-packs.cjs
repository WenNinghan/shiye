const fs = require('node:fs/promises');
const { createReadStream, createWriteStream } = require('node:fs');
const path = require('node:path');
const { createHash, randomUUID } = require('node:crypto');
const { pipeline } = require('node:stream/promises');
const { spawn } = require('node:child_process');
const yauzl = require('yauzl');

function safeEntry(root, entry) {
  const name = entry.fileName;
  const mode = entry.externalFileAttributes >>> 16;
  if (name.includes('\\') || name.includes(':') || name.startsWith('/') || name.includes('\0') ||
      name.split('/').some(part => part === '..' || part === '.' || /[. ]$/.test(part)) ||
      (mode & 0xf000) === 0xa000)
    throw new Error('模型包含不安全路径');
  const destination = path.resolve(root, name);
  if (!destination.startsWith(path.resolve(root) + path.sep)) throw new Error('模型包路径越界');
  return destination;
}
async function sha256(file) {
  const hash = createHash('sha256');
  for await (const chunk of createReadStream(file)) hash.update(chunk);
  return hash.digest('hex');
}
async function extract(file, root, maxBytes) {
  const zip = await new Promise((resolve, reject) => yauzl.open(file, { lazyEntries: true, autoClose: true },
    (error, value) => error ? reject(error) : resolve(value)));
  return new Promise((resolve, reject) => {
    let total = 0, count = 0, failed = false;
    function fail(error) { if (!failed) { failed = true; zip.close(); reject(error); } }
    zip.on('error', fail); zip.on('end', resolve);
    zip.on('entry', async entry => {
      try {
        if (++count > 100000 || (total += entry.uncompressedSize) > maxBytes)
          throw new Error('模型包解压体积超限');
        const destination = safeEntry(root, entry);
        if (entry.fileName.endsWith('/')) await fs.mkdir(destination, { recursive: true });
        else {
          await fs.mkdir(path.dirname(destination), { recursive: true });
          const source = await new Promise((resolve, reject) => zip.openReadStream(entry, (error, stream) => error ? reject(error) : resolve(stream)));
          await pipeline(source, createWriteStream(destination, { flags: 'wx' }));
        }
        if (!failed) zip.readEntry();
      } catch (error) { fail(error); }
    });
    zip.readEntry();
  });
}
async function probe(root) {
  await new Promise((resolve, reject) => {
    const child = spawn(path.join(root, 'runtime', 'shiye-formula.exe'), ['--warm'], {
      cwd: root, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'],
      env: { ...process.env, PADDLE_PDX_CACHE_HOME: path.join(root, 'cache'),
        PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK: 'True', PYTHONUTF8: '1' }
    });
    let output = '';
    child.stdout.on('data', chunk => { output = (output + chunk.toString()).slice(-65536); });
    child.stderr.on('data', () => {});
    const timer = setTimeout(() => { child.kill(); reject(new Error('公式包启动验证超时；旧模型保持不变')); }, 300000);
    child.once('error', () => { clearTimeout(timer); reject(new Error('公式引擎无法启动')); });
    child.once('exit', code => {
      clearTimeout(timer);
      try {
        const data = JSON.parse(output.trim().split('\n').at(-1));
        if (code !== 0 || !data.ok || !data.result?.model_cached) throw new Error();
        resolve();
      } catch { reject(new Error('公式包实际加载失败；旧模型保持不变')); }
    });
  });
}
async function importModelPack(file, userRoot, manifestPath, storageRoot = userRoot) {
  const manifest = JSON.parse(await fs.readFile(manifestPath, 'utf8'));
  const stat = await fs.stat(file);
  if (stat.size > 8 * 1024 ** 3) throw new Error('模型包过大');
  const digest = await sha256(file);
  const trusted = manifest.packs.find(pack => pack.sha256 === digest && pack.bytes === stat.size &&
    pack.platform === process.platform && pack.arch === process.arch);
  if (!trusted) throw new Error('此模型包未在当前版本的可信清单中，或文件已损坏');
  const models = path.join(path.resolve(storageRoot), 'shiye-models');
  await fs.mkdir(models, { recursive: true });
  const disk = await fs.statfs(models);
  if (disk.bavail * disk.bsize < trusted.unpackedBytes + 512 * 1024 ** 2)
    throw new Error('模型目录空间不足；至少需要 ' + Math.ceil((trusted.unpackedBytes + 512 * 1024 ** 2) / 1024 ** 3) + ' GB 可用空间');
  const stage = path.join(models, 'pack-' + randomUUID());
  await fs.mkdir(stage);
  try {
    await extract(file, stage, trusted.unpackedBytes);
    await probe(stage);
    const data = path.join(userRoot, 'data');
    await fs.mkdir(data, { recursive: true });
    const config = { executable: path.join(stage, 'runtime', 'shiye-formula.exe'),
      cache: path.join(stage, 'cache'), model: 'PP-FormulaNet_plus-M', device: 'cpu' };
    await fs.writeFile(path.join(data, 'formula-runtime.json.new'), JSON.stringify(config), 'utf8');
    await fs.rename(path.join(data, 'formula-runtime.json.new'), path.join(data, 'formula-runtime.json'));
  } catch (error) {
    // Only remove this newly created staging directory, never user data or old packs.
    if (path.dirname(stage) === models) await fs.rm(stage, { recursive: true, force: true });
    throw error;
  }
}
module.exports = { importModelPack, safeEntry, extract };
