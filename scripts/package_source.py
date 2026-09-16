"""Build a source-only handoff archive from explicit, project-owned allowlists."""
import argparse
import zipfile
from pathlib import Path


def package(target: Path):
    root = Path(__file__).resolve().parents[1]
    files = [root/name for name in [
        "README.md", "Dockerfile", ".gitignore", ".dockerignore", "启动识页.cmd",
        "backend/pyproject.toml", "backend/requirements-lock.txt", "backend/requirements-formula.txt",
        "web/package.json", "web/package-lock.json", "web/index.html", "web/tsconfig.json",
        "web/vite.config.ts", "web/playwright.config.ts", "verification/export-check.json",
        "verification/formula-check.json"
    ]]
    for directory in [
        "backend/shiye", "backend/tests", "web/src", "web/e2e", "web/public/examples",
        "scripts", "docs", ".ai-governance", "verification/screenshots"
    ]:
        files.extend(path for path in (root/directory).rglob("*") if path.is_file() and "__pycache__" not in path.parts and ".pytest_cache" not in path.parts)
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(set(files)):
            if file.is_symlink() or not file.resolve().is_relative_to(root):
                raise ValueError(f"Refusing unexpected path: {file.name}")
            archive.write(file, root.name+"/"+file.relative_to(root).as_posix())
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        forbidden = {".data", ".venv", "node_modules", ".env", "test-results", "generated"}
        assert not any(forbidden.intersection(Path(name).parts) for name in archive.namelist())
        assert f"{root.name}/README.md" in archive.namelist()
        print(f"Verified {len(archive.namelist())} source/sample/evidence files; no runtime data or environments included.")
    print(f"Source archive: {target} ({target.stat().st_size/1024/1024:.2f} MB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[2]/"识页-Shiye-v0.2-源码.zip")
    package(parser.parse_args().output)
