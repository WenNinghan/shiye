# 无 IPP 的 OpenCV 云端构建（G2 增量）

2026-09-16，用户回复“好的”，已确认新增 GitHub Actions 构建路线。本文件细化已确认方案，不重复请求确认。

## 范围与判定

计划文件：`.github/workflows/opencv-no-ipp.yml`、`packaging/build_opencv_no_ipp.py`、`packaging/verify_opencv_no_ipp.py`、`packaging/tests/test_opencv_build.py`、本文、`docs/distribution-licensing.md`、`docs/release-status.md`、原开发工作区能力地图。

| 条件 | 判定与依据 |
| --- | --- |
| H1 | 命中，8 个文件 |
| H2 | 未命中，不改数据库 |
| H3 | 未命中，不改业务 API |
| H4 | 未命中，不改应用认证；CI 仅声明 contents:read，不授予仓库写权限 |
| H5 | 未命中，不开通付费产品、购买许可或调用付费 API |
| H6 | 未命中，不改共享业务模块 |
| H7 | 命中，新增 GitHub Actions 构建服务及构建工具，不增加应用运行库 |
| H8 | 未命中，不改前后端契约 |
| H9 | 命中，新增 CI 与构建脚本 |
| H10 | 未命中，新增构建路线已获确认 |

判定中等，未降级；属于已批准的大型分发任务的构建子阶段。

## 现状、复用与边界

已完整阅读原开发目录 `.ai-governance/capability-map.md`。`rg --files .github` 报目录不存在；`scripts/build-desktop.ps1` 只调用现成依赖的 PyInstaller/Electron，故新增上游 wheel 构建入口，保留原桌面流程。

- 复用 `docs/distribution-materials/python-sources.json` 中的准确源包 URL、字节数、SHA-256；不跟随上游最新分支。
- 复用 `backend/requirements-lock.txt`、`backend/tests` 和公开合成样例；不上传真实用户文件。
- 普通 OCR 使用 opencv-python 5.0.0.93；公式环境使用 opencv-contrib-python 4.10.0.84。分开的 job/环境构建，避免共用 cv2 命名空间。
- 新增：编译和构建结果验证脚本、手动 CI、测试及构建证据包。前端、业务服务、数据库和权限不涉及；日志/源码材料扩展现有分发流程。
- 不采用：只禁用 IPP 运行时开关；直接改装未知 headless wheel；更换 PDF 引擎；本机安装大型 MSVC 工具链。

## 构建与验证设计

1. 手动 `workflow_dispatch`，标准 windows-2022 runner、Python 3.12，actions 固定提交；只读仓库权限、不保存 checkout 凭证、不使用项目 secrets、不自动发布 Release。
2. 下载并核对已经锁定的 PyPI 源归档；`tarfile` data filter 解包；安装明确版本的构建工具，在全新 runner 内编译。保留源归档、实际 pip freeze、CMake 缓存、构建日志、SHA-256 和修改说明。
3. 编译禁用 `WITH_IPP`、`WITH_IPP_IW`、`WITH_FFMPEG`；禁用无关 OBSENSOR 下载。保留图片和矩阵处理，不以删除 DLL 伪装重新编译。
4. 从生成 wheel 安装并检查：版本、架构、构建报告、IPP 查询、CMake 缓存、wheel 内是否包含 IPP/FFmpeg 二进制；执行真实图像处理冒烟测试。缺少证据或发现启用即失败。
5. 核心 job 安装原有锁定依赖（跳过官方 OpenCV wheel），再运行后端测试和合成通知页 RapidOCR。公式 job 验证 contrib wheel；真实 Paddle 模型与最终冻结程序测试留到下载候选轮子后的重打包阶段。
6. 成功才上传 wheel 候选及源码证据；失败仅保存日志，不将未验证 wheel 当成可发布产物。Actions 工件有保存期限，不替代最终永久 Release 的对应源码。

## 风险、回滚与验收

构建耗时/外部下载失败：每 job 180 分钟上限，最多两个并行 job，手动触发；失败读取实际日志修复，不无限重跑。MSVC/runner 镜像非逐位固定，保留环境版本，不声称可逐位复现。移除 IPP 可能改变速度和数值细节，需要 OCR 回归，不能只检查编译完成。

只上传构建候选到 Actions，不立即替换现有开发环境或公开安装包；旧运行时和模型包可继续回退。验收分开报告本地工具单测、云端编译、云端功能和最终包功能，不互相代替。所有后续原生依赖许可审查仍需完成。

## 首轮执行记录

已触发 run `35078797797`。本地与云端的 10 项工具单测通过。公式 job 在加载 setuptools 59.2.0 的构建后端时失败（`Cannot import setuptools.build_meta`），尚未编译；核心使用 setuptools 69.5.1 已进入构建。修正公式构建工具为 69.5.1，通过 `--no-build-isolation` 使用明确记录的构建环境；不修改上游算法源码。新增单环境重试选项，仅重跑失败的公式 job，不取消正在进行的核心编译。

公式定向重试为 run `35079017321`，已经进入构建步骤。原 run 仍有失败的历史公式 job，不能把原 run 的整体红色状态直接当作核心 job 的结论；分别查看：

- [核心 job](https://github.com/WenNinghan/shiye/actions/runs/35078797797/job/104737515359)
- [修正后的公式 run](https://github.com/WenNinghan/shiye/actions/runs/35079017321)

### G3 分阶段状态

| 项目 | 验证 / 实际结果 |
| --- | --- |
| 工具单测 | 本地执行 `python -m unittest discover -s packaging/tests -v`，10/10 通过；首轮两套 runner 的同一步骤均通过 |
| 工作流接入 | GitHub 已接受并启动手动触发，使用标准 Windows runner；仓库只读权限、未配置 secrets、无 Release 写入步骤 |
| 核心/公式源码编译 | 更新记录时两者均为 in_progress；这不是编译成功或产物验收通过 |
| 最终应用 | 未换本机 wheel，未重新冻结，未跑新版桌面完整测试；下一阶段必须继续 |

在 Actions 页面选择 `Run workflow`，`variant=both` 可构建两套；`core` 或 `formula` 用于有明确修正后的单环境重试。下载成功 job 的 `opencv-*-no-ipp-windows-x64` 工件：wheel、原始源码、编译参数、CMake 缓存、环境、日志及验证报告一并保留。失败工件后缀为 `-failure`，只含诊断资料，不是安装包。

工件到期会删除，最终公开分发前仍需把适用源码与材料移到永久 Release，并核对所有第三方条款。构建候选不自动等于整个产品分发通过。

## 构建失败修复设计（截图反馈后）

实查两个 run 已失败，不再沿用上面的运行中快照。核心 job 日志为 `LNK1181 ... SgemmKernelSse2.obj`；公式重试 job 日志为 `Not found: 'bin/opencv_videoio_ffmpeg\\d{4}_64\\.dll'`。前者是 MLAS 汇编链接，后者是在 CMake 安装后由 setup.py 文件分类器强制寻找被禁用的 FFmpeg。

本次属于已确认 CI 的修复：涉及构建脚本、验证脚本、工具测试、工作流工件列表、本文/发布状态与原能力地图；H1/H9 命中，其余 H2–H8（H9 除外）及 H10 未命中，判定中等，不新增服务/运行库，不改应用接口、权限或数据库。已重读能力地图，复用原下载、编译、证据与校验能力，不另建构建体系。

修复方案：核心通过 CMake `CMAKE_ASM_COMPILER=NOTFOUND` 走该锁定版本 MLAS CMakeLists 中已经提供的 DNN 内建 SGEMM 回退；不删除 DNN 模块，不修改识别算法。两套源包仅对 setup.py 的 FFmpeg 额外文件条目作精确、拒绝未知版本的修补，与 WITH_FFMPEG=OFF 一致。保留原归档、统一差异补丁和修补后哈希。不要重新启用 FFmpeg/IPP 来绕过打包失败，也不要忽略失败直接上传 wheel。

验收：工具测试 + 对两份真实源包的修补/语法检查；重新运行两套云端构建；核对实际无 IPP/FFmpeg、核心 MLAS 已回退、图片处理和后端回归。云端结果未出之前只称修复已提交/重跑，不称构建通过。

### 本次修复的阶段验收

- `python -m unittest discover -s packaging/tests -v`：13/13 通过。
- 两份锁定的真实 sdist 再核对 SHA-256/大小后，仅将 setup.py 中强制 FFmpeg 文件列表改为 `[]`；生成的统一差异均为单行修改，语法编译检查通过。未执行上游 setup.py 进行该离线检查。
- 改动提交 `5aeb0bf86e02691c493cd6342ae2f1eb7856aadd`，已启动[第三次运行 35081772275](https://github.com/WenNinghan/shiye/actions/runs/35081772275)，包含 core/formula 两个 job；结果以该运行页为准。
- 旧运行仍显示红叉是历史结果，并非新运行状态。未取得新运行成功结果前，不宣称已完成云端验收或安装包发布。

## 完整离线路线与测试入口修复

用户选择“完整离线”：继续已有本地文字/公式运行时和文档导出，不改成必须调用 API，不更换 PDF 引擎。本节为已批准构建方案内的定向修复。

`gh run view 35081772275 --json jobs` 已确认公式 job 成功并保存候选；核心源码编译及实际 wheel 校验也成功，失败发生在后端测试收集：`ModuleNotFoundError: No module named 'shiye'`。工作流从仓库根运行 `-o pythonpath=backend`，而 pytest 的配置根是 backend，导致相对路径重复。不是新的编译失败。

G1：本次涉及工作流、本文、发布状态三份逻辑文件（同步原开发副本不新增设计范围）；H9 命中。H1 未命中（3 份），H2/H3/H4/H5 未命中（不改数据库、业务接口、认证或计费），H6/H7/H8 未命中（不改共享业务模块、不加依赖、不改跨端契约），H10 未命中（用户已明确完整离线）。判定中等，沿用已确认 G2。

G2：已核对原能力地图，复用现有 backend/pyproject.toml 的 `pythonpath=["."]` 与 backend/tests。在 backend 目录执行测试，JUnit 输出到上级 candidate；用 finally 恢复工作目录，保留随后真实 OCR 校验。应用界面、服务、数据和权限均不涉及；仅扩展本构建记录。不采用更换 PDF 栈、跳过测试或重复构建成功的公式 job。风险是 CI 环境仍可暴露其他运行问题；失败按实际日志处理，不把本地通过当云端通过。回滚仅恢复此测试调用。

验收：在发布仓库 backend 目录执行同一测试命令，确认 44 项既有用例；执行 13 项材料/构建工具单测；仅触发 core 构建并分别记录云端结果。公式候选下载保存到 G 盘用于后续整合，但候选成功不代表已完成模型推理、冻结程序或整包断网验收。

本地 G3：修正后的 `python -m pytest tests -q --junitxml=...` 在发布仓库 backend 目录运行，44 passed（15.23 秒，2 条上游弃用警告）；`python -m unittest discover -s packaging/tests -v` 为 13/13 通过；`git diff --check` 通过。本机使用现有开发环境，这些结果不替代新 wheel 的云端回归和整包断网测试。
