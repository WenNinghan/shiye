# 0.3.1 公开预发布收尾

本任务继续执行作者已确认的 release-compliance-design.md G2 方案。2026-09-17 作者再次明确要求“继续，直到为我上传release为止”。大型任务等级不变；不新增业务 API、模型或权限。

复用已经通过测试的无 IPP 核心与公式构建、材料收集器、模型包导入器和 Electron 打包流程。补充材料生成脚本用于合并现有清单、原始正文及固定版本源码；现有工具只生成分散清单，不能生成用户可离线阅读的入口。前端仅扩展使用指南中的许可入口，打包脚本补上版本参数。

本阶段受控范围：packaging/finalize_release_materials.py、web/src/App.tsx、web/public/licenses/、desktop/tests/lifecycle.spec.cjs、scripts/build-desktop.ps1、desktop/trusted-models.json、发布说明及第三方材料清单。延续原计划，不重新设计 OCR、PDF 或公式工作流。

验收：许可页面正文全部转义、无远程脚本；实际安装器内可访问；最终模型包与可信清单匹配且导入通过；既有桌面/冻结引擎合成样本回归；来源包不含凭证和用户文档；上传后 GitHub 资产大小和摘要匹配。本机测试不是另一台干净 Windows 测试，预发布须明确说明。

不采用：重复云端编译已经通过的 OpenCV；降低模型包验证；只上传二进制不附源码材料；把全部组件一律标成 MIT；清理 C 盘的无关内容。
