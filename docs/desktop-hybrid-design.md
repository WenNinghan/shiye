# 识页 Windows 混合桌面版：实现前设计

- 类型：G2 实现前设计
- 来源：用户希望不依赖作者电脑，支持用户自主接 API，或将模型与环境一起安装到用户端；最新指示“好的，去做吧”。
- 日期：2026-09-16
- 复杂度：大
- 状态：**已实施内部测试版；G3 本机验证完成，外部验收待补**
- 确认证据：用户于本方案之后回复“做完这个再做手机端”。先实现本设计的 Windows 版，再进入手机端设计与实施，不把手机端算作已完成。
- G1/G2 已完成；本轮开始实施及 G3 验证。

## 一、当前理解与首版边界

让同学下载安装后双击使用，无需自己安装 Python、Node、运行命令行，也不依赖作者电脑开机。先做 Windows x64 CPU 桌面版：现有本地识别为默认，用户可选配置自己的图片识别 API；继续使用同一套校对、公式显示、Word/Markdown/PDF 导出。

首版交付：核心安装包、可导入的公式离线扩展包、包含二者的离线发布目录、源码与测试记录。核心本地 OCR 自带必要模型；公式包包含独立运行环境、公式模型和版面模型，导入后断网可用。首版不依赖尚不存在的下载服务器；在线一键下载待有正式发布地址后接入，先做“选择离线包并安装”。

这里的“无需作者电脑开机”不是“无需任何电脑”：桌面识别仍在使用者电脑运行。网站、手机应用和托管云推理不在本轮。

## 二、G1 复杂度判定

| 硬条件 | 命中 | 依据 |
| --- | --- | --- |
| H1 文件 ≥5 | 是 | 下列具体清单共 39 个计划涉及文件，含文档、锁文件与测试 |
| H2 数据库结构 | 否 | 沿用 sessions/documents/exports 表；只给 documents.body JSON 增加有默认值的引擎元数据，无 SQL 表结构迁移 |
| H3 接口 | 是 | main.py 的启动/会话/健康响应扩展；新增受保护配置控制面、API 识别设置与检测 |
| H4 权限/鉴权 | 是 | 桌面运行令牌、私有控制面、密钥保护和云端发送授权 |
| H5 资金/计费 | 是（保守） | 虽无平台支付业务，BYOK 调用会消耗用户供应商额度；重复调用和重试会影响费用 |
| H6 公共模块 | 是 | models.py 被 formula/main/recognition/worker/store/tasks 六个后端模块引用；保持旧字段兼容 |
| H7 新依赖 | 是 | Electron、electron-builder、PyInstaller，以及后端网络请求库 |
| H8 跨端 | 是 | React、Electron 主进程和 Python 后端协作 |
| H9 构建/部署 | 是 | 新安装包、独立运行时、模型包及资源路径 |
| H10 业务口径不明 | 是 | 首版系统、API 协议与离线包交付粒度需本设计确认；建议值已给出 |

命中 9 条，文件 39 个，判定为“大”。无用户要求降级，不跳过 G2 确认或 H4/H5 风险与回滚。

### 具体文件清单

文件名是计划边界，不表示已经新增或修改；生成的 dist、模型二进制不计为逐个代码文件。若实施发现需要扩大产品或安全边界，另行说明。

| # | 文件 | 处理 | 用途 |
| --- | --- | --- | --- |
| 1 | `desktop/package.json` | 新增 | 桌面依赖和构建命令 |
| 2 | `desktop/package-lock.json` | 新增 | 锁定构建依赖 |
| 3 | `desktop/main.cjs` | 新增 | 窗口、子进程、下载、生命周期 |
| 4 | `desktop/preload.cjs` | 新增 | 窄权限 IPC 桥 |
| 5 | `desktop/security.cjs` | 新增 | IPC 来源、URL、窗口安全策略 |
| 6 | `desktop/credentials.cjs` | 新增 | 系统加密保存密钥 |
| 7 | `desktop/model-packs.cjs` | 新增 | 离线包校验、导入和状态 |
| 8 | `desktop/electron-builder.yml` | 新增 | Windows x64 NSIS、资源白名单 |
| 9 | `desktop/tests/security.test.cjs` | 新增 | IPC、URL、加密失败分支测试 |
| 10 | `desktop/tests/lifecycle.spec.cjs` | 新增 | 桌面启动退出、下载和设置测试 |
| 11 | `packaging/backend.spec` | 新增 | 核心 Python 冻结构建 |
| 12 | `packaging/formula.spec` | 新增 | 独立公式引擎冻结构建 |
| 13 | `packaging/requirements-build.txt` | 新增 | 构建工具锁定 |
| 14 | `scripts/build-desktop.ps1` | 新增 | 先核心后公式包的可重复构建 |
| 15 | `scripts/desktop_backend.py` | 新增 | 端口、启动握手、freeze_support |
| 16 | `scripts/formula_engine.py` | 扩展 | 冻结运行入口兼容 |
| 17 | `backend/shiye/config.py` | 扩展 | 安装资源与用户数据目录分离 |
| 18 | `backend/shiye/formula.py` | 扩展 | 公式独立程序与开发模式双入口 |
| 19 | `backend/shiye/main.py` | 扩展 | 桌面鉴权、识别模式、隐私状态 |
| 20 | `backend/shiye/desktop_control.py` | 新增 | 仅主进程可用的配置控制接口 |
| 21 | `backend/shiye/cloud_ocr.py` | 新增 | 图片协议适配、解析、取消和错误处理 |
| 22 | `backend/shiye/models.py` | 扩展 | 本地/API 引擎及提供方元数据，旧数据默认本地 |
| 23 | `backend/shiye/worker.py` | 扩展 | 引擎路由、发送授权检查 |
| 24 | `backend/shiye/store.py` | 扩展 | API 队列重启后暂停，不自动重新发送 |
| 25 | `backend/requirements-lock.txt` | 扩展 | 固定网络请求依赖 |
| 26 | `backend/tests/test_desktop_security.py` | 新增 | 控制面、会话和文档归属 |
| 27 | `backend/tests/test_cloud_ocr.py` | 新增 | 模拟服务、错误和数据归一化 |
| 28 | `web/src/App.tsx` | 扩展 | 设置入口、引擎选择、发送确认 |
| 29 | `web/src/components/RecognitionSettings.tsx` | 新增 | API 配置、模型包状态、首次引导 |
| 30 | `web/src/desktop.ts` | 新增 | 桌面桥类型与浏览器降级 |
| 31 | `web/src/types.ts` | 扩展 | 与后端识别契约保持一致 |
| 32 | `web/src/styles.css` | 扩展 | 设置与引导样式 |
| 33 | `web/e2e/recognition-settings.spec.ts` | 新增 | 未配置、本地、云端同意流程 |
| 34 | `.gitignore` | 扩展 | 构建、包、用户凭证和测试输出排除 |
| 35 | `README.md` | 扩展 | 安装版与源码版分别说明 |
| 36 | `docs/desktop-hybrid-design.md` | 新增 | 本设计 |
| 37 | `docs/desktop-guide.md` | 新增 | 安装、密钥、模型和排错 |
| 38 | `docs/desktop-acceptance.md` | 新增 | 实际测试证据与未验证项 |
| 39 | `.ai-governance/capability-map.md` | 实施后更新 | 只记录真正完成和验证的能力 |

## 三、现状调查与证据

| 调查项 | 结论 | 依据 |
| --- | --- | --- |
| 页面 | 复用现有 React 工作台，非重新设计第二套编辑器 | web/src/App.tsx:133；web/src/components/FormulaCard.tsx、VisualFormulaEditor.tsx；能力地图“2026-09-16 公式交互增量” |
| HTTP | 前端以相对 /api 地址访问本机服务，可继续同源加载 | web/src/api.ts:1；backend/shiye/main.py:78 |
| 会话与权限 | 已有 cookie 会话、跨站写入检查、文档归属和版本冲突检测 | backend/shiye/main.py:101、123、130、136、146 |
| 数据库 | SQLite 三表及 JSON 文档；已有恢复和 CAS | backend/shiye/store.py:20、28、89、102 |
| OCR/导出 | 现有子进程识别与导出器可原样复用 | backend/shiye/recognition.py:252；backend/shiye/exports.py:185 |
| 公式 | 独立 Python 子进程；目前依赖开发目录脚本和本机绝对路径 | backend/shiye/formula.py:97、141；backend/shiye/config.py:19 |
| 启动 | 首次仍需 Python/uv、npm 构建，终端保持运行 | scripts/start.ps1 全文 |
| 桌面/BYOK | 未发现现成桌面壳或密钥配置实现 | 对 backend、web/src、scripts、docs、.ai-governance、README 搜索 electron/tauri/byok/api.key/base.url/provider/safeStorage，仅命中 PowerShell 的 PSProvider；第二组 desktop/桌面版/密钥/云端识别/API设置只出现截图名及“无需 API 密钥”说明 |
| 工具链 | 当前 PATH 有 Node/npm/uv；未查到 cargo/rustc；系统 python 指向 LibreOffice，不能用于构建 | Get-Command node,npm,python,uv,cargo,rustc 输出；实现必须显式选项目 Python 3.12 |
| 既有文档 | 保留公式人工核对与导出质量边界 | .ai-governance/capability-map.md；docs/formula-guide.md；docs/acceptance.md |

读取过能力地图。此前记忆仅用于提醒保留公式人工校对；旧样张测试不当作本轮测试，也不当作准确率证明。

## 四、能力地图核对

| 能力类型 | 已有入口 | 处理 | 新增理由或边界 |
| --- | --- | --- | --- |
| 前端组件/页面 | App、FormulaCard、VisualFormulaEditor | 复用并扩展设置入口 | 不改公式编辑与导出交互；新增设置组件因为现在没有 API/模型包管理 |
| 共享状态/工具 | api.ts、types.ts、后端 models.py | 保留同源 API，扩展类型 | 新 desktop.ts 仅桥接主进程，不另造数据管理框架 |
| 后端服务 | recognition、formula、worker、exports | 扩展引擎路由 | cloud_ocr 新增，已有两个引擎均为本地，不处理远端协议 |
| 权限/异常/日志 | main.owner/owned、CSP、Conflict | 复用并扩展 | 新增桌面控制鉴权和系统密钥存储，现有 cookie 不足以保护桌面控制面 |
| 数据库/测试 | store.py、backend/tests、web/e2e | 复用；增加模拟 API、桌面安全与生命周期测试 | 无新表；用户原文档不自动迁移进测试库 |
| 文档/流程 | README、acceptance、能力地图 | 按现有格式扩展 | 增加安装版说明；G3 才把已验证能力写回地图 |
| 桌面/打包 | 当前只有 start.ps1 | 新增 Electron 壳及冻结打包 | 启动脚本依赖开发环境，无法作为最终安装包 |

## 五、设计方案

### 5.1 推荐架构与执行顺序

1. **先验证核心可打包性。** 在独立 staging 构建 PyInstaller one-dir 核心引擎，打包前端 dist、RapidOCR 资源和必要 DLL。入口处理 multiprocessing.freeze_support；不复制开发 .venv。不改动已运行的 8765 服务。
2. **桌面壳接入。** Electron 主进程启动专属后端，绑定 127.0.0.1 随机端口，等待健康握手再打开现有页面。持有进程句柄，退出只停止自身后端及其 OCR/公式子进程；禁止按通用 python.exe 名称批量杀进程。
3. **设置与引导。** 首次显示“本地识别（默认）/ API 识别（可选）”；公式包未安装时普通 OCR 仍可用，明确显示体积、空间需求、安装进度和失败原因。模型状态通过真实启动探测，不以“文件夹存在”直接判定可用。
4. **BYOK。** 首版支持图片输入的 Chat Completions 兼容协议（Bearer 密钥、完整 endpoint、模型名），不自动猜测供应商或模型，不承诺任意文本聊天接口可识图。先用模拟服务验收协议，再由用户在界面配置真实密钥。真实调用测试需另行明确授权；不读取其他软件已保存的密钥。
5. **独立公式包。** 在隔离构建环境冻结 Paddle 公式引擎；保留现有 JSON-lines 协议。扩展 FormulaClient 支持冻结 exe 或原开发脚本。打包权重和 DLL，移动目录后断网实测；失败就记录，不把开发环境测试算作独立包通过。
6. **安装与验收。** electron-builder 生成当前用户级 Windows x64 NSIS 安装包。模型包单独导入；另给包含核心安装器、同版本公式包和说明的完整离线目录。不购买签名证书、不自动上传 GitHub、不注册收费服务。

构建依赖在实施时选择支持当前 Windows/Node 的稳定版本并精确锁定；不在设计中虚构已经验证的版本。PyInstaller 冻结 Paddle 的实际可用性是首要技术试验，不保证仅靠添加 spec 就必然成功。

### 5.2 安全与数据流

- Electron renderer：sandbox=true、contextIsolation=true、nodeIntegration=false，保留 CSP；拦截非预期导航、新窗口，外部链接只允许明确的 HTTPS 页面并交给系统浏览器。IPC 校验发送 frame、来源、参数长度/结构，不暴露任意 shell/fs/fetch。
- 后端分两层令牌：主进程独享的控制令牌与本地页面访问令牌。启动通过私有标准输入传递，不放 URL、命令行或日志。主进程对自身 backend 精确 origin 的页面请求注入访问令牌；仅带页面令牌无法读写凭证控制接口。保留 cookie 归属、版本和 Host/Origin 检查。开发浏览器模式不开放桌面控制端点。
- API 密钥输入时会短暂出现在输入组件内存，保存后清空。持久保存默认关闭；用户选择后由主进程调用系统加密存储。优先使用 safeStorage 异步 API；加密不可用则仅本次会话使用，不降级明文。
- 主进程通过受保护控制面交给 Python 内存使用；后端不写 SQLite、普通 JSON、导出或日志。前端只收到“已配置/未配置”等状态，不读回密钥。Windows 系统加密不能防住同一用户权限下的恶意程序，不宣称绝对保护。
- 第一次及每次更改供应商后显示实际域名、模型、外发页数/裁剪范围、可能收费提示；“同意发送并识别”才建立绑定文档版本、提供方和页集合的内存授权。提供方变更/重启失效；本地失败不自动切云端。
- HTTPS endpoint；首版不支持私网/localhost 服务端点。拒绝 URL 内凭证、片段、不允许的协议和私网地址；DNS 解析/连接目的地址一致校验，禁止重定向和隐式代理，避免绕过。设置页显示完整目标地址。
- 网络调用在 Python 后端执行，不需要放开浏览器 CORS 或前端 CSP connect-src。超时、取消、401、429、服务不可用与响应超限分别提示；无自动付费重试。取消只能阻止后续发送/落盘，不能保证供应商撤销已开始调用或费用。
- 图片/模型回复都是不可信内容：只转录，不执行图中指令、HTML、URL、工具调用；限制大小和块数，严格校验结构。模型声称的 confidence 不作为校准置信度，默认 null；公式 verified=false。
- 自定义端点本身是用户选择的第三方，应用不承诺其保密政策或计费准确性；不上传图片到我们自建的中转服务。

### 5.3 识别结果如何接入现有校对

- 文档的 provider 元数据与版面模式（普通/学术）分开，旧 JSON 无新字段时按 local 处理。
- API 对选定页面按页发送，可单独重试未完成页；公式框选只发送裁剪图。后端从已有文档 ID/页 ID 读取授权图片，不接收任意本机路径。
- 统一结果为既有 Block：标题、段落、列表、表格、公式，保留原始模型内容与来源；云端结果仍进入现有校对和本地导出。
- API 返回的区域不视为精确定位。单公式裁剪使用用户框；整页结果没有可靠坐标时标注“整页来源”，bbox 只代表整页，不伪造紧框；前端不把它画成精确检测。无有效结构时显示可重试错误，不把一大段乱码当成功。
- 重做识别前保留旧结果，云端候选经用户确认替换；已手工修改/已确认公式不得被后台静默覆盖。沿用版本 CAS，并使旧导出失效。
- 启动恢复时未完成的 API 任务暂停，等待用户重新同意，不像本地 OCR 一样自动继续付费发送。
- 当前临时文档保留期 24 小时不在本轮悄悄改成永久库；首次引导明确提示及时导出。桌面新用户目录不自动搬迁开发环境的私人文档。

### 5.4 模型包和磁盘

资源目录只读，数据/模型缓存放用户目录；不改系统 PATH/Python。包有版本、平台、引擎版本、文件清单、空间需求和 SHA-256；校验值来自受信任发布清单，不能仅相信包内部自报值。导入拒绝路径穿越、符号链接、越界解压和解压体积超限。解压到隔离暂存目录，真实引擎探测通过后原子切换；失败保留旧版本。大包校验用于可执行运行时供应链和下载完整性，不对普通用户文档额外逐文件哈希。

离线目录必须实际包含核心 OCR、公式模型和版面模型；只提供会联网下载的脚本不能称为完整离线包。准确体积、内存和耗时待实测，不沿用开发脚本的 4 GB 建议作为成品大小。

### 5.5 不采用的方案

| 方案 | 不采用原因 |
| --- | --- |
| 仅把网页上传静态托管 | 无法运行当前 Python/Paddle 引擎，不能直接保留本地导出链路 |
| Tauri 首版 | 可行，但当前工具链未查到 Rust；本项目大模型占体积，先复用 Node 构建和 Electron 密钥/进程能力。不是宣称 Tauri 不适合 |
| 直接压缩 .venv | 当前机器绝对路径、原生 DLL、解释器和模型缓存可迁移性未证明 |
| 把所有引擎塞进单文件 exe | 启动解压与排错不利；优先 one-dir，再由安装器分发 |
| 本地失败自动云端兜底 | 未经同意外发文档及产生费用，不接受 |

**明确不做：** 手机、macOS、Linux、登录/收费平台、自建云推理、自动更新、公开部署、新 OCR 模型训练、保证百分百公式正确。后续平台另行构建测试，不把 Windows 包称为跨平台包。

## 六、接口与影响范围

| 范围 | 影响 | 具体对象 |
| --- | --- | --- |
| 页面 | 是 | 工作台设置、引擎标识、发送确认、模型包管理；不重做编辑器 |
| 后端 | 是 | start 增加可选 provider；health/session 隐私说明随模式变化；公式框选支持选定引擎 |
| 控制面 | 是 | desktop_control 中 /internal/desktop/config PUT/DELETE，严格控制令牌，普通 renderer 无权限；关闭时 404 |
| API 文档 | 是 | 新控制契约和云端候选/确认写入流程记录于 desktop-guide；候选不直接覆盖原内容 |
| 数据库 | 内容扩展，表结构否 | documents.body 兼容新字段；store.recover 对云端暂停；密钥不落库 |
| 权限 | 是 | 双令牌、IPC 来源、资源归属、发送授权与 URL 约束 |
| 配置/部署 | 是 | 桌面构建、固定依赖、冻结资源路径与独立模型包 |
| 文档 | 是 | README、desktop-guide、acceptance 和能力地图 |
| 原源码启动 | 保持 | start.ps1 与旧浏览器流程继续可用，不受桌面控制接口影响 |

## 七、风险与回滚

| 风险 | 缓解及失败条件 |
| --- | --- |
| Paddle/ONNX 原生库冻结失败 | 先核心后公式技术探针；保持分离，记录缺失 DLL/资源；若必须改运行时方案，先报告影响 |
| 只在开发机能运行 | 变更路径、清空开发 PATH 只算隔离冒烟；最终需无 Python/Node 的干净 Windows 环境。没有该环境则明确未验收 |
| 凭证泄漏/越权 | 凭证只在受保护控制面和内存；系统加密；拒绝 renderer 凭证读取；对日志和产物做目标性测试 |
| 重复付费调用 | 不自动重试，取消/恢复/确认过期测试；真实 API 验证需明确授权和测试范围 |
| 旧校对内容丢失 | 候选审阅、CAS、保留手动结果；兼容字段默认值；开发文档不自动迁移 |
| 模型包过大或损坏 | 预先显示空间、单独扩展包、可信清单校验、暂存后切换 |
| 分发许可与未签名安装警告 | 打包清点并附依赖/模型许可；公开分发前核对再分发条件。无证书时明确未签名，不指导关闭系统防护 |
| 用户误以为云端更准确 | 标注来源、保留原图和 verified=false；准确率必须符号级对照，排版正确不等于识别正确 |

回滚：修改前保存本任务涉及的现有文件副本和差异，不覆盖其他用户修改；新增 desktop/packaging 与原启动隔离。失败时停掉本任务自己的进程，回到源码版。桌面数据放独立目录，默认卸载/回滚保留文档，不主动删旧 .data 或模型。凭证可在设置中主动删除；撤销 API 配置同时取消未发送任务。没有 SQL 迁移回滚需求。

## 八、验收标准（全部待实施）

| 验收 | 命令/操作 | 期望 | 实际/状态 |
| --- | --- | --- | --- |
| 后端回归 | 项目 Python 执行 pytest backend/tests | 原用例与新增安全/API 模拟测试通过 | 未执行 |
| 前端构建 | web 下 npm.cmd run build | 类型检查和生产构建通过 | 未执行 |
| 桌面单测 | desktop 下 npm.cmd test | IPC、端点、控制令牌、密钥失败分支通过 | 未执行 |
| 浏览器/桌面流程 | web E2E 及桌面生命周期测试 | 设置、取消、公式校对、导出正常 | 未执行 |
| 开发模式兼容 | 独立测试端口启动旧源码版 | 现有上传、公式/导出不退化 | 未执行 |
| 安装 | 无 Python/Node 的干净 Windows x64 安装运行 | 双击打开，无需终端 | 未执行；需可用验收环境 |
| 本地隐私 | 阻断外网，读取合成中英文图片并导出 | 无外部识别请求，本地 OCR 可用 | 未执行 |
| 公式离线 | 导入包后移动安装位置并断网识别积分/矩阵 | 引擎正常、符号对照有记录、可视化修改可保存 | 未执行 |
| Word/PDF | 导出含公式的合成样本，检查 OMML 并打开/渲染 | 不只有代码；检查编辑性与版面，不仅 ZIP 完整 | 未执行 |
| 云端 | 模拟正确/畸形 JSON、401、429、超时、取消 | 提示清晰、结果保护、不静默重试；原文可恢复 | 未执行 |
| 外发控制 | 未同意/改域名/重启后排队/取消后 | 无新云端发送；同意只覆盖所选页和版本 | 未执行 |
| 真实 API | 用户配置后授权一页无隐私合成样本 | 实际端点可用才标记此提供方已验证 | 未执行；不自动消耗用户额度 |
| 凭证 | 用假 key 检查用户数据、导出、日志、打包资源 | 无明文；不记住时重启要求重填 | 未执行 |
| 访问控制 | 错令牌、其他会话、外站 Origin、恶意 IPC | 拒绝；页面令牌不得调用控制接口 | 未执行 |
| 模型包 | 损坏包、越界路径、低磁盘、错误平台 | 导入失败不破坏旧模型 | 未执行 |
| 进程清理 | 多开、正常退出、后端异常 | 不残留本程序子进程，不影响现有 8765 服务 | 未执行 |
| 发布目录 | build-desktop.ps1 生成核心及公式包 | 无私人文档/密钥/测试截图；记录版本大小与已知限制 | 未执行 |

没有干净 Windows、有效授权 API 或可用公式独立包时，分别标为“未验收/阻塞”，不得以源码成功替代成品成功。

## 九、实现前结论与待确认

- [x] 已完成相关代码调查和能力地图核对。
- [x] 已给出推荐方案、替代方案、影响面、风险、回滚及可执行验收。
- [x] 用户确认本设计后进入实现（“做完这个再做手机端”）。
- [x] G3 完成本机验证并回写能力地图；逐项结果见 desktop-acceptance.md，未验证项仍保留。

请确认：**首版按 Windows x64 + Electron + 本地默认 + 用户自带图片 API 实施；交付核心安装包、独立公式离线包和完整离线目录；不在此轮做网站/手机端/公开发布。**
确认后连续推进打包试验、实现、测试；只有遇到新安全边界、额外收费、必须改变方案或缺少真实验收环境时再单独说明。

## 十、官方依据（2026-09-16 查阅）

- [Electron 安全建议](https://www.electronjs.org/docs/latest/tutorial/security)：上下文隔离、沙箱、IPC/导航限制。
- [Electron safeStorage](https://www.electronjs.org/docs/latest/api/safe-storage)：系统加密、优先异步接口；Windows 无法防同用户恶意程序。
- [PyInstaller 运行与分发](https://pyinstaller.org/en/stable/operating-mode.html)：打包解释器/依赖，按系统架构构建，one-dir 用于先验证。不是 Paddle 打包已通过的证据。
- [OpenAI 图片输入说明](https://developers.openai.com/api/docs/guides/images-vision)：图片输入支持 URL/base64 等；本文选择兼容协议是项目设计决策，不是供应商兼容性保证。
