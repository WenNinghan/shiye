# 桌面公开分发许可核对

2026-09-16 · **部分完成，二进制发布仍被阻断**。根目录自有源码 MIT 不变。

## 已确认的分发路线

作者已同意：自有源码保留 MIT；包含 PyMuPDF 的组合程序履行适用 AGPL-3.0 条件；第三方库与模型保留各自条款；材料齐备并验证后再上传预发布安装包。该同意不等于现有安装包已满足所有条件。

- [AGPL 正文](../licenses/AGPL-3.0.txt)：原样取得自 MuPDF 1.28.2 的 COPYING。
- [Apache-2.0 正文及上游声明](../licenses/Apache-2.0.txt)：原样取得自 Paddle 3.3.1 对应源码提交。
- [模型身份与来源](distribution-materials/models.md)。模型权重的 Apache-2.0 标识不覆盖整个 Paddle 运行时。

## 本轮产物与证据

| 项目 | 实际结果 | 边界 |
| --- | --- | --- |
| Python 物料 | [核心 35 项](distribution-materials/core-inventory.json)、[公式 103 项](distribution-materials/formula-inventory.json) | 与原 PyInstaller Analysis 文件有交集的发行包，不是已经逐项批准的最终 SBOM；可能含仅元数据项 |
| 精确版本源码 | [118 个名称/版本组合](distribution-materials/python-sources.json)，113 个有 sdist，已下载 541,223,090 字节并核对 PyPI SHA-256/大小 | 5 项无 sdist；不以框架主页替代完整对应源码 |
| 原生依赖源码 | MuPDF 1.28.2 官方完整源码包与 GEOS 3.13.1 源码包已取得，见下面校验表 | 仍不代表所有其他原生依赖、构建工具和字体均已覆盖 |
| 许可收集器 | `packaging/collect_release_notices.py` | 按实际 Analysis 项查找安装包所有者，连同许可证目录内部文件一起保留；缺正文保持显式状态 |
| 源码收集器 | `packaging/prepare_release_sources.py` | 只下载并读取归档，不执行其代码；检查来源、大小、SHA-256、路径穿越；网络/完整性错误返回非零 |
| 增量测试 | `python -m unittest discover -s packaging/tests -v`：6/6 通过 | 检查许可目录、EULA、损坏下载、危险路径、无源码包、未知 Analysis 格式；不是新安装包功能验收 |

sdist 缺项：aistudio_sdk 0.3.9、flatbuffers 25.12.19、onnxruntime 1.29.0、paddlepaddle 3.3.1、rapidocr-onnxruntime 1.4.4。其中四个有明确上游 tag，可继续取得源码及子模块；不能因没有 PyPI sdist 就断言无源码或不可分发。

原生源码文件（完整材料现保存在维护者 G 盘构建目录，尚不是公开 Release 资产）：

| 文件 / 官方下载 | SHA-256 |
| --- | --- |
| [mupdf-1.28.2-source.tar.gz](https://mupdf.com/downloads/archive/mupdf-1.28.2-source.tar.gz) | `44075a84e329db55b9bef5f342a70fd26d69e48ad1d33cb89d9664581c641156` |
| [geos-3.13.1.tar.bz2](https://download.osgeo.org/geos/geos-3.13.1.tar.bz2) | `df2c50503295f325e7c8d7b783aca8ba4773919cde984193850cf9e361dfd28c` |

PyMuPDF 的 sdist 不包含 MuPDF 本体。本次另取 MuPDF 完整官方源码归档，枚举到 8,689 项，其中 thirdparty 路径 7,170 项；没有把 GitHub 不含子模块的自动 ZIP 当作相同材料。

## 新发现的发布阻断：OpenCV 静态 IPP

1. 在构建核心程序的环境运行 `cv2.getBuildInformation()`：OpenCV **5.0.0**、`Built as dynamic libs?: NO`、`Intel IPP: 2026.0.0`。`cv2` 与 PyMuPDF 都在核心进程中使用。
2. opencv-python **5.0.0.93** 附带 `cv2/LICENSE-3RD-PARTY.txt:2953` 明示 x86/x64 wheel 静态链接 IPP；`:2971` 起的条款禁止逆向、反编译、反汇编和修改。该文件标题仍写旧版 IPP，不能只依赖此标题判定实际版本。
3. 因此又读取该版本源码的 `opencv/3rdparty/ippicv/ippicv.cmake`：指向 opencv_3rdparty 提交 `406d398c436d0465c8e53dd432d9ecd9301d5f4a` 下的 `ippicv_2026.0.0_win_intel64_20260327_general.zip`。
4. 下载原始归档，MD5 `73bc67cd5e4c8da706fa88fe84630231` 与上游构建文件一致；SHA-256 为 `cf1560b05cc67795852d4ec32ce58ceee466a8d996404af27dfaaea5f1da2760`。内部 `ippicv_win/EULA.rtf` 仍为 **Intel Simplified Software License (October 2022)**，含上述限制。该下载只用于检查，未放进公开仓库或 Release。

据此，不能把“公开应用源码 + 补 AGPL 文本”视为现有核心组合包已具备再分发条件。这里是明确的许可兼容性风险与发布阻断判断，不是法院结论。参考 [Intel 官方条款](https://www.intel.com/content/www/us/en/content-details/749362/intel-simplified-software-license-version-october-2022.html)、[GNU 关于组合许可的说明](https://www.gnu.org/licenses/gpl-faq.en.html#GPLIncompatibleLibs) 和 [PyMuPDF 官方双许可说明](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright)。

**不能用 `cv2.ipp.setUseIPP(False)` 解决分发问题**：关闭运行时加速不会移除已链接的二进制。直接换 `opencv-python-headless` 也不等于关闭 IPP，仍须检查实际构建。

## 建议的下一步（新增构建范围，待确认）

推荐保持 OCR、PDF、公式的业务接口和模型不变，**从锁定源码构建不含 IPP 的 OpenCV wheel**，再重建核心运行时并验证。可以在 GitHub Actions Windows runner 上构建，避免向已接近满盘的本机安装大型 MSVC 工具链。需要新增 CI 配置、第三方 wheel 构建/存档及其验收；原计划仅重打包现有运行时，未包含这项。

验收至少包括：

1. `cv2.getBuildInformation()` 显示 IPP 未启用；核对新 wheel 和最终程序实际使用这一构建，不能只设置环境变量。
2. 保留第三方补丁、编译选项、构建脚本和精确源码；继续核对 FFmpeg、GEOS、Python、Electron/Chromium、Paddle 原生依赖及字体。
3. 若在构建中排除不使用的视频模块/FFmpeg，应记录影响并测试现有图片/PDF 流程，不随意删除运行时 DLL。
4. 新环境通过本地 OCR、英文空格恢复、公式、PDF/Word 导出、模型导入和退出清理回归。
5. 许可材料和对应源码覆盖通过之后，才重生成模型清单、打包和公开预发布资产。

另一条路线是取得所需商业许可或另行改造 PDF 引擎；这两条都不在当前授权范围内，本轮未实施，也没有产生购买或付费调用。

## 当前停止点

已完成材料收集工具、首轮精确版本源码归档、模型来源核对和新风险定位。**未重建 0.3.1 安装器、未修改可信模型哈希、未上传二进制 Release、未把资料库链接改成不存在的下载地址**。旧内测包和用户文档原样保留。许可 UI 和新包功能验收留待解决构建路线后一起完成。
