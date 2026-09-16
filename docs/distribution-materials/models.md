# 公式模型来源

2026-09-16 核对官方 Hugging Face 模型卡、固定 revision 和 LFS SHA-256；本轮再次计算本地权重哈希，值一致。权重文件未修改。

| 模型 | 官方固定版本 | inference.pdiparams SHA-256 |
| --- | --- | --- |
| PP-FormulaNet_plus-M | [PaddlePaddle / 712e6e2e4c313b1ea163be5c350127b82662c58d](https://huggingface.co/PaddlePaddle/PP-FormulaNet_plus-M/tree/712e6e2e4c313b1ea163be5c350127b82662c58d) | `f16ef9b5c8227da70d3ec969a5195f4d62c1154427b883f4d6cff07633654041` |
| PP-DocLayout_plus-L | [PaddlePaddle / aa52b8528c84f9b1a34ac3a88fe0e576edb9d11d](https://huggingface.co/PaddlePaddle/PP-DocLayout_plus-L/tree/aa52b8528c84f9b1a34ac3a88fe0e576edb9d11d) | `24ca3e2e442164505e250deef59f7ee9a54ea12dd32875c9cd6155d959dc97da` |

上述官方模型页标注 **Apache-2.0**。发布者为 PaddlePaddle，识页未对权重训练或修改；不将其改授为 MIT，也不暗示上游为本项目背书。

这份记录只证明两个权重文件的身份及官方许可标识。整个 `.shiye-model` 还包含 Paddle 及大量原生/传递依赖；它们仍需单独核对，不能由此宣布整个离线包完成分发许可检查。

模型包若补入许可材料，其 ZIP 的 SHA-256 与大小会改变，须重新生成并测试 `desktop/trusted-models.json`，不得绕过现有验证。本轮尚未重打模型包。
