const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const { validateProfile, assertSender } = require('../security.cjs');
const { CredentialStore } = require('../credentials.cjs');
const { safeEntry } = require('../model-packs.cjs');
const valid = { endpoint: 'https://api.example.com/v1/chat/completions', model: 'vision', key: 'fake-only', remember: false };
test('profile rejects local addresses and unsafe URL components', () => {
  assert.equal(validateProfile(valid).model, 'vision');
  for (const endpoint of ['http://api.example.com','https://127.0.0.1/v1','https://x.local/api','https://u:p@api.example.com','https://api.example.com?a=b','https://api.example.com:9443/v1'])
    assert.throws(() => validateProfile({ ...valid, endpoint }));
});
test('IPC accepts only the main frame of the actual application window', () => {
  const frame = { url: 'http://127.0.0.1:8769/' }, wc = { mainFrame: null }; wc.mainFrame = frame;
  assert.doesNotThrow(() => assertSender({ sender: wc, senderFrame: frame }, wc, 'http://127.0.0.1:8769'));
  assert.throws(() => assertSender({ sender: {}, senderFrame: frame }, wc, 'http://127.0.0.1:8769'));
  assert.throws(() => assertSender({ sender: wc, senderFrame: { url: frame.url } }, wc, 'http://127.0.0.1:8769'));
});
test('model paths reject traversal, ADS and links', () => {
  for (const fileName of ['../x','/x','C:/x','runtime/a:stream','runtime/../x','runtime/a\\b','runtime/b.'])
    assert.throws(() => safeEntry(path.resolve('temp'), { fileName, externalFileAttributes: 0 }));
  assert.throws(() => safeEntry(path.resolve('temp'), { fileName: 'link', externalFileAttributes: 0xa000 << 16 }));
});
test('remember is explicit and encryption failure never writes plaintext', async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'shiye-vault-test-'));
  const store = new CredentialStore(root, { isAsyncEncryptionAvailable: async () => false });
  await assert.rejects(store.save({ ...valid, remember: true }));
  assert.deepEqual(await fs.readdir(root), []);
  await store.save(valid); assert.equal(await store.load(), null);
  await fs.rmdir(root);
});
