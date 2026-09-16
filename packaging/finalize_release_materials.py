"""Combine the existing 0.3.1 inventory with original notices and source inputs.

This is a release assembly tool, not a license compatibility classifier.
Downloads are data only: no downloaded code is executed. All output stays
below --build-root; the generated HTML escapes every third-party text.
"""
import argparse
import concurrent.futures
import hashlib
import html
import json
import re
import shutil
import tarfile
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = 'https://github.com/WenNinghan/shiye/releases/tag/v0.3.1'
UPSTREAM = {
    'flatbuffers-25.12.19': ('google/flatbuffers', '282dcb1c3266b45600510da4810092f6ec4c85f2'),
    'rapidocr-1.4.4': ('RapidAI/RapidOCR', 'd6c6daf850a8fcc0ddf220aff88357faf423ec51'),
    'latex2mathml-3.81.1': ('roniemartinez/latex2mathml', '994752d5553ab813ffb8a17e049a1b3893b4cc80'),
    'onnxruntime-1.29.0': ('microsoft/onnxruntime', '2e2543fbe9fae542f921d47a72d21d5a4ef0b710'),
    'paddlepaddle-3.3.1': ('PaddlePaddle/Paddle', '7688495538f4d6c1893f084dd238a402e8f68ab6'),
    'oneDNN-3.6.2': ('oneapi-src/oneDNN', '28d696724426b943e2f4a0e607f90cdc19aedaf6'),
}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def download(url, path, expected=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and (not expected or sha(path) == expected):
        return
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'Shiye-release-materials/0.3.1'})
            with urllib.request.urlopen(request, timeout=60) as response, path.with_suffix(path.suffix+'.part').open('wb') as target:
                shutil.copyfileobj(response, target, length=1024*1024)
            part = path.with_suffix(path.suffix+'.part')
            if expected and sha(part) != expected:
                raise ValueError('SHA-256 mismatch: '+path.name)
            part.replace(path)
            return
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2)


def get_json(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.load(response)


def collect(build):
    extra = build/'sources'/'supplemental'
    extra.mkdir(parents=True, exist_ok=True)
    jobs = []
    for name, (repo, revision) in UPSTREAM.items():
        jobs.append({'name': name, 'url': f'https://codeload.github.com/{repo}/tar.gz/{revision}',
                     'file': name+'.tar.gz', 'revision': revision,
                     'scope': 'Upstream repository snapshot; nested dependency URLs and pins remain in upstream build scripts.'})
    jobs.append({'name': 'CPython-3.12.14', 'url': 'https://www.python.org/ftp/python/3.12.14/Python-3.12.14.tar.xz',
                 'file': 'Python-3.12.14.tar.xz', 'scope': 'Official CPython source distribution.'})
    # These distributions have no sdist. Their pure-Python wheels contain the
    # preferred .py source, metadata and (for RapidOCR) separately licensed models.
    for name, version in [('aistudio_sdk','0.3.9'), ('flatbuffers','25.12.19'), ('rapidocr-onnxruntime','1.4.4')]:
        metadata = get_json(f'https://pypi.org/pypi/{name}/{version}/json')
        wheel = next(item for item in metadata['urls'] if item['filename'].endswith('none-any.whl'))
        jobs.append({'name': name+'-'+version, 'url': wheel['url'], 'file': wheel['filename'],
                     'expected_sha256': wheel['digests']['sha256'],
                     'scope': 'Original pure-Python source-containing wheel, not a substitute for native source.'})
    notices = [
        ('bce-python-sdk-LICENSE.txt', 'baidubce/bce-sdk-python', 'b1979d1e63240b88ef8c68c0456800e0d9ae31bf', 'LICENSE'),
        ('oneDNN-LICENSE.txt', 'oneapi-src/oneDNN', UPSTREAM['oneDNN-3.6.2'][1], 'LICENSE'),
    ]
    for filename, repo, revision, source in notices:
        jobs.append({'name': filename, 'url': f'https://raw.githubusercontent.com/{repo}/{revision}/{source}',
                     'file': filename, 'scope': 'Original upstream license text at stated revision.'})
    def perform(record):
        target = extra/record['file']
        download(record['url'], target, record.get('expected_sha256'))
        record.update(sha256=sha(target), bytes=target.stat().st_size)
        print('Collected '+record['file'], flush=True)
        return record
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(perform, jobs))
    for component, filename in [('flatbuffers-25.12.19','flatbuffers-LICENSE.txt'),
                                ('latex2mathml-3.81.1','latex2mathml-LICENSE.txt'),
                                ('rapidocr-1.4.4','RapidOCR-LICENSE.txt')]:
        with tarfile.open(extra/(component+'.tar.gz')) as archive:
            member = next(m for m in archive.getmembers() if len(Path(m.name).parts) == 2 and Path(m.name).name == 'LICENSE')
            (extra/filename).write_bytes(archive.extractfile(member).read())
        records.append({'name': filename, 'file': filename, 'source_archive': component+'.tar.gz',
                        'sha256': sha(extra/filename), 'bytes': (extra/filename).stat().st_size})
    (extra/'sources.json').write_text(json.dumps(records, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def copy_tree(source, target):
    if not source.is_dir():
        raise FileNotFoundError(source)
    shutil.copytree(source, target, dirs_exist_ok=True)


def assemble(build, python_base):
    material = build/'final'/'materials'
    notices = material/'notices'
    copy_tree(build/'candidate'/'notices'/'core', notices/'core')
    copy_tree(build/'candidate'/'notices'/'formula', notices/'formula')
    copy_tree(build/'candidate'/'notices'/'native', notices/'native')
    copy_tree(build/'notices'/'source-notices', notices/'source-supplements')
    extra = build/'sources'/'supplemental'
    supplement = notices/'upstream-supplements'
    supplement.mkdir(parents=True, exist_ok=True)
    for file in extra.glob('*LICENSE.txt'):
        shutil.copy2(file, supplement/file.name)
    shutil.copy2(python_base/'LICENSE.txt', supplement/'Python-3.12.14-LICENSE.txt')
    shutil.copy2(ROOT/'LICENSE', notices/'Shiye-MIT.txt')
    copy_tree(ROOT/'licenses', notices/'project-and-models')
    for scope, packages in {'web': ['react','react-dom','scheduler','katex','mathlive','html-to-image','lucide-react'],
                            'desktop': ['yauzl','buffer-crc32','pend']}.items():
        for package in packages:
            folder = ROOT/scope/'node_modules'/package
            meta = json.loads((folder/'package.json').read_text(encoding='utf-8'))
            target = notices/'javascript'/(package+'-'+meta['version'])
            target.mkdir(parents=True, exist_ok=True)
            matched = []
            for file in folder.rglob('*'):
                if file.is_file() and re.search(r'license|licence|copying|notice|ofl', file.name, re.I):
                    dest = target/file.relative_to(folder)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file, dest)
                    matched.append(dest)
            if not matched:
                raise ValueError('Missing JavaScript notice: '+package)
    electron = ROOT/'desktop'/'node_modules'/'electron'/'dist'
    for name in ('LICENSE', 'LICENSES.chromium.html'):
        shutil.copy2(electron/name, supplement/('Electron-'+name))
    coverage = []
    named = {'flatbuffers': 'flatbuffers-LICENSE.txt', 'latex2mathml': 'latex2mathml-LICENSE.txt',
             'rapidocr-onnxruntime': 'RapidOCR-LICENSE.txt', 'bce-python-sdk': 'bce-python-sdk-LICENSE.txt'}
    for scope in ('core', 'formula'):
        inventory = json.loads((notices/scope/'inventory.json').read_text(encoding='utf-8'))
        for component in inventory['components']:
            paths = [scope+'/'+record['file'] for record in component['notices']]
            if not paths:
                name = component['name']
                if name in named:
                    paths = ['upstream-supplements/'+named[name]]
                else:
                    directory = notices/'source-supplements'/(name+'-'+component['version'])
                    paths = [p.relative_to(notices).as_posix() for p in directory.rglob('*') if p.is_file()]
            if not paths or not all((notices/path).is_file() for path in paths):
                raise ValueError('Unresolved notice: '+component['name'])
            coverage.append({'scope': scope, 'name': component['name'], 'version': component['version'],
                             'notice_files': paths, 'status': 'text-present-original-or-source-supplement'})
    (material/'notice-coverage.json').write_text(json.dumps(coverage, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    # Retain original bytes separately; render as escaped text, never executable HTML.
    sections = []
    seen = {}
    for file in sorted(notices.rglob('*')):
        if file.is_file() and file.suffix.lower() not in {'.json', '.png', '.svg', '.html', '.h', '.hpp', '.cc', '.c', '.py'}:
            seen.setdefault(sha(file), []).append(file)
    for files in seen.values():
            text = files[0].read_text(encoding='utf-8', errors='replace')
            names = ' | '.join(file.relative_to(notices).as_posix() for file in files)
            sections.append('<details><summary>'+html.escape(names)+
                            '</summary><pre>'+html.escape(text)+'</pre></details>')
    intro = (ROOT/'docs'/'release-license-scope.md').read_text(encoding='utf-8')
    page = '''<!doctype html><html lang="zh-CN"><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>识页 · 开源许可与源码</title><style>body{max-width:1000px;margin:32px auto;padding:0 20px;font:16px/1.7 system-ui;background:#fafbf7;color:#223329}a{color:#28693c}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.55 monospace}details{border:1px solid #ccd9c8;border-radius:8px;margin:10px 0;padding:12px}summary{cursor:pointer;overflow-wrap:anywhere}</style>
<a href="/">← 返回识页</a><h1>开源许可与源码 · 0.3.1</h1><p>本页正文随应用保存，可以离线阅读。使用浏览器查找可按组件名称检索。公开源码下载需要联网。</p>'''
    page += '<pre>'+html.escape(intro)+'</pre><p><a href="'+RELEASE+'">GitHub 固定版本下载与源码材料</a></p>'
    page += '<p><a href="chromium.txt">Electron / Chromium 完整第三方声明（大文件，按需阅读）</a></p>'
    page += ''.join(sections)+'</html>'
    target = ROOT/'web'/'public'/'licenses'/'index.html'
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(supplement/'Electron-LICENSES.chromium.html', target.parent/'chromium.txt')
    target.write_text(page, encoding='utf-8')
    shutil.copy2(target, material/'licenses.html')
    shutil.copy2(target.parent/'chromium.txt', material/'chromium.txt')
    shutil.copy2(ROOT/'docs'/'release-license-scope.md', material/'LICENSE-SCOPE.md')
    shutil.copy2(ROOT/'docs'/'distribution-materials'/'models.md', material/'MODEL-SOURCES.md')
    print(json.dumps({'notice_files': len(sections), 'html_bytes': target.stat().st_size}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['collect','assemble'])
    parser.add_argument('--build-root', type=Path, required=True)
    parser.add_argument('--python-base', type=Path)
    args = parser.parse_args()
    if args.phase == 'collect':
        collect(args.build_root.resolve())
    else:
        if not args.python_base:
            parser.error('assemble requires --python-base')
        assemble(args.build_root.resolve(), args.python_base)
