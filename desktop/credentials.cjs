const fs = require('node:fs/promises');
const path = require('node:path');
class CredentialStore {
  constructor(folder, storage) { this.file = path.join(folder, 'credentials.json'); this.storage = storage; }
  async save(profile) {
    if (!profile.remember) { await this.clear(); return; }
    const storage = this.storage;
    if (!storage.isAsyncEncryptionAvailable || !await storage.isAsyncEncryptionAvailable())
      throw new Error('系统加密暂不可用，请取消“记住密钥”后重试');
    const ciphertext = await storage.encryptStringAsync(JSON.stringify(profile));
    await fs.mkdir(path.dirname(this.file), { recursive: true });
    await fs.writeFile(this.file + '.new', JSON.stringify({ v: 1, encrypted: ciphertext.toString('base64') }), { mode: 0o600 });
    await fs.rename(this.file + '.new', this.file);
  }
  async load() {
    try {
      const data = JSON.parse(await fs.readFile(this.file, 'utf8'));
      if (data.v !== 1 || !this.storage.isAsyncEncryptionAvailable || !await this.storage.isAsyncEncryptionAvailable())
        throw new Error('凭证暂不可解密');
      const decrypted = await this.storage.decryptStringAsync(Buffer.from(data.encrypted, 'base64'));
      return JSON.parse(decrypted.result);
    } catch (error) {
      if (error.code === 'ENOENT') return null;
      // Never replace unreadable ciphertext with plaintext or silently delete it.
      throw new Error('已保存密钥无法读取，请在设置中重新配置或删除');
    }
  }
  async clear() { await fs.rm(this.file, { force: true }); }
}
module.exports = { CredentialStore };
