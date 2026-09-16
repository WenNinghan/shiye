# 0.3.1 最终预发布包验收 · 2026-09-17

G3：沿用作者批准的分发设计；源码 MIT 不变、核心组合依适用 AGPL 条件发布。最后环节是向 Release 上传并核对资产，不把本机产物等同于在线发布完成。

## 实际构建与测试

| 项目 | 验证方式 | 实际结果 |
| --- | --- | --- |
| 后端回归 | 独立 core 环境，backend 工作目录 `python -m pytest -q` | 44 passed，11.96 s；2 条上游弃用警告 |
| 材料/构建安全 | `python -m unittest discover -s packaging/tests -v` | 15 passed；新增许可页转义、无 script/iframe/object 和本地链接存在检查 |
| 桌面安全 | `node --test tests/security.test.cjs` | 4 passed；没有关闭 IPC、模型哈希或凭证隔离 |
| 最终 APP | 对 final/release/win-unpacked/识页.exe 运行 Playwright | 2 passed，16.7 s；含本机 OCR、许可入口、密钥加密、模拟 API 同意/候选、正常/强制退出释放后台 |
| 许可入口 | 真正的 Electron 使用指南展开，隔离 iframe srcDoc 显示 | 标题可见、AGPL 正文可读；不修改后端 frame-ancestors 'none' 安全策略 |
| 许可正文覆盖 | 对 core 35 + formula 103 清单逐条检查原始或补充正文实际存在 | 138 条记录均有文件映射；这不是把全部许可统一判为 MIT |
| 新公式包 | 原有 importModelPack 实现，全新 G 盘测试/模型目录 | 哈希、空间、解压路径和实际模型启动通过，FINAL_MODEL_IMPORT_OK |
| 实际公式推理 | 最终冻结 EXE + 上一步导入的模型，合成 formula-page.png，academic 模式 | 12 块、3 个公式；Word 37,779 字节；开发 PATH 去除，鉴权启用 |
| 已知识别误差 | 输出逐式比对 ground truth | 积分/高斯公式可读，逆矩阵右下角 a 错成 d；明确不宣称全对 |
| 签名 | Get-AuthenticodeSignature 检查最终安装器 | NotSigned；构建日志的 signtool 字样不能当签名成功 |
| 原开发服务 | GET 127.0.0.1:8765/api/health | HTTP 200，未替换原服务或删除原 0.3.0 包 |

## 最终主要资产

| 资产 | 字节 | SHA-256 |
| --- | ---: | --- |
| Shiye-0.3.1-Windows-x64.exe | 202447083 | 1280f6051bb7e4e5e55ad626e09dc51ef01619da9d85a8744f4acc6582df3499 |
| Shiye-Formula-0.3.1-Windows-x64.shiye-model | 846533639 | 961c7af28b4b3070a4844245e8f8fac6aa06075f681112e6159ebf95de24bb91 |

新可信清单已写入源码和最终安装器；不再沿用旧候选 ebeea48b… 或 0.3.0 清单。原候选/原环境保留，所有新增下载和构建存 G 盘。

源码材料：113 份 PyPI sdist，另外 6 个固定上游源码快照、CPython 官方源码、3 份带 .py 源码的纯 Python wheel；MuPDF 完整源码、GEOS 与原始 MKLML 重建输入；两套无 IPP OpenCV 源码/wheel/补丁/CMake/验证资料。实际来源、大小和 SHA-256 保存在各组 sources.json 与 Release SHA256SUMS.txt。

## 没有声称完成的测试

- 未在另一台干净 Windows 上完成安装/运行，未进行操作系统全局断网测试。
- 未购买或配置代码签名证书，不要求用户关闭 Windows 安全防护。
- API 同意/加密/候选 UI 使用模拟服务验证，不冒称付费真实供应商调用成功。
- 未完成手机端、网站公网部署或总体 OCR 准确率基准。

本版定义为 Pre-release，普通用户入口明确区分安装器/模型包与开发者源码材料。上传后以 Release 资产列表与服务器 digest 逐项核对，再更新社区项目入口。
