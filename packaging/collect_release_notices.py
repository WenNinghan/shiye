"""Inventory frozen Python components using PyInstaller evidence, not pip freeze.

Run with the interpreter that built the selected runtime. Output is evidence,
not an automatic legal approval. Missing license texts remain explicit.
"""
import argparse
import ast
import hashlib
import importlib.metadata as metadata
import json
import re
import shutil
from pathlib import Path


def file_sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def paths_in(value):
    if isinstance(value, str) and Path(value).is_absolute():
        yield str(Path(value).resolve()).casefold()
    elif isinstance(value, (tuple, list)):
        for child in value:
            yield from paths_in(child)


def inventory(toc, output):
    analysis = ast.literal_eval(toc.read_text(encoding='utf-8'))
    # PyInstaller 6 Analysis cache: scripts, pure modules, binaries and final
    # data TOCs. Earlier fields are inputs/hooks; the final field is graph
    # bookkeeping, which can mention excluded modules such as pytest.
    if len(analysis) != 20:
        raise ValueError('Unsupported Analysis schema; review collector before release')
    sources = set(paths_in([analysis[i] for i in (13, 14, 15, 18)]))
    output.mkdir(parents=True, exist_ok=True)
    records = []
    covered = set()
    for dist in metadata.distributions():
        files = list(dist.files or [])
        owned = {str(Path(dist.locate_file(f)).resolve()).casefold() for f in files}
        matched = owned & sources
        if not matched:
            continue
        covered.update(matched)
        name, version = dist.metadata['Name'], dist.version
        folder = re.sub(r'[^a-zA-Z0-9_.-]', '_', name + '-' + version)
        target = output / folder
        target.mkdir(exist_ok=True)
        notices = []
        for item in files:
            # Wheels can store e.g. licenses/BUILD_LICENSES/freetype.txt.
            # Checking only the basename silently drops these native notices.
            if not re.search(r'(license|licence|copying|notice|copyright|authors|eula|third.party)', item.as_posix(), re.I):
                continue
            source = Path(dist.locate_file(item)).resolve()
            if not source.is_file() or source.suffix.lower() in {'.py', '.pyc', '.so', '.pyd', '.dll'}:
                continue
            safe = '/'.join(part for part in item.parts if part not in {'.', '..'})
            destination = target / safe
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            notices.append({'file': destination.relative_to(output).as_posix(), 'sha256': file_sha(destination)})
        records.append({'name': name, 'version': version, 'matched_files': len(matched),
                        'license': dist.metadata.get('License-Expression') or dist.metadata.get('License', ''),
                        'classifiers': [c for c in dist.metadata.get_all('Classifier', []) if c.startswith('License')],
                        'project_urls': dist.metadata.get_all('Project-URL', []),
                        'pypi': f'https://pypi.org/project/{name}/{version}/', 'notices': notices,
                        'review': 'text-present-review-required' if notices else 'MISSING-TEXT'})
    # Source paths are local evidence only; do not publish developer home paths.
    unmatched = sorted(p for p in sources - covered if 'site-packages' in p)
    result = {'scope': 'Distributions with files present in this PyInstaller Analysis',
              'components': sorted(records, key=lambda r: r['name'].lower()),
              'unmapped_site_package_files': [p.split('site-packages', 1)[1].lstrip('/\\') for p in unmatched]}
    (output / 'inventory.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'components': len(records), 'missing_text': [r['name'] for r in records if not r['notices']],
                      'unmapped_site_package_files': len(unmatched)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--analysis', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    inventory(args.analysis, args.output)
