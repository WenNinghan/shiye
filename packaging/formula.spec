from pathlib import Path
from PyInstaller.utils.hooks import collect_all, copy_metadata
root = Path(SPECPATH).parent
datas, binaries, hiddenimports = [], [], []
for package in ("paddle", "paddleocr", "paddlex", "tokenizers", "tiktoken", "sentencepiece", "safetensors"):
    data, binary, hidden = collect_all(package)
    datas += data
    binaries += binary
    hiddenimports += hidden
for distribution in ("paddleocr", "paddlepaddle", "paddlex", "tokenizers",
    "beautifulsoup4", "einops", "ftfy", "imagesize", "Jinja2", "latex2mathml",
    "lxml", "opencv-contrib-python", "openpyxl", "premailer", "pyclipper",
    "pypdfium2", "python-bidi", "regex", "safetensors", "scikit-learn",
    "scipy", "sentencepiece", "shapely", "tiktoken"):
    datas += copy_metadata(distribution, recursive=True)
a = Analysis([str(root / "scripts" / "formula_engine.py")],
             pathex=[str(root)], binaries=binaries, datas=datas, hiddenimports=hiddenimports,
             excludes=["pytest", "tkinter", "torch", "IPython"], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="shiye-formula",
          debug=False, strip=False, upx=False, console=True)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="shiye-formula")
