const { isIP } = require('node:net');
function assertSender(event, webContents, origin) {
  if (event.sender !== webContents || event.senderFrame !== webContents.mainFrame ||
      new URL(event.senderFrame.url).origin !== origin) throw new Error('拒绝非应用页面调用');
}
function validateProfile(value) {
  if (!value || typeof value !== 'object') throw new Error('设置格式错误');
  let url;
  try { url = new URL(value.endpoint); } catch { throw new Error('请填写完整 HTTPS API 地址'); }
  if (url.protocol !== 'https:' || url.username || url.password || url.hash ||
      url.search || url.port && url.port !== '443' || isIP(url.hostname) ||
      !url.hostname.includes('.') || url.hostname.length > 253 ||
      /(^|\.)(localhost|local|internal|test|invalid)$/.test(url.hostname))
    throw new Error('仅支持公网 HTTPS API 地址，不支持内网、查询参数或 URL 凭证');
  if (typeof value.model !== 'string' || !value.model.trim() || value.model.length > 200)
    throw new Error('请填写图片模型名');
  if (typeof value.key !== 'string' || !value.key.trim() || value.key.length > 4096 || /[\r\n]/.test(value.key))
    throw new Error('请填写有效密钥');
  return { endpoint: url.href, model: value.model.trim(), key: value.key.trim(), remember: value.remember === true };
}
module.exports = { assertSender, validateProfile };
