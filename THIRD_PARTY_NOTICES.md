# 第三方来源与发布边界

本文件列出主要上游来源，**不是完整 SBOM、法律意见或“许可证全部通过”的证明**。实际直接及传递依赖版本见 backend 的 requirements 文件、web/package-lock.json 和 desktop/package-lock.json。

## 项目自己的许可证

作者 / 维护者：WenNinghan。经作者明确选择，项目自有源码及随附文档采用 [MIT License](LICENSE)，版权署名为 Copyright (c) 2026 WenNinghan。对这些自有内容，可按 MIT 条款使用、复制、修改及分发，不另加“必须先联系作者”的许可条件。

此授权不把第三方依赖、模型、字体或上游素材改成 MIT。包含这些组件的组合软件与部署方式仍需满足各自许可证；尤其不能把根目录的 MIT 文件当成整套含 AGPL 组件安装包可仅按 MIT 分发的证明。

## 主要上游

| 组件 | 用途 | 官方来源 / 许可入口 |
| --- | --- | --- |
| RapidOCR | 本地普通文字识别 | [项目与许可](https://github.com/RapidAI/RapidOCR) |
| ONNX Runtime | 普通 OCR 推理运行时 | [官方项目](https://github.com/microsoft/onnxruntime) |
| PaddleOCR / PaddlePaddle / PaddleX | 公式识别、公式区域定位与运行时 | [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)、[PaddlePaddle](https://github.com/PaddlePaddle/Paddle)、[PaddleX](https://github.com/PaddlePaddle/PaddleX) |
| PP-FormulaNet_plus-M / PP-DocLayout_plus-L | 可选模型权重 | 官方模型卡标注 Apache-2.0，两个权重与固定 revision 的 LFS SHA-256 一致；见[身份与来源记录](docs/distribution-materials/models.md)，不代表整个运行时审查完成 |
| PyMuPDF / MuPDF | PDF 读取、渲染、搜索层及导出 | [官方 AGPL / 商业双许可说明](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright) |
| python-docx、latex2mathml、mathml2omml | Word 文档与数学结构转换 | [python-docx](https://github.com/python-openxml/python-docx)、[latex2mathml](https://github.com/roniemartinez/latex2mathml)、[mathml2omml](https://pypi.org/project/mathml2omml/) |
| React / Vite / FastAPI | 界面、构建与本机服务 | [React](https://github.com/facebook/react)、[Vite](https://github.com/vitejs/vite)、[FastAPI](https://github.com/fastapi/fastapi) |
| KaTeX / MathLive | 数学排版和可视化编辑 | [KaTeX](https://github.com/KaTeX/KaTeX)、[MathLive](https://github.com/arnog/mathlive) |
| Electron / electron-builder / PyInstaller | Windows 桌面与独立运行时构建 | [Electron](https://github.com/electron/electron)、[electron-builder](https://github.com/electron-userland/electron-builder)、[PyInstaller](https://github.com/pyinstaller/pyinstaller) |

PyMuPDF 官方声明其与 MuPDF 采用 AGPL 与商业许可双授权。0.3.1 按作者批准的适用 AGPL 路线提供核心组合、应用源码、依赖源码和重建材料，不承诺闭源再分发无条件可行。公式工作进程与各原生组件保留原许可，详见[实际分发范围](docs/release-license-scope.md)。

2026-09-16 的 OpenCV/IPP 阻断已通过两套无 IPP 源码构建处理，旧包未发布。0.3.1 提供原始声明、113 份 Python sdist、缺项补充源码、MuPDF/GEOS 源码以及 OpenCV 构建材料。历史核对过程保存在[分发记录](docs/distribution-licensing.md)，当前范围以[重建说明](docs/rebuild-0.3.1.md)为准。

## 本次公开内容

- 项目编写的 Python / TypeScript / Electron 代码、构建配置、依赖锁文件。
- 使用说明、验收记录、合成演示样例与程序界面截图。
- 样例来自 scripts/make_samples.py 与 web/scripts/make-formula-sample.mjs；不是用户的真实成绩单、课堂聊天或论文扫描件。
- Git 源码树不保存模型权重、完整 Python/Node 环境、DLL 或安装器；运行时和模型包作为 Release 资产单独提供。不会上传用户成绩单、聊天截图或个人文件。合成示例 PDF 使用 PyMuPDF 内置字体/栅格页面，不分发系统字体文件。

## 安装包公开前检查

1. 自有源码许可证已确定为 MIT；继续核对与实际依赖组合、打包及部署方式的兼容要求。
2. 核对锁定版本的全部依赖、模型、字体与运行时的分发条款，保留必须的 LICENSE / NOTICE。
3. 按适用条款提供完整对应源码、构建资料与必要通知。
4. 说明签名状态、支持平台和下载校验。本次为未签名预发布，同机测试已做，另一台干净 Windows 验证仍未完成。

未完成的项目请保留为未完成，不把当前源码公开解释为安装包已获完整分发批准。
