# 识页实现设计与授权记录

## 授权

来源：已交付《识页-OCR文档工具完整规划-v2.md》。用户：“可以，按照规划详细实现”。确认进入实现；本次落地为可运行本机应用及可部署源码，暂不购买服务或发布到公网。

## G1 复杂度

| 条件 | 结果 | 依据 |
|---|---|---|
| H1 ≥5 文件 | 命中 | 下列 27 个拟建源文件 |
| H2 数据库 | 命中 | 新增 sessions、jobs、documents、exports 与 tasks 表 |
| H3 接口 | 命中 | 上传、识别、文档、导出、删除接口 |
| H4 权限 | 命中 | 会话 cookie 与资源归属检查 |
| H5 计费 | 未命中 | 本机引擎，无付费调用 |
| H6 修改公共模块 | 未命中 | 新项目，不改原资源库公共代码 |
| H7 新依赖 | 命中 | React、FastAPI、OCR、PDF 等 |
| H8 跨端 | 命中 | 前后端共享数据结构 |
| H9 配置 | 命中 | 包管理、运行脚本、Dockerfile |
| H10 业务口径不明 | 未命中于本轮 | 用户确认方案；默认本机、忠实识别、24小时保留；公开部署与付费服务另行落实 |

判定：大。已有用户确认，不重复索要批准。

具体拟建清单：backend/pyproject.toml；backend/shiye/__init__.py；config.py；models.py；store.py；recognition.py；exports.py；tasks.py；main.py；backend/tests/test_api.py；test_exports.py；test_recognition.py；web/package.json；web/tsconfig.json；web/vite.config.ts；web/index.html；web/src/main.tsx；App.tsx；types.ts；api.ts；styles.css；web/e2e/app.spec.ts；scripts/start.ps1；scripts/start.sh；scripts/make_samples.py；Dockerfile；README.md。还会添加必要的锁文件和配置。

## G2 现状与方案

Get-ChildItem outputs 仅见两份设计文档；工作区原项目源码在 work/student-projects-*，本轮不改这些目录。依赖探测发现 Python 3.12 与 Node 24，尚未装 FastAPI/OCR。可复用能力已记录在 capability-map.md。

采用 React + TypeScript 工作台、Python FastAPI 单服务、SQLite 持久队列、单 worker；构建后 FastAPI 同源提供前端。用 Vite 构建 React 可避免为本机 Python 工作流再启一个 Node 服务。默认 RapidOCR 的 Paddle 系中文 ONNX 模型作 CPU 路线；结构识别包含行框、简单表格与原图回退。可选 Paddle 适配不伪装为已验证效果。

导出统一 DocumentIR：DOCX、MD+assets ZIP、TXT、图像 PDF、可搜索 PDF、JSON备份；文字层由当前校对版本生成。来源图像保持不变。原生 PDF 先取文字，扫描区域 OCR。

不采用纯前端伪 OCR 或整页图片冒充 Word；不采用每次导出重新调模型；当前不通过 Cloudflare Sites 运行 Python/ONNX 任务。

## 风险、回滚、验证

全部数据放专用 SHIYE_DATA_DIR；支持手动清理和到期清理。会话隔离、限制页数/像素/请求尺寸，源文件不执行脚本；本机仅监听 127.0.0.1。SQLite 原子保存与版本冲突保护。测试将验证跨会话访问、失效版本、中文导出内容、真实 OCR、取消/重试、删除。停止服务即可撤回新应用；原工作区和资源库不受影响。

使用构造样例做真实识别；测试成绩与公开试用分开记录。v0.2 已加入可选印刷公式链路，复杂 / 手写公式和杂志排版仍用明确回退，不声称全部文档无损转换。
