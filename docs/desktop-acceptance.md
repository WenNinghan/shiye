# Windows 混合桌面版验收记录

日期：2026-09-16。状态：**桌面内部测试版完成本机验收，源码已整理发布；安装包的正式公开分发验收未完成。** 本文为测试记录，不表示在每台 Windows 上均已验证。

用户确认：“做完这个再做手机端”。本轮只实现 Windows 桌面版；手机端待确定平台路线后进入下一阶段。

## 交付物

- `Shiye-0.3.0-Windows-x64.exe`：约 207 MiB，未签名，内部测试产物，未上传本仓库。
- `Shiye-Formula-0.3.0-Windows-x64.shiye-model`：859,620,337 字节，约 820 MiB，内部测试产物，未上传本仓库。
- 公式包解压内容：1,540,114,840 字节，约 1.43 GiB；含独立公式运行时和两套模型。
- `release/win-unpacked/识页.exe`：同版本免安装目录入口，必须保留旁边的 resources/DLL 等文件，不能只拷贝 exe。
- `docs/desktop-guide.md`：中文安装、模型包、API 和隐私说明；发布目录同步副本。

## 实际验证

| 项目 | 方式与实际结果 | 状态 |
| --- | --- | --- |
| 前端 | `web: npm run build`，类型检查与生产构建 exit 0；有既有大 chunk 提示 | 通过 |
| 后端 | `backend: ../.venv/Scripts/python.exe -m pytest -q`，44 passed，2 个上游弃用提示 | 通过 |
| 桌面安全单测 | `desktop: npm test`，4 passed；IPC 主 frame、URL、包路径、加密失败分支 | 通过 |
| 独立核心程序 | `scripts/verify_desktop_engine.py`；PATH 仅 System32，无 PYTHONPATH/PYTHONHOME；通知样例 14 块，生成 37,531 字节 DOCX；无令牌请求 403 | 通过（同机隔离） |
| 公式冻结引擎 | PyInstaller 冻结构建成功；包含 Paddle extras 元数据；`--warm` 实际加载两模型 | 通过 |
| 离线包导入 | `model-packs.importModelPack` 导入全新 G 盘测试目录；可信哈希校验、解压、实际加载成功 | 通过 |
| 自选模型目录 | 配置位于 model-location-test，模型位于独立 selected-model-storage；完整导入与引擎加载输出 CUSTOM_MODEL_STORAGE_AND_ENGINE_PASS | 通过 |
| 离线约束 | 冻结公式程序嵌入 socket.connect/getaddrinfo 阻断和 HF_HUB_OFFLINE；读取导入目录模型，不使用开发缓存 | 通过该代码路径；未断开整台机器网络 |
| 学术公式链路 | 导入包后，以独立核心程序处理 formula-page.png：12 块、3 个公式、DOCX 37,779 字节 | 通过流程；识别非全对 |
| Word 公式结构 | 对上述 DOCX 解包 XML：3 个原生 OMML，2 个矩阵 | 通过结构；本轮未重新用 Word/LibreOffice 渲染版面 |
| 安装后的桌面应用 | 对 installer-smoke-2/识页.exe 执行 Playwright：2 passed，17.7 秒 | 通过 |
| 最终重建产物 | 增加模型目录选择后重新生成安装器（216,675,410 字节）；对 release/win-unpacked/识页.exe 执行相同测试：2 passed，15.4 秒，证据 temp/shiye-desktop-U1FW24 | 通过；最终小改动后未重复安装/卸载 |
| 桌面具体行为 | 本地 OCR；API 配置不发送；取消外发；实际系统加密/解密/删除；模拟 API 候选显示 KaTeX、人工采用；正常退出与强杀真正主进程后的后端关闭 | 通过 |
| API 数据保护 | 后端模拟测试验证未同意拒绝、授权单次使用、改配置失效、队列重启暂停、候选不覆盖原结果、人工采用才替换 | 通过模拟测试 |
| 安装器 | 首次默认 TEMP 安装退出 2，未形成完整安装；将 TEMP/TMP 指向 G 盘后全新目标安装退出 0，独立应用存在并通过上述 2 项测试 | 有条件通过；低空间情况见下 |
| 签名 | Get-AuthenticodeSignature 返回 NotSigned | 已明确；不是签名正式版 |
| 卸载 | 仅对 installer-smoke-2 的测试安装执行，退出 0，应用 exe 不再存在；用户测试数据与分发安装包保留 | 通过 |
| 进程清理 | 测试后查询 shiye-engine.exe/shiye-formula.exe 无残留 | 通过 |
| 真实第三方 API | 没有用户授权的服务账户，没有进行付费请求 | 未验收 |
| 干净 Windows | 未提供另一台没有开发工具的机器/虚拟机 | 未验收；PATH 隔离不等于干净机测试 |
| 再分发许可 | 未替项目指定新许可证，未完成完整依赖/模型再分发审核 | 公开发布前必须完成 |
| 手机/网站 | 本轮没有实现或发布 | 后续阶段 |

完整桌面测试日志与临时产物由维护者本地保留，不随源码上传。公开演示图见 [工作台截图](../verification/screenshots/02-workspace-desktop.png) 和 [可视化公式编辑截图](../verification/screenshots/12-visual-formula-editor.png)；这些演示图不是 API 真实提供方测试证据。

## 内容准确性

三处公式中，逆矩阵右下角本应为 a，输出仍为 d。当前改造解决分发和使用方式，没有提升模型准确率。公式必须维持 verified=false，用户对照原图后确认；不得将“3 处检出”写成“100% 准确”。

## 已定位并处理的问题

- Paddle extras 依赖元数据未打包导致加载失败：补齐元数据，重新构建及实际加载验证。
- 构建工具的路径宏解析漏复制引擎：改为 JavaScript 构建配置解析真实绝对路径，缺失引擎时构建失败，并验证成品内含引擎。
- 保持 stdin 打开并在后台读取的寿命监测导致冻结 OCR 子进程等待：恢复握手后关闭 stdin，改用 Windows 进程句柄等待父进程退出。之后独立 OCR、公式及应用测试通过。
- 初次异常退出测试杀到启动器而非真正 Electron 主进程：改为从 Electron 取得实际 PID 后强杀，验证后端退出。
- UI 测试全局 status 定位与短暂提示冲突：限定在设置对话框内，最终安装版 2/2 通过。

## 磁盘与环境边界

安装期间检查发现 C 盘剩余约 130 MB。首次默认 TEMP 安装失败原因没有独立定位，不据此直接断言根因；G 盘 TEMP 重试成功。建议系统临时目录至少留 2 GB 余量，低空间时可先使用 G 盘的免安装目录。没有清理其他软件或用户资料。

本任务新增桌面开发依赖与 Electron 下载缓存迁到 G 盘，源码的 desktop/node_modules 以目录联接继续访问。本机开发工作目录依赖 G 盘；分发安装包/免安装目录不依赖它。

## 实施相对 G2 的调整

- 使用 Python 标准库实现 HTTPS、DNS 固定与响应限额，未增加原计划的第三方 HTTP 依赖。
- electron-builder.yml 改为 electron-builder.config.cjs，解决已复现的跨盘路径宏问题。
- 新增 packaging/build_model_pack.py、scripts/verify_desktop_engine.py、desktop/trusted-models.json 和桌面 Playwright 配置，用于实际产物构建及验证。
- 前端场景集中在真实 Electron 测试中，没有再造一套重复的浏览器模拟服务器。
- 由于本机系统盘空间不足，模型导入增加原生目录选择，可将大模型放到 D/G 盘；小配置仍在当前用户目录，失败只回收本次新建模型暂存目录。
- 保留旧源码启动、原导出器、公式编辑器与 SQLite 表结构，不把试验结果写成新模型能力。

## 回滚与下一步

维护者本地保留了改造前备份；历史备份不随源码分发。桌面新增内容与旧源码启动隔离。安装包正式公开分发前补真实提供方测试、干净机验证及许可证审核。手机端属于下一阶段，尚未实现独立 APP。
