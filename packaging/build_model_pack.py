"""Build a versioned offline payload and its separately shipped trusted manifest."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument("--runtime", required=True)
parser.add_argument("--cache", required=True)
parser.add_argument("--output", required=True)
parser.add_argument("--manifest", required=True)
parser.add_argument("--version", default="0.3.0", help="Version used in the trusted pack ID")
args = parser.parse_args()
runtime, cache = Path(args.runtime).resolve(), Path(args.cache).resolve()
output = Path(args.output).resolve()
assert (runtime / "shiye-formula.exe").is_file()
models = ["PP-FormulaNet_plus-M", "PP-DocLayout_plus-L"]
for model in models:
    assert (cache / "official_models" / model / "inference.json").is_file(), model
output.parent.mkdir(parents=True, exist_ok=True)
entries = []
for file in runtime.rglob("*"):
    if file.is_file():
        entries.append((file, "runtime/" + file.relative_to(runtime).as_posix()))
for model in models:
    folder = cache / "official_models" / model
    for file in folder.rglob("*"):
        if file.is_file():
            entries.append((file, "cache/" + file.relative_to(cache).as_posix()))
total = sum(file.stat().st_size for file, _ in entries)
with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=3, allowZip64=True) as archive:
    for file, name in entries:
        archive.write(file, name)
with output.open("rb") as stream:
    digest = hashlib.file_digest(stream, "sha256").hexdigest()
manifest = {"version":1, "packs":[{"id":"formula-cpu-" + args.version,"platform":"win32","arch":"x64",
    "file":output.name,"bytes":output.stat().st_size,"unpackedBytes":total,"sha256":digest}]}
Path(args.manifest).write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print(json.dumps(manifest))
