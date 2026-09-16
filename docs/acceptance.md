# 识页 v0.2 验收记录

验收日期：2026-09-08；英文空格回归：2026-09-09。环境：Windows x64、Python 3.12.14、Node 24.13.0、Chromium 153（Playwright）、PaddleOCR 3.7.0、PaddlePaddle 3.3.1、Microsoft Word 16。

结论：**本机核心流程与学术公式增强均可运行；30 项后端测试、生产构建和 4 条浏览器端流程通过。** 公式样张验证了自动定位、框选识别、KaTeX 校对、Markdown 数学块及 Word 原生公式，但不代表真实论文总体准确率或全部复杂公式均已验收。

## 实际执行结果

| 验收项 | 方法与证据 | 实际结果 |
|---|---|---|
| 独立启动 | `scripts/start.ps1 -NoBrowser -SkipSetup`，实际监听 `127.0.0.1:8765`，读取健康接口 | 通过；接口报告 v0.2.0、RapidOCR、公式运行时与模型缓存状态 |
| TypeScript 与生产构建 | `web/` 下 `npm run build` | 通过；1745 个模块，KaTeX 字体随站点本地打包；仅有 500 kB chunk 提示，无编译错误 |
| 中文真实 OCR | `test_real_chinese_ocr` 使用合成中文通知调用真实 ONNX 模型 | 检出中文、日期和有线表格；未 mock OCR |
| 英文词间空格 | 使用真实英文成绩单回归整页 OCR，并以单元测试覆盖候选筛选 | `FACULTY OF POLITICAL SCIENCE AND INTERNATIONAL STUDIES`、`UNIVERSITY OF WARSAW`、`TRANSCRIPT OF RECORDS` 等标题恢复词间空格；候选若改变任何非空白字符或分数低于门槛则保留原识别 |
| 图片 / PDF 上传 | API 测试 + 浏览器上传图片和双页原生 PDF，选择 `1-2` 页 | 通过 |
| 原生 PDF 优先提取 | 后端与浏览器双页 PDF 流程 | 通过；显示“PDF 原生文字”，未重新 OCR |
| 文本校对与保存 | 浏览器把第一块改成“识页：已人工校对的中文标题”并保存 | 通过；Word / MD / TXT / JSON / PDF 均包含修改值 |
| 简单表格 | 实际 OCR 后校验“第 2 行第 2 列”为“项目展示” | 通过；DOCX 中是可编辑表格单元格 |
| 页序、旋转与删除 | 浏览器交换双页 PDF、旋转页面、删除文档 | 通过；变换后旧识别与旧导出失效 |
| 遮盖与旧导出失效 | API 框选遮盖后检查像素、旧下载返回 404 | 通过 |
| 会话、版本与任务恢复 | 跨会话访问、过期版本、取消 / 重试、OCR 子进程超时、崩溃恢复 | 均通过；不合法访问被拒绝，旧请求不覆盖新内容 |
| 待办与日历 | 候选草稿、日期规则、人工确认门槛、VEVENT / VTODO、UTF-8 折行 | 通过；无明确时间不虚构 23:59 |
| 实际下载 | 浏览器下载 DOCX、MD、TXT、两类 PDF、JSON、ICS | 7 个核心流程文件落盘并由 `scripts/verify_exports.py` 复查 |
| Word / PDF 视觉 | LibreOffice 渲染普通 DOCX；Microsoft Word 本体渲染公式 DOCX；PyMuPDF 渲染两类 PDF | 中文、表格、公式无裁切或乱码；可搜索 PDF 与图片 PDF 画面一致 |
| 桌面和手机 UI | 1440×1100、390×844；真实页面截图并检查横向宽度 | 通过，无横向溢出 |

## 学术公式专项验收

| 验收项 | 真实操作 | 实际结果 |
|---|---|---|
| 隔离运行时 | 核心 `.venv` 外的本地公式环境，健康接口与 `/api/formula/status` | `PP-FormulaNet_plus-M`、CPU、模型已缓存；普通 OCR 不依赖该环境 |
| 框选识别 | 对积分 PNG 的完整区域调用真实 FormulaRecognition | 返回 `\int_{0}^{\infty}e^{-x^2}dx=\frac{\sqrt{\pi}}{2}`；积分边界、指数、分式、根号和 π 均保留 |
| 整页自动定位 | 含中文正文、积分、电磁公式和矩阵的 1100×1500 合成页 | 定位 3/3 个公式，框坐标与页面匹配；缓存模型下本次约 12.9 秒 |
| 去重与 OCR 替换 | 重复扫描；让 RapidOCR 同时读取公式区域 | 相同自动公式不堆叠；被公式框覆盖的标题 / 段落乱码被移除；人工确认公式保留 |
| 模型误差可见 | 将第三个矩阵结果与生成真值比较 | 末项曾把 `a` 识别为 `d`；界面默认“未核对”，编辑后取消确认，未把模型分数宣传为正确率 |
| 浏览器完整链 | 选择学术模式 → 上传公式页 → 自动识别 → 3 个 KaTeX 预览 → 勾选确认 → 保存 → 下载 Word | 通过，实际公式工作台截图已保存；无页面脚本错误 |
| Markdown | 导出积分与矩阵 | 使用 `$$` 数学块，LaTeX 未被 HTML 转义破坏 |
| Word 原生公式 | 解压 DOCX 检查 XML；Microsoft Word 以 COM 打开并导出 PDF | 验收文档有 2 个 `OMath` 对象，实际 UI 下载有 3 个；分式、平方根、积分上下限和矩阵正常渲染且无源码回退 |
| 平方根兼容修复 | Word 首次渲染发现根号前多出空度数占位框 | 补齐 OMML `degHide` 与空 degree 后消失；单元测试与 Word 本体重渲染通过 |

机器可读证据：[公式检查结果](../verification/formula-check.json)。本次缓存模型下，框选积分约 13.8 秒、整页扫描约 12.9 秒；首次模型下载和首次进程加载更慢。这是单机合成样张记录，不是速度或准确率承诺。

## 最终测试结果

- 后端：`30 passed, 2 warnings in 8.08s`。两条警告来自 Starlette 测试接口弃用提示，不是识别失败。
- 前端构建：通过；Vite 7.3.6，1745 个模块。
- 浏览器：`4 passed (33.7s)`，包括真实公式模型流程；公式运行时未安装的机器会透明跳过该可选用例。
- 公式专项脚本：区域与整页真实推理、Markdown、DOCX XML 检查全部通过。

开发中曾有两项失败被实际修复：浏览器用普通 OCR 的完成文案等待学术模式，调整为等待真实公式块；普通 OCR 把公式行误标成标题导致重复，合并规则已覆盖并重新验收。未把失败运行写成通过。

## 视觉证据

- [桌面首页](../verification/screenshots/01-home-desktop.png)
- [普通文档校对](../verification/screenshots/02-workspace-desktop.png)
- [通知候选事项](../verification/screenshots/03-tasks-desktop.png)
- [手机首页](../verification/screenshots/04-home-mobile.png)
- [手机工作台](../verification/screenshots/05-workspace-mobile.png)
- [搜索 PDF 渲染](../verification/screenshots/06-searchable-pdf-render.png)
- [普通 Word 渲染](../verification/screenshots/07-word-render-page-1.png)
- [整页公式定位](../verification/screenshots/08-formula-detection.png)
- [Word 原生公式渲染](../verification/screenshots/09-formula-word-render.png)
- [公式校对工作台](../verification/screenshots/10-formula-workspace.png)

## 未验证 / 未实现的范围

- 未对真实论文 / 课本数据集建立人工真值，因此没有 CER、公式表达式识别率、表格 F1 或用户满意度结论。
- 公式专项只覆盖清晰印刷积分、分式、根式、电磁公式和矩阵；未验收手写、化学结构式、极端长公式、自定义宏包或复杂分段公式。
- 未实测 Safari、Firefox、Linux、macOS、Docker、屏幕阅读器、高并发或恶意 PDF。
- 复杂多栏阅读顺序、曲面展开、合并单元格和无框线复杂表格仍不保证。
- 未做图像解码进程级硬内存沙箱；当前限于本机 / 可信材料。公网部署治理仍属后续阶段。

## 交付与回滚

交付包含源码、核心与公式安装脚本、锁文件、合成样例、截图、机器可读验收记录和源码 ZIP。`.data/`、`.venv/`、公式大模型环境、`node_modules/`、测试 Cookie 和用户上传文件不进入源码包。

停止本机进程即可撤回运行服务。删除独立公式运行时只会关闭学术增强，不影响普通文档模式；新增公式字段有默认值且不需要 SQLite 表迁移。未执行 git commit、push 或公网部署。
