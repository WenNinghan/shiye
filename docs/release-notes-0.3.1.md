# 识页 0.3.1 · Windows 离线预发布版

把截图、讲义和论文页面变成可校对、可编辑的 Word / Markdown / PDF。默认在自己的电脑识别，不依赖作者电脑，不需要 API 密钥。

## 普通用户只需这两个文件

1. **`Shiye-0.3.1-Windows-x64.exe`**（约 202 MB）：Windows x64 安装器，已包含文字 OCR 与运行环境，不用另装 Python、Node 或 Office。
2. **`Shiye-Formula-0.3.1-Windows-x64.shiye-model`**（约 847 MB）：需要识别数学公式时下载。在应用“识别设置 → 导入公式离线包”中选择它，并选择空间充足的模型保存盘，建议预留至少 3 GB。导入成功后重启应用。

随后：选图片/PDF → 开始识别 → 对照原图校对 → 生成并下载。可先点“用示例体验一下”。公式默认显示数学排版，可以直观编辑，常见结构可导出为 Word 原生公式。

下载和首次安装/导入准备好后，本机识别、校对、导出无需网络。自己的 API 是可选联网功能，只有明确确认后才发送所选图片，费用由使用者与服务商结算。

## 重要说明

- **未签名 Pre-release**。请核对本仓库来源和 `SHA256SUMS.txt`，不要关闭安全防护。尚未在另一台干净 Windows 电脑或操作系统全局断网环境测试。
- 公式必须人工校对：合成样例的逆矩阵右下角 `a` 仍可能识别成 `d`。能漂亮排版不等于识别正确。
- 文档默认暂存 24 小时，请及时导出；请勿在问题反馈中上传个人成绩单、身份证、密钥或未授权材料。
- 仅 Windows x64；没有安卓/iPhone 安装包，也不是公网在线网站。

## 开发者 / 许可材料

普通使用不必下载以下源码归档：

- `Shiye-Source-0.3.1.zip`：对应应用源码、构建脚本和锁定依赖。
- `Shiye-Dependencies-Python-0.3.1.zip`：113 份精确版本 PyPI sdist 与来源校验清单。
- `Shiye-Dependencies-Supplemental-0.3.1.zip`：补充的固定上游源码、Python 源码及纯 Python wheel 源文件。
- `Shiye-Dependencies-Native-0.3.1.zip`：MuPDF / GEOS 源码及未修改的 MKLML 二进制重建输入。
- `Shiye-OpenCV-Builds-0.3.1.zip`：两套无 IPP OpenCV 源码、补丁、构建参数、wheel 与验证证据。
- `Shiye-Notices-0.3.1.zip`：原始声明、物料/许可映射、模型来源和离线阅读页。

自有源码 MIT 保留；含 PyMuPDF 的核心组合依适用 AGPL v3 条件分发。模型和公式工作进程依各原始条款分发，不能把全部第三方改标为 MIT。[许可范围](https://github.com/WenNinghan/shiye/blob/v0.3.1/docs/release-license-scope.md) · [源码/重建说明](https://github.com/WenNinghan/shiye/blob/v0.3.1/docs/rebuild-0.3.1.md) · [详细使用说明](https://github.com/WenNinghan/shiye/blob/v0.3.1/docs/desktop-guide.md)。

## 本次测试

44 项后端、15 项打包材料、4 项桌面安全、2 项最终桌面端到端测试通过；新公式包已实际导入，冻结程序识别 3 个公式并导出 Word。[验收记录及边界](https://github.com/WenNinghan/shiye/blob/v0.3.1/docs/release-acceptance-0.3.1.md)。
