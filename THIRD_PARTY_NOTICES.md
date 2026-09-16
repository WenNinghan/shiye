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
| PP-FormulaNet_plus-M / PP-DocLayout_plus-L | 可选模型权重 | 由 PaddleOCR / PaddleX 官方下载流程取得；权重授权需按具体模型来源单独核对，不用框架许可证代替 |
| PyMuPDF / MuPDF | PDF 读取、渲染、搜索层及导出 | [官方 AGPL / 商业双许可说明](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright) |
| python-docx、latex2mathml、mathml2omml | Word 文档与数学结构转换 | [python-docx](https://github.com/python-openxml/python-docx)、[latex2mathml](https://github.com/roniemartinez/latex2mathml)、[mathml2omml](https://pypi.org/project/mathml2omml/) |
| React / Vite / FastAPI | 界面、构建与本机服务 | [React](https://github.com/facebook/react)、[Vite](https://github.com/vitejs/vite)、[FastAPI](https://github.com/fastapi/fastapi) |
| KaTeX / MathLive | 数学排版和可视化编辑 | [KaTeX](https://github.com/KaTeX/KaTeX)、[MathLive](https://github.com/arnog/mathlive) |
| Electron / electron-builder / PyInstaller | Windows 桌面与独立运行时构建 | [Electron](https://github.com/electron/electron)、[electron-builder](https://github.com/electron-userland/electron-builder)、[PyInstaller](https://github.com/pyinstaller/pyinstaller) |

PyMuPDF 官方声明其与 MuPDF 采用 AGPL 与商业许可双授权。仅公开一部分源码不能自动证明所有组合分发义务已满足。因此当前不公开上传包含这些依赖的冻结安装包或模型离线包，也不承诺闭源部署、再分发或商业使用无条件可行。

## 本次公开内容

- 项目编写的 Python / TypeScript / Electron 代码、构建配置、依赖锁文件。
- 使用说明、验收记录、合成演示样例与程序界面截图。
- 样例来自 scripts/make_samples.py 与 web/scripts/make-formula-sample.mjs；不是用户的真实成绩单、课堂聊天或论文扫描件。
- 未上传第三方模型权重、Python/Node 环境、DLL、安装器或系统字体文件。合成 PDF 的字体引用/嵌入仍需在后续素材许可核对中检查；当前公开版本只保留合成 PNG 与生成脚本，PDF 可在用户本地生成。

## 安装包公开前检查

1. 自有源码许可证已确定为 MIT；继续核对与实际依赖组合、打包及部署方式的兼容要求。
2. 核对锁定版本的全部依赖、模型、字体与运行时的分发条款，保留必须的 LICENSE / NOTICE。
3. 按适用条款提供完整对应源码、构建资料与必要通知。
4. 完成干净 Windows 验证，说明签名状态、支持平台和下载校验。

未完成的项目请保留为未完成，不把当前源码公开解释为安装包已获完整分发批准。
