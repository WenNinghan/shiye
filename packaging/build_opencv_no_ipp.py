"""Build the locked OpenCV sdist on a disposable Windows runner.

No application environments are changed by this script. Installing build tools
and the resulting wheel is the workflow's explicit responsibility.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = {'core': ('opencv-python', '5.0.0.93'),
            'formula': ('opencv-contrib-python', '4.10.0.84')}
FLAGS = ['-DWITH_IPP:BOOL=OFF', '-DWITH_IPP_IW:BOOL=OFF', '-DWITH_FFMPEG:BOOL=OFF',
         '-DWITH_OBSENSOR=OFF', '-DBUILD_TESTS=OFF', '-DBUILD_PERF_TESTS=OFF',
         '-DBUILD_EXAMPLES=OFF', '-DBUILD_JAVA=OFF']


def source_record(variant):
    name, version = PACKAGES[variant]
    records = json.loads((ROOT/'docs/distribution-materials/python-sources.json').read_text(encoding='utf-8'))
    matches = [r for r in records if (r['name'], r['version']) == (name, version)]
    if len(matches) != 1 or matches[0]['status'] != 'mirrored':
        raise ValueError('Exactly one locked source archive is required')
    return matches[0]


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def check_source(path, record):
    if path.stat().st_size != record['bytes'] or sha256(path) != record['sha256']:
        raise ValueError('Source size/SHA-256 mismatch')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--variant', choices=PACKAGES, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'win32':
        raise RuntimeError('This recipe targets Windows x64 only')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    record = source_record(args.variant)
    source = output/record['file']
    if not record['url'].startswith('https://files.pythonhosted.org/'):
        raise ValueError('Unexpected upstream source host')
    print('Downloading locked source:', record['file'], flush=True)
    with urllib.request.urlopen(record['url'], timeout=120) as response, source.open('wb') as target:
        shutil.copyfileobj(response, target)
    check_source(source, record)
    work = output/'source'
    work.mkdir()
    with tarfile.open(source) as archive:
        archive.extractall(work, filter='data')
    roots = list(work.iterdir())
    if len(roots) != 1 or not (roots[0]/'setup.py').is_file():
        raise ValueError('Unexpected source layout')
    source_root = roots[0]
    env = {**os.environ, 'CMAKE_ARGS': ' '.join(FLAGS),
           'CMAKE_BUILD_PARALLEL_LEVEL': '2', 'ENABLE_CONTRIB': '1' if args.variant == 'formula' else '0'}
    wheels = output/'wheels'
    wheels.mkdir()
    command = [sys.executable, '-m', 'pip', 'wheel', str(source_root), '--no-deps',
               '--no-build-isolation', '--no-cache-dir', '--verbose', '--wheel-dir', str(wheels)]
    evidence = {'variant': args.variant, 'source': {k:record[k] for k in ('name','version','file','url','sha256','bytes')},
                'cmake_args': FLAGS, 'source_patches': [], 'python': sys.version,
                'git_commit': os.environ.get('GITHUB_SHA'), 'run_url':
                f"https://github.com/{os.environ.get('GITHUB_REPOSITORY')}/actions/runs/{os.environ.get('GITHUB_RUN_ID')}"}
    (output/'build-recipe.json').write_text(json.dumps(evidence, indent=2)+'\n', encoding='utf-8')
    (output/'build-environment.txt').write_text(subprocess.check_output(
        [sys.executable, '-m', 'pip', 'freeze', '--all'], text=True), encoding='utf-8')
    result = 1
    try:
        with (output/'build.log').open('w', encoding='utf-8') as log:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       text=True, encoding='utf-8', errors='replace', env=env)
            for line in process.stdout:
                log.write(line)
                print(line, end='', flush=True)
            result = process.wait()
    finally:
        cache_dir = output/'cmake-evidence'
        cache_dir.mkdir()
        for number, cache in enumerate(source_root.rglob('CMakeCache.txt')):
            shutil.copy2(cache, cache_dir/f'{number}-CMakeCache.txt')
    if result:
        raise RuntimeError(f'OpenCV build failed: {result}; see build.log')
    found = list(wheels.glob('*.whl'))
    if len(found) != 1:
        raise RuntimeError('Expected exactly one output wheel')
    (output/'wheel-sha256.txt').write_text(f'{sha256(found[0])}  {found[0].name}\n', encoding='utf-8')
    (output/'SHIYE-BUILD-NOTICE.txt').write_text(
        'Shiye custom build of the attached unmodified upstream source archive.\n'
        'IPP and FFmpeg disabled at compile time; see build-recipe.json.\n'
        'Upstream umbrella license texts can mention components not compiled here.\n'
        'The original source archive, CMake evidence and build environment accompany this wheel.\n'
        'No claim of complete Shiye application license clearance or bit-for-bit reproducibility.\n', encoding='utf-8')


if __name__ == '__main__':
    main()
