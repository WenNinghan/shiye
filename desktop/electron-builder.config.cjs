const path = require('node:path');
const fs = require('node:fs');
if (!process.env.SHIYE_ENGINE_DIR) throw new Error('SHIYE_ENGINE_DIR is required');
const engine = path.resolve(process.env.SHIYE_ENGINE_DIR);
if (!fs.existsSync(path.join(engine, 'shiye-engine.exe'))) throw new Error('Frozen engine executable missing');
module.exports = {
  appId: 'org.aiaadc.shiye', productName: '识页', asar: true,
  directories: { output: 'dist' },
  files: ['*.cjs', 'package.json', '!tests/**', '!playwright.config.cjs', '!electron-builder.config.cjs'],
  extraResources: [{ from: engine, to: 'engine' }, { from: 'trusted-models.json', to: 'trusted-models.json' }],
  win: { target: 'nsis', signAndEditExecutable: false, artifactName: 'Shiye-${version}-Windows-x64.${ext}' },
  nsis: { oneClick: false, perMachine: false, allowToChangeInstallationDirectory: true, deleteAppDataOnUninstall: false }
};
