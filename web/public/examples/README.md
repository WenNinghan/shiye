# 合成演示样例

本目录公开 PNG 和公式真值，不含真实个人文档。两份 PDF 在本机生成，避免随源码再分发可能嵌入的系统字体。

正常运行根目录 scripts/start.ps1 会先生成样例。已准备 Python 环境时也可执行：

```powershell
./.venv/Scripts/python.exe scripts/make_samples.py
```

公式样例的生成实现位于 web/scripts/make-formula-sample.mjs；使用前先安装 web 的锁定依赖。样例通过只表示这组输入的流程可运行，不代表真实论文、教材或手写材料的总体准确率。
