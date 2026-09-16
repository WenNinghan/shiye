# 安装包与模型包公开分发：核对结果及实施方案

日期：2026-09-16。状态：G2 已确认，进入实施。用户明确回复“同意”，批准保留自有源码 MIT、组合程序履行 AGPL-3.0 分发条件的路线；不购买商业授权。

实施更新：材料收集与测试已完成阶段性结果；发现现有 OpenCV 静态链接 IPP 的新增兼容性风险，停止二进制发布。新增无 IPP 的第三方源码构建范围待确认，见 [G3 记录](release-compliance-acceptance.md) 和 [具体阻断与建议](distribution-licensing.md)。下文 G1/G2 保留最初设计记录，不代表仍在等待原路线的确认。

## 1. 当前理解

用户要求处理“安装包、模型包因许可核对尚未完成，暂未公开上传”。上一轮用户明确选择自有源码 MIT，本轮不擅自撤销、替换该授权，也不购买商业许可证。

目标是在保留现有 OCR、公式和导出功能的前提下，补齐分发许可、声明、对应源码和构建资料，重新验包，再发布明确标注的 Windows 测试 Release。不能把修改 README 当作完成包内合规。

## 2. 本轮已经核实的证据

### 2.1 两套模型权重

官方 PaddlePaddle 模型页均标注 Apache-2.0；本轮同时查询 Hugging Face 模型 API 的 revision、cardData.license、LFS SHA-256，并对本地权重实际计算 SHA-256。两者均相等。

| 模型 | 官方 revision | 本地与官方一致的 inference.pdiparams SHA-256 |
| --- | --- | --- |
| PP-FormulaNet_plus-M | 712e6e2e4c313b1ea163be5c350127b82662c58d | f16ef9b5c8227da70d3ec969a5195f4d62c1154427b883f4d6cff07633654041 |
| PP-DocLayout_plus-L | aa52b8528c84f9b1a34ac3a88fe0e576edb9d11d | 24ca3e2e442164505e250deef59f7ee9a54ea12dd32875c9cd6155d959dc97da |

来源：[公式模型](https://huggingface.co/PaddlePaddle/PP-FormulaNet_plus-M)、[版面模型](https://huggingface.co/PaddlePaddle/PP-DocLayout_plus-L)。这是权重来源和许可标识核验，不代表把模型运行时的所有依赖一并判定通过。

### 2.2 现有产物与缺项

- Windows 安装器：216,675,410 字节；公式离线包：859,620,337 字节。保留原内测产物，不原地覆盖。
- 读取 .shiye-model ZIP 目录得到 7,071 项，文件名含 license/copying/notice 的候选项 133 个；其中 cache/ 模型目录的许可说明候选项为 0。不能据“文件多”或“有一些许可证”断言许可已齐全。
- 核心运行目录含 pymupdf/_extra.pyd、_mupdf.pyd、mupdfcpp64.dll；开发环境 pymupdf-1.28.2.dist-info/METADATA 的 License 明确写为 AGPL 3.0 / Artifex 商业双授权。
- 核心目录搜索有 24 个 license/copying/notice 文件名候选；其中搜索 Affero 命中的是 NumPy 许可文件中的相关文字，不是已整理好的 PyMuPDF 完整分发材料。开发 wheel 中 PyMuPDF 的 COPYING 也只是一行双许可说明，不能以复制这一行替代全文和对应源码。
- Electron 目录已有 LICENSE.electron.txt 与 LICENSES.chromium.html，应保留；仍需核对其实际捆绑组件、字体、Python 运行时和原生库的条款。
- mathml2omml 0.0.2 的 METADATA 写 UNKNOWN，但其 LICENSE 正文是 MIT；说明仅用自动元数据标签会误判，需阅读实际文本。
- backend/shiye/recognition.py:7 和 exports.py:6 直接 import pymupdf；并非可简单删除的“无关打包文件”。
- packaging/backend.spec:5 整目录带入 web/dist；desktop/electron-builder.config.cjs:9-10 当前只明确列入应用代码、引擎和模型清单，尚未设计完整分发资料入口。
- scripts/build-desktop.ps1:21、27、29 已有核心/公式构建和可信模型清单生成，可扩展，不需另建一套发布系统。
- 在 packaging/、scripts/ 搜索 collect.*(license|notice)、license.*collect、sbom、corresponding.source，0 命中：未发现现成的许可清单/对应源码收集实现。

### 2.3 字体排查的修正

scripts/make_samples.py:10-16 选择系统字体用于 PNG 绘制；PDF 原生文字部分使用 PyMuPDF 的 china-s 字体，而不是直接把 msyh.ttc 文件传给 PDF 插入接口。不能把“脚本用了微软雅黑绘图”直接断言成“PDF 嵌入了微软雅黑”。下一步应检查最终 PDF 字体对象以及 MuPDF 内置字体许可；当前不将所有字体宣告通过。

## 3. 真正需要作者确认的选择

推荐：**保留自有源码 MIT，包含 PyMuPDF 的组合程序按适用 AGPL-3.0 条件分发**，同时保留 Apache、MIT、BSD 等第三方声明。模型权重按其 Apache-2.0 来源声明，不改成项目 MIT。

这不是把根 LICENSE 换成 AGPL，也不是“加一段免责声明就可以发布”。需准备与最终二进制相匹配的完整对应源码、相关依赖源码、安装/构建脚本、许可正文和用户可访问的源码入口。组合包不能宣传为可仅按 MIT 闭源再分发。

依据：[PyMuPDF 官方双许可说明](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright)、[MuPDF 所附 AGPL 正文](https://github.com/ArtifexSoftware/mupdf/blob/1.28.0/COPYING)、[GNU 许可兼容性说明](https://www.gnu.org/licenses/license-compatibility.en.html)。最终依赖源码版本以实际 wheel 和运行时版本核对，不以示例链接中的 tag 代替。

替代路线：如果作者要求整个分发产品只使用宽松许可依赖，则需要替换 PDF 引擎并重新验证 PDF 读取、文字提取、搜索层、图片 PDF 和导出行为。这是另一项实现，不会未经确认直接重构。

不采用：仅把安装器丢上 Release；只贴上游主页代替对应源码；把冻结 EXE 误当源码；把框架 Apache 许可自动套到所有模型；未经授权购买商业许可。

## 4. G1 复杂度判定

计划涉及下列 16 个受控文件，另有生成的第三方许可与来源清单；本设计不包含功能算法重写。

1. packaging/collect_release_notices.py（新增）
2. packaging/backend.spec
3. packaging/formula.spec
4. desktop/electron-builder.config.cjs
5. scripts/build-desktop.ps1
6. desktop/trusted-models.json
7. web/src/App.tsx
8. web/public/licenses/index.html（新增）
9. docs/distribution-licensing.md（新增）
10. THIRD_PARTY_NOTICES.md
11. README.md
12. docs/release-status.md
13. docs/desktop-acceptance.md
14. licenses/AGPL-3.0.txt（新增）
15. AIAADC/student-projects 的 projects/shiye-WenNinghan/README.md
16. 原开发目录 .ai-governance/capability-map.md

| 条件 | 判定 | 依据 |
| --- | --- | --- |
| H1 ≥5 文件 | 命中 | 上述 16 项 |
| H2 数据库 | 未命中 | 不改数据库结构或文档数据 |
| H3 对外接口 | 未命中 | 不增加业务 API；许可页复用已有静态文件服务 |
| H4 权限认证 | 未命中 | 保留令牌、IPC、资源归属和包验证逻辑，仅重生成包的可信数据 |
| H5 资金计费 | 未命中 | 不购买许可、不新增付费调用 |
| H6 公共模块 | 未命中 | 不改 ≥3 处调用的运行时工具模块，App 指引增加许可入口 |
| H7 新依赖 | 未命中 | 使用现有构建器和标准库收集信息，不新增第三方运行库 |
| H8 跨端协同 | 未命中 | 不改变前后端业务契约，仅打包文件和静态说明 |
| H9 构建部署 | 命中 | 修改 PyInstaller / Electron / 构建脚本 |
| H10 口径待定 | 命中 | 自有源码 MIT 已确定，组合包是否按 AGPL 条件发布待明确确认 |

判定：大型（≥15 文件）；无降级。根据 ai-governance，G2 确认前不改实现代码、不重建、不公开二进制。

## 5. G2 能力复用

已完整阅读原开发目录 .ai-governance/capability-map.md。

| 能力 | 处理 | 入口与边界 |
| --- | --- | --- |
| 前端 | 扩展 | App.tsx 现有使用指南增加静态许可/源码入口；不重做界面 |
| 共享状态与数据结构 | 不涉及 | 保留模型、文档和公式结构 |
| 后端 OCR / 导出 | 复用 | recognition.py、exports.py、formula.py 原样复用 |
| 权限、异常与日志 | 复用 | 不降低桌面双令牌、IPC 限制和包校验 |
| 数据库与合成测试 | 复用 | 既有样例与存储，未经授权的真实文档不进入发行资料 |
| 构建 | 扩展 | 现有 spec、build-desktop.ps1 与 build_model_pack.py 流程加入许可产物；模型包变更重新计算哈希与大小 |
| 文档 | 扩展 | 已有 MIT、THIRD_PARTY_NOTICES、桌面验收与 Release 状态 |
| 分发清单收集 | 新增 | 上述搜索未发现现成实现；需要将实际打包文件、许可证、源码版本和获取地址对应起来，不能只罗列整个开发环境 |

## 6. 实施顺序与范围

1. 锁定源码提交及现有构建环境；从实际产物/Analysis 清单建立运行时物料清单，区分被打包项与仅构建时依赖。
2. 核对核心、公式、Electron/Chromium、Python、原生库及字体；为每个需声明组件保存原始 LICENSE/NOTICE。UNKNOWN 逐项核查，不自动视为禁止或通过。
3. 锁定模型来源 revision 和文件校验；为模型加入 Apache 正文、作者/来源和未修改说明。补说明时不改权重本身。
4. 准备与最终二进制匹配的对应源码材料，包括受适用条款约束的依赖源码、构建补丁和安装说明；对下载来源与覆盖范围逐项验收。不把 GitHub 自动源码 ZIP 等同于全部依赖对应源码。
5. 增加本地可读许可页及固定版本源码入口，保留根 MIT，不额外限制原有 MIT 权利。
6. 用独立新输出目录重建包；重新生成可信模型清单，不绕过哈希验证。发布候选版与原内测包区分，不沿用旧包校验值。
7. 测试许可证可读、模型导入、本地 OCR、公式与导出、退出清理；功能回归使用既有测试。无干净 Windows 环境时明确记录该限制，不把同机测试当跨机器测试。
8. 材料核对通过后创建 GitHub 预发布 Release，包含安装器、模型包、校验文件、对应源码和许可清单；AIAADC 只链接主仓库下载，避免大包重复入 Git。

明确不做：手机端、改模型、换 PDF 库、收费功能、商业许可采购、改变根 MIT、声称未知依赖已通过、声称未签名软件已签名。

## 7. 风险与回滚

- 遗漏传递依赖/原生组件：以打包清单与产物反查，不只读 requirements。
- 模型包改动导致哈希拒绝：最终字节与清单一致后测试；不关闭校验。
- 对应源码不完整：发行阻断，不用免责声明代替缺失材料。
- 字体与示例误判：检查实际 PDF 与字体来源后决定是否随包保留。
- 未签名/干净机未测：在 Release 显著标明；不要求用户关闭安全防护。
- 回滚：旧安装包、原模型与数据保留；代码通过独立提交可回退，不覆盖用户文档，不对仓库或工作区做重置清理。

## 8. 验收标准

| 检查 | 可执行验证 | 当前状态 |
| --- | --- | --- |
| 模型身份与标识 | 官方 API revision/license/LFS 与本地 SHA-256 对比 | 两套权重一致、官方标注 Apache-2.0；不代表运行时完成审查 |
| 许可证材料 | 每个实际组件能对应许可正文、版本、来源；AGPL 材料单列 | 未实施完整收集 |
| 对应源码 | 从最终 Release 下载、校验、解包；覆盖被分发的受约束部分及构建脚本 | 未准备 |
| 包内容 | 解包检查 LICENSE/NOTICE、源码入口、无凭证/用户数据 | 仅完成旧包初步盘点 |
| UI | 打开许可入口，离线正文可读；固定版本源码地址有效 | 未实施 |
| 功能 | 既有后端/桌面测试、全新目录模型导入、真实合成公式与导出 | 本轮尚未重建，旧测试不算新验收 |
| 发布 | GitHub Release 列表与资源字节数/校验一致，资料库下载链接有效 | 未上传；查询尚无 Release |

## 9. 原路线确认记录

用户已回复“同意”：**自有源码继续 MIT，完整组合程序履行 AGPL-3.0 分发条件，模型保留 Apache-2.0，补齐对应源码及许可材料后重新打包并上传测试 Release**。不重复询问此项。

若坚持整套产品仅采用宽松许可依赖，应另选替换 PDF 引擎方案，不能在本方案中静默切换。
