from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files

root = Path(SPECPATH).parent
datas = [(str(root / "web" / "dist"), "web/dist")]
binaries = []
hiddenimports = ["uvicorn.logging", "uvicorn.loops.auto", "uvicorn.protocols.http.h11_impl",
                 "uvicorn.protocols.websockets.auto", "uvicorn.lifespan.on"]
for package in ("rapidocr_onnxruntime", "onnxruntime", "latex2mathml", "mathml2omml"):
    data, binary, hidden = collect_all(package)
    datas += data
    binaries += binary
    hiddenimports += hidden
datas += collect_data_files("docx")
a = Analysis([str(root / "scripts" / "desktop_backend.py")],
             pathex=[str(root / "backend")], binaries=binaries, datas=datas,
             hiddenimports=hiddenimports, excludes=["pytest", "reportlab", "tkinter"],
             noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="shiye-engine",
          debug=False, strip=False, upx=False, console=True)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="shiye-engine")
