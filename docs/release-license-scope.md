# 识页 0.3.1：许可、源码与再分发

识页自有源码由 WenNinghan 以 MIT 发布，根 LICENSE 保持不变。
无任何担保；文字和公式识别结果需要人工核对。

包含 PyMuPDF / MuPDF 的核心组合程序依适用的 GNU AGPL v3 条件分发，
不能仅凭项目 MIT 声明把整个核心二进制视为可闭源再分发。
AGPL 正文和原作者声明随包保存。修改并对外提供网络服务时，
还需遵守 AGPL 对访问该服务的用户提供相应源码的要求。

公式包是独立进程的图像到 LaTeX 工具，使用 Paddle、PaddleOCR、PaddleX
和两套 Apache-2.0 模型；通过图像路径/JSON/LaTeX 与核心通信，不共享
PyMuPDF 代码或内存。其原始第三方组件分别遵循各自条款，不能把整个
公式运行时或 Intel DLL 改标为 Apache 或 MIT。Paddle 所附未修改
MKLML / OpenMP DLL 保留 Intel Simplified Software License (April 2018)
及 third-party-programs.txt；该专有组件的限制不扩展到识页的开源代码。

OpenCV 为源码重建版本，核心 5.0.0.93、公式 4.10.0.84，均不含 IPP。
构建参数、原始源码、补丁、wheel 和实际 build-information 随发布提供。
上游通用 NOTICE 可能提到本次未启用的组件，以实际构建信息为准。

其他组件包括 Electron/Chromium、Python、NumPy/SciPy、GEOS、PDFium、
KaTeX/MathLive 等，保留原始许可/版权/例外文本，不统一替换为 MIT。
LGPL/MPL 组件的原始源码、版本及构建说明随源码材料提供；本项目不
额外限制用户为调试其修改而采取的、适用开源许可允许的行为。

固定版本源码与下载：
https://github.com/WenNinghan/shiye/releases/tag/v0.3.1
https://github.com/WenNinghan/shiye/tree/v0.3.1

Release 的 Shiye-Source-0.3.1.zip 是应用对应源码；Dependencies-Python、
Dependencies-Native、Dependencies-Supplemental、OpenCV-Builds 与 Notices
资产包含依赖源码/原始声明/重建材料。各归档内 sources.json 保留上游
精确版本、URL 与 SHA-256。上游源码自己的第三方下载/子模块构建流程
仍以其锁定版本脚本为准；这不是保证任意电脑都可断网从源码重建的 SDK。
“完整离线”指下载安装器和公式包后，识别/校对/导出不需要联网。

Windows/微软系统运行库按适用系统组件条款使用，不声称拥有其源码。
未签名测试版不要求关闭系统安全防护；请核对 GitHub 来源和 SHA256SUMS。
