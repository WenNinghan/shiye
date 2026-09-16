const path = require('node:path');
const fs = require('node:fs');
if (!process.env.SHIYE_ENGINE_DIR) throw new Error('SHIYE_ENGINE_DIR is required');
const engine = path.resolve(process.env.SHIYE_ENGINE_DIR);
if (!fs.existsSync(path.join(engine, 'shiye-engine.exe'))) throw new Error('Frozen engine executable missing');
const modelManifest = process.env.SHIYE_MODEL_MANIFEST || path.join(__dirname, 'trusted-models.json');
if (!fs.existsSync(modelManifest)) throw new Error('Trusted model manifest missing');
module.exports = {
  appId: 'org.aiaadc.shiye', productName: '识页', asar: true,
  directories: { output: 'dist' },
  files: ['*.cjs', 'package.json', '!tests/**', '!playwright.config.cjs', '!electron-builder.config.cjs'],
  extraResources: [{ from: engine, to: 'engine' }, { from: modelManifest, to: 'trusted-models.json' }],
  win: { target: 'nsis', signAndEditExecutable: false, artifactName: 'Shiye-${version}-Windows-x64.${ext}' },
  nsis: { oneClick: false, perMachine: false, allowToChangeInstallationDirectory: true, deleteAppDataOnUninstall: false }
};
