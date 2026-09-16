# 发布状态 · 2026-09-16

维护者：[WenNinghan](https://github.com/WenNinghan)。

| 入口 / 产物 | 状态 |
| --- | --- |
| [个人源码仓库](https://github.com/WenNinghan/shiye) | 主维护入口，包含前后端、桌面源码、构建脚本和说明 |
| [AIAADC 项目目录](https://github.com/AIAADC/student-projects/tree/main/projects/shiye-WenNinghan) | 轻量项目展示、截图、运行与主仓库链接；不另设作者文件夹 |
| 在线网站 | 未部署；127.0.0.1 不是公网演示地址 |
| Windows x64 安装包 | 已本机内测，未签名，暂未公开上传 |
| 公式离线包 | 已实测导入及指定存储目录，暂未公开上传权重和运行时 |
| 手机端 | 规划中，未发布 APK / iOS 安装包 |

## 本次公开源码包含什么

- backend：OCR、公式调度、PDF/Word 等导出、文档状态及桌面 API 控制。
- web：校对工作台、公式数学排版/可视化编辑与桌面设置界面。
- desktop / packaging：桌面安全边界、密钥可选系统加密、模型包校验、构建配置。
- tests / e2e、合成 PNG 与生成脚本、使用指南、测试记录和截图。

没有把本地用户文档、会话数据库、API 密钥、开发环境、临时日志、备份目录或安装包纳入 Git。

## 测试记录如何理解

2026-09-16 已记录：44 项后端测试、4 项桌面安全单测、2 项最终打包应用流程测试通过。可选公式链路检出合成页 3 个公式，但存在矩阵字符错误；不能据此推导总体正确率。见 [完整验收](desktop-acceptance.md)。本次 GitHub 整理不改变功能代码，不重复宣称新一轮完整产品验收。

真实服务商 API、独立干净 Windows 机器和完整依赖/权重再分发许可仍待核对。详见 [第三方来源](../THIRD_PARTY_NOTICES.md)。

## 下一步

先完善桌面公开分发条件，再确定手机端路线。上传 GitHub 不是自动上线网站，也不是把 Windows 可执行文件转换成手机 APP。
