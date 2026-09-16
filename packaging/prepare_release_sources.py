"""Mirror exact PyPI source distributions and their notices without executing them.

Missing archives/texts are reported; this does not declare license compliance.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import re
import sys
import tarfile
import urllib.request
import zipfile


def fetch_json(url):
    with urllib.request.urlopen(url, timeout=45) as response:
        return json.load(response)


def prepare(item, output, notices):
    name, version = item
    result = {'name': name, 'version': version}
    try:
        meta = fetch_json(f'https://pypi.org/pypi/{name}/{version}/json')
        sources = [f for f in meta['urls'] if f['packagetype'] == 'sdist']
        if not sources:
            result.update(status='NO-SDIST', project_urls=meta['info'].get('project_urls'))
            return result
        entry = sources[0]
        filename = entry['filename']
        if Path(filename).name != filename or not entry['url'].startswith('https://files.pythonhosted.org/'):
            raise ValueError('Unexpected source location')
        archive = output / filename
        expected = entry['digests']['sha256']
        if not archive.exists():
            part = archive.with_name(archive.name+'.part')
            with urllib.request.urlopen(entry['url'], timeout=60) as response, part.open('wb') as stream:
                digest = hashlib.sha256()
                count = 0
                while data := response.read(1024*1024):
                    count += len(data)
                    if count > entry['size']:
                        raise ValueError('Source larger than PyPI metadata')
                    stream.write(data)
                    digest.update(data)
            if digest.hexdigest() != expected or count != entry['size']:
                raise ValueError('Source digest/size mismatch')
            part.replace(archive)
        with archive.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
                raise ValueError('Existing archive digest mismatch')
        destination = notices / re.sub(r'[^a-zA-Z0-9_.-]', '_', name+'-'+version)
        texts = []
        def save(path, data):
            parts = Path(path).parts
            if Path(path).is_absolute() or Path(path).drive or ':' in path or '..' in parts:
                raise ValueError('Unsafe archive path')
            target = destination / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            texts.append(target.relative_to(notices).as_posix())
        pattern = re.compile(r'(license|licence|copying|notice|copyright|authors|eula|third.party)', re.I)
        if filename.endswith('.zip'):
            with zipfile.ZipFile(archive) as z:
                for info in z.infolist():
                    if pattern.search(info.filename) and 0 < info.file_size < 2_000_000 and not info.is_dir():
                        save(info.filename, z.read(info))
        else:
            with tarfile.open(archive) as t:
                for member in t:
                    if pattern.search(member.name) and member.isfile() and 0 < member.size < 2_000_000:
                        save(member.name, t.extractfile(member).read())
        result.update(status='mirrored', file=filename, url=entry['url'], sha256=expected,
                      bytes=entry['size'], license_files=texts)
    except Exception as error:
        result.update(status='ERROR', error=str(error))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--inventory', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--notices', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    items = {(r['name'], r['version']) for f in args.inventory for r in json.loads(f.read_text(encoding='utf-8'))['components']}
    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        tasks = [pool.submit(prepare, item, args.output, args.notices) for item in sorted(items)]
        for task in as_completed(tasks):
            result = task.result()
            results.append(result)
            print(result['name'], result['version'], result['status'], flush=True)
    (args.output/'sources.json').write_text(json.dumps(sorted(results, key=lambda r: (r['name'],r['version'])), ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    # NO-SDIST is a documented gap, not an implicit license/source approval.
    # Actual network/integrity failures must also fail the calling build step.
    sys.exit(1 if any(r['status'] == 'ERROR' for r in results) else 0)
