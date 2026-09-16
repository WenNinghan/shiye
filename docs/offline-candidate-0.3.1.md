# 0.3.1 完整离线候选整合

2026-09-16。用户选择“完整离线”，在确认两套云端候选成功后回复“好的，继续”。本阶段沿用已确认的 `release-compliance-design.md` 和 `opencv-cloud-build.md`，不更换模型/PDF 引擎或改成 API 必选。

## G1 / G2 续行范围

原大型分发方案继续有效。本次复用既有 core/formula spec、模型包构建、桌面构建、安全测试和真实样例验证。若修改版本参数、许可材料打包或增加离线验证，属于原方案的构建/验收步骤；应用 API、数据库、认证和计费不变。H1/H9 按原方案命中，H2/H3/H4/H5/H6/H7/H8/H10 未命中；不增加运行依赖或新的云服务。

已完整核对迁移后的能力地图 `G:\Shiye\outputs\shiye-WenNinghan\.ai-governance\capability-map.md`。前端/后端功能、权限和测试数据复用；构建材料扩展；数据库不涉及。不采用替换 PDF 技术栈或覆盖原可用环境的方案。

具体步骤：

1. 下载 core run 35094639675、formula run 35081772275 的成功工件，核对 wheel SHA-256。
2. 在 G 盘复制现有两套环境，只在副本中替换同版本自编译 wheel；通过实际已加载扩展与 wheel 字节对比、构建参数和图像测试。
3. 对新环境执行后端测试，在独立目录冻结两套引擎；最终冻结的 cv2 扩展须与候选相同。
4. 复用公开合成图片检查普通 OCR、公式识别及导出；测试数据和日志放 G 盘，不触碰正在运行的 8765 服务或用户文档。
5. 补齐许可/源码材料、重生成模型包及可信清单后，执行桌面验收。材料或真实推理未通过时不发布公开 Release。

风险与回滚：新环境/新输出全部独立保存；保留旧 0.3.0 内测包、原开发环境和模型，不通过就不替换。第三方运行库还须按最终 Analysis 再检查，不能把 OpenCV 成功视为全部分发条件完成。

## 已执行验证

- 两个复制任务的 robocopy 汇总均为 FAILED=0；核心 7,294 文件、公式 28,844 文件。原环境没有被安装操作修改。
- 两个 wheel 下载哈希与云端工件记录一致；在复制环境安装后运行 `packaging/verify_opencv_no_ipp.py` 均成功，图片处理通过、IPP 未启用。
- 新核心环境 `python -m pytest tests -q`：44 passed，12.27 秒；两条已有上游弃用警告。

冻结引擎、整包断网验收和公开发行结果在实际完成后追加，不提前标为通过。

## 候选包版本隔离（实施前补充）

修改范围：`packaging/build_model_pack.py` 增加可选 `--version`（默认保留 0.3.0）；`desktop/electron-builder.config.cjs` 增加可选 `SHIYE_MODEL_MANIFEST` 路径，默认仍使用仓库清单；本记录和构建用例随之补充。H9 命中，判定中等，属于原已确认模型包重打与哈希验证方案。H1 未命中（4 个文件），其余 H2–H8、H10 均未命中；不修改包导入鉴权或校验逻辑。

复用既有模型包格式和校验器，不覆盖仓库旧可信清单；候选清单单独保存，并在候选桌面构建时明确选择。桌面包版本通过 electron-builder 已有 extraMetadata 参数设为 0.3.1，识别业务代码不变。不采用原地替换旧模型包或关闭哈希验证的做法。验收为小型虚拟运行时/模型目录打包检查、既有工具测试和最终新包真实导入。必要时移除新参数即可回到原构建行为。

## 独立引擎验收

- 两套 PyInstaller 冻结构建均完成。最终 core/formula 的 cv2.pyd 分别与已验证环境逐字节哈希一致：core `fbd8027536fbdd74809b9b75510d6859af688d4b1fd966a38d5dd2ab2369d883`；formula `4196e5ee0ff1a3560a4504452694eb0b8bbfa5392dad454b1c0267d9a9bd0ed8`。最终两个目录未发现以 ipp 或 opencv_videoio_ffmpeg 开头的文件；编译信息和扩展对应关系才是去除 IPP 的主要证据，不单靠文件名。
- `scripts/verify_desktop_engine.py` 直接启动冻结 EXE，移除 PYTHONPATH/PYTHONHOME、PATH 仅保留 System32：普通页 14 个内容块、Word 37,531 字节，访问令牌校验通过。
- 学术模式连接新的冻结公式 EXE，用已有本地模型识别公开合成页：3 个公式、12 个内容块，Word 37,779 字节。实际 Word XML 含 3 个 OMML 公式、3 个分式、1 个根式、2 个矩阵。
- 积分式识别正确；逆矩阵右下角仍把 a 识别为 d，不能把检出 3 个公式当作全部符号正确。与旧版本相同，必须保留人工校对。
- 公式 EXE 自带禁止 Python socket.connect/getaddrinfo 的离线审计钩子，使用已缓存模型完成推理；本次不是操作系统级全机断网，也不是另一台干净电脑测试。
- 新包版本单测连同既有材料测试 14/14 通过；桌面安全单测 4/4 通过。

## 原生声明补充

按 [Paddle v3.3.1 构建配置](https://github.com/PaddlePaddle/Paddle/blob/v3.3.1/cmake/external/mklml.cmake) 取得其固定 MKLML Windows 归档，MD5 与上游记录 `ff8c5237570f03eea37377ccfc95a08a` 一致。其中 mklml.dll、libiomp5md.dll 的 SHA-256 与实际 Paddle wheel 完全相同，原始 Intel April 2018 license.txt 和 third-party-programs.txt 已保存；不将其套用为 Paddle Apache 许可。此项只完成来源与声明对应，不自动判断整个组合的法律兼容性或完整源码覆盖。

重新从本次 Analysis 收集得到 core 35、formula 103 个组件，未映射 site-packages 项为 0；仍保留缺文本/需复核状态，随本机候选附入已取得的许可和 sdist 补充材料。最终公开 Release 仍需完成原生依赖及对应源码覆盖审查。

## 模型包与桌面候选验收（G3）

- 新模型包：836,790,318 字节，解包大小 1,484,173,155 字节，SHA-256 `ebeea48b100ce10004ae418b7f4f572f046f7a0651a0001ee9b909bedcd5bc18`。可信 ID 为 formula-cpu-0.3.1，清单独立存放，未覆盖仓库的旧清单。
- 使用真正的 `desktop/model-packs.cjs#importModelPack` 导入到全新 G 盘存储目录，哈希校验、路径检查、解压、冻结模型预热均成功；再用导入后的 executable/cache 运行学术模式，3 个公式与 Word 导出均成功，矩阵已知误识别仍存在。
- 初次桌面打包时目录联接让依赖收集器遗漏 buffer-crc32/pend，产物移至 `first-desktop-build`，未交付。改用 G 盘实体依赖副本后重新打包，ASAR 已核实同时包含 yauzl、buffer-crc32 和 pend；不再存在该漏包警告。
- 最终 NSIS 安装候选：198,778,804 字节，SHA-256 `d49662e4fb025e54dea1810027f1ba0130a90cd17186d04009b0115c3c0a5840`。Authenticode 为 NotSigned；构建日志出现 signtool 步骤不等于签名成功。
- 新包内核心 EXE 与已测试核心 EXE SHA-256 相同，均为 `21820d329faf6024e4d29e101dc7f0a747b7e4544765e9746cd5b2e888ca1c16`；新可信模型清单已进入 resources。
- 对最终 win-unpacked/识页.exe 执行既有 Playwright 桌面测试：2/2 通过，16.2 秒。覆盖实际 OCR、设置/隐私交互、正常退出和异常退出后的后台清理；截图已打开检查，工作台内容正常呈现。
- 本轮未在另一台干净机器安装 NSIS，也未执行全机断网；安装器生成、打包 APP 实测与 OS 级断网验收分别记录，不互相替代。界面页脚仍是原有前端 v0.2 标识，桌面包元数据为 0.3.1（本次为底层依赖/打包候选，不是前端功能升级）。

本机产物位于 `G:\CodexBuilds\shiye-release-0.3.1\candidate\release`，保留旧 0.3.0 内测版。源码改动可以公开保存，安装器/模型包不上传公开 Release，直到分发条件完成。尚待：原生依赖和对应源码覆盖、缺失许可正文的最终补齐、可离线浏览的完整许可入口以及干净 Windows 安装/断网验收。
