# 0.3.1 对应源码与重建

固定应用源码：Git tag `v0.3.1`，与 Release 的 `Shiye-Source-0.3.1.zip` 对应。
Release 附带的 `SHA256SUMS.txt` 校验各资产；每组依赖归档内还有来源清单。

## 材料分组

- `Shiye-Dependencies-Python-0.3.1.zip`：实际打包清单对应的 113 个 PyPI sdist（含构建工具），原始 `sources.json` 记录版本、官方 URL、大小和 SHA-256。其“五项无 sdist”状态是原始收集结果，由 Supplemental 补齐，不表示遗漏仍未处理。
- `Shiye-Dependencies-Supplemental-0.3.1.zip`：ONNX Runtime、Paddle、FlatBuffers、RapidOCR、latex2mathml、oneDNN 的固定上游源码快照，CPython 3.12.14 官方源码；三个无 sdist 的纯 Python wheel 保留可编辑 `.py` 源码与元数据；补充缺失的许可证正文。
- `Shiye-Dependencies-Native-0.3.1.zip`：完整 MuPDF 1.28.2（含 thirdparty）、GEOS 3.13.1 源码；Paddle 固定的原始 MKLML 2019.0.5 归档是未修改的二进制重建输入，不冒称其为开源源码。
- `Shiye-OpenCV-Builds-0.3.1.zip`：两套无 IPP / FFmpeg 源码、wheel、补丁、CMake 参数和实际构建/验证证据；不包含旧 IPP 检查归档。
- `Shiye-Notices-0.3.1.zip`：原始声明、Python 物料清单、补充许可映射、模型来源及本地可读页面。上游通用声明可能覆盖未打包的可选模块。

这些材料面向审阅、修改和重建；并不是无网络、任意机器可一键重建的完整编译工具链。上游构建脚本内锁定的子模块/下载依赖按其原始步骤取得，不将二进制 wheel 冒称为其原生源码。Electron/Chromium、Python 标准发行组件保留上游声明，Windows 系统组件不重授权。

## Windows 重建顺序

1. 解压应用源码与上述材料。在空间充足的磁盘设置 `TEMP`、`TMP`、npm / Electron / PyInstaller 缓存目录；不要在用户原安装目录中构建。
2. 使用 Python 3.12 x64，为核心和公式分别创建环境。核心环境版本表见 Notices 的 `environments/core-requirements.txt`，公式见 `formula-requirements.txt`。从相应 sdist、源码构建或安装上游相同版本组件；清单是发行环境记录，不声称 PyInstaller/pytest 等元数据项都参与运行。
3. **不能直接使用官方默认 OpenCV wheel 代替本版无 IPP wheel。** 使用 OpenCV-Builds 中相应的 `build-recipe.json`、源码和补丁，或本仓库 `.github/workflows/opencv-no-ipp.yml` / `packaging/build_opencv_no_ipp.py` 重建。两个环境分别安装自己的 wheel，并运行 `packaging/verify_opencv_no_ipp.py`（参数见脚本 `--help`）。
4. `web/` 与 `desktop/` 分别 `npm ci`，以各自 lockfile 锁定的依赖为准。原构建使用 Electron 44.4.1、electron-builder 26.15.3。`desktop/node_modules` 使用物理目录；不要用跨目录 junction 令打包器漏掉传递依赖。
5. 按 `docs/distribution-materials/models.md` 固定 revision 准备两套未修改模型到 `official_models/`。不需要自己的 API、不需要购买额度。
6. 原始 LICENSE、NOTICE 和模型来源放到两个冻结运行时的 `licenses/`；保留网页的离线许可入口。`packaging/collect_release_notices.py` 与 `prepare_release_sources.py` 可重新生成材料；`finalize_release_materials.py` 复用已下载材料生成离线页，具体路径参数见 `--help`。
7. 前端 `npm run build`；核心/公式分别用 `packaging/backend.spec` 与 `packaging/formula.spec` 冻结。模型包用 `build_model_pack.py --version 0.3.1` 生成，再把新的 manifest 通过 `SHIYE_MODEL_MANIFEST` 交给桌面构建器。
8. 设置 `SHIYE_ENGINE_DIR` 指向刚构建的核心，执行 Electron builder `--win nsis --x64 --config.extraMetadata.version=0.3.1`。未配置真实证书时不要声称安装器已签名。
9. 新包的哈希不同是正常的，必须更新本次随安装器分发的可信模型清单；不要关闭哈希、路径与模型启动验证。用户重建的包不应冒充官方原字节包。

`scripts/build-desktop.ps1 -Version 0.3.1` 串联主要构建步骤；公开分发前还须像本版一样把该构建对应的许可和源码资料放入运行时并随 Release 提供，脚本运行成功不自动等于材料准备完毕。

## 本版的组合边界

核心在同一 Python 进程使用 PyMuPDF，按适用 AGPL 条件分发。公式工作进程不加载 PyMuPDF，输入图片路径，输出通用 JSON/LaTeX，可独立启动；没有共享核心内存/内部对象。模型包按其各组件原始许可提供，包括原样保留 Intel MKLML 条款。项目 MIT 不覆盖第三方权利。

GEOS 通过其独立动态库加载，LGPL/Python 组件源码可修改后重新冻结并替换用户自建引擎。本项目不设置禁止调试开源修改的附加条款；模型包的完整性校验是安全措施，维护者/重建者可为自己的发布生成相应清单。

## 验证边界

本版在作者同一台 Windows x64 电脑上使用独立数据目录、冻结 EXE 和已导入模型测试。公式工作进程禁用 Python socket 外连并使用本地缓存；不等同于操作系统断网、第二台干净 Windows 或全部 API 服务商验证。

已知样例：逆矩阵右下角 `a` 被识别为 `d`，需人工改正；Word 原生公式、分式/根号/矩阵结构可以导出，结构正确不等于识别内容全对。
