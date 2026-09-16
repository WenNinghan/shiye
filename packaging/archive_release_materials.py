"""Archive existing, explicitly selected release materials; never scan user data."""
import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def archive(output, roots):
    count = 0
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=1, allowZip64=True) as target:
        for folder, prefix in roots:
            files = [folder] if folder.is_file() else sorted(p for p in folder.rglob('*') if p.is_file())
            if not files:
                raise ValueError('No selected material: '+str(folder))
            for file in files:
                if file.name.endswith('.part'):
                    raise ValueError('Incomplete download: '+str(file))
                name = prefix+'/'+(file.name if folder.is_file() else file.relative_to(folder).as_posix())
                # Already compressed inputs are stored without wasteful recompression.
                compressed = file.suffix in {'.gz', '.xz', '.bz2', '.zip', '.whl'}
                target.write(file, name, compress_type=zipfile.ZIP_STORED if compressed else zipfile.ZIP_DEFLATED)
                count += 1
    print(json.dumps({'file': output.name, 'files': count, 'bytes': output.stat().st_size, 'sha256': digest(output)}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--build-root', type=Path, required=True)
    args = parser.parse_args()
    build = args.build_root.resolve()
    output = build/'final'/'release'
    output.mkdir(parents=True, exist_ok=True)
    original = json.loads((build/'sources'/'python'/'sources.json').read_text(encoding='utf-8'))
    for record in original:
        if record.get('status') == 'mirrored':
            if digest(build/'sources'/'python'/record['file']) != record['sha256']:
                raise ValueError('Python source changed: '+record['file'])
    groups = {
        'Dependencies-Python': [(build/'sources'/'python', 'python')],
        'Dependencies-Supplemental': [(build/'sources'/'supplemental', 'supplemental')],
        'Dependencies-Native': [(build/'sources'/'native'/name, 'native') for name in [
            'mupdf-1.28.2-source.tar.gz', 'geos-3.13.1.tar.bz2', 'mklml_win_2019.0.5.20190502.zip']],
        'OpenCV-Builds': [(build/'cloud-candidates'/'core-35094639675', 'core'),
                          (build/'cloud-candidates'/'formula-35081772275', 'formula')],
        'Notices': [(build/'final'/'materials', 'materials')],
    }
    native_urls = {
        'mupdf-1.28.2-source.tar.gz': 'https://mupdf.com/downloads/archive/mupdf-1.28.2-source.tar.gz',
        'geos-3.13.1.tar.bz2': 'https://download.osgeo.org/geos/geos-3.13.1.tar.bz2',
        'mklml_win_2019.0.5.20190502.zip': 'https://paddlepaddledeps.bj.bcebos.com/mklml_win_2019.0.5.20190502.zip',
    }
    native_manifest = build/'final'/'materials'/'native-sources.json'
    native_manifest.write_text(json.dumps([
        {'file': name, 'url': url, 'sha256': digest(build/'sources'/'native'/name),
         'kind': 'unmodified proprietary binary rebuild input' if name.startswith('mklml') else 'upstream source archive'}
        for name, url in native_urls.items()], indent=2)+'\n', encoding='utf-8')
    groups['Dependencies-Native'].append((native_manifest, 'native'))
    for name, roots in groups.items():
        archive(output/('Shiye-'+name+'-0.3.1.zip'), roots)


if __name__ == '__main__':
    main()
