"""Fail closed on missing compile evidence, then test the installed wheel."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import zipfile


def verify_cache(text):
    for flag in ('WITH_IPP', 'WITH_IPP_IW', 'WITH_FFMPEG'):
        match = re.search(rf'^{flag}:BOOL=(\S+)\s*$', text, re.M)
        if not match or match.group(1).upper() not in {'OFF', 'FALSE', '0', 'NO'}:
            raise ValueError(f'{flag} must explicitly be OFF in CMakeCache')


def verify_build_info(text):
    if not re.search(r'General configuration for OpenCV', text):
        raise ValueError('Missing OpenCV build information')
    for name in ('Intel IPP', 'Intel IPP IW', 'FFMPEG'):
        for value in re.findall(rf'^\s*{re.escape(name)}:\s*(.*)$', text, re.M):
            if value.strip().upper() not in {'NO', 'OFF', 'DISABLED'}:
                raise ValueError(f'Unexpected enabled build component: {name}={value}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.output
    recipe = json.loads((root/'build-recipe.json').read_text(encoding='utf-8'))
    caches = list((root/'cmake-evidence').glob('*CMakeCache.txt'))
    applicable = [p.read_text(encoding='utf-8', errors='replace') for p in caches if 'WITH_IPP:BOOL=' in p.read_text(encoding='utf-8', errors='replace')]
    if not applicable:
        raise ValueError('No OpenCV CMake cache evidence')
    for text in applicable:
        verify_cache(text)
    wheels = list((root/'wheels').glob('*.whl'))
    if len(wheels) != 1:
        raise ValueError('Expected one wheel')
    with zipfile.ZipFile(wheels[0]) as archive:
        forbidden = [n for n in archive.namelist() if Path(n).suffix.lower() in {'.dll','.pyd','.lib'}
                     and re.search(r'(^|[/_])(?:ipp|ffmpeg)|opencv_videoio_ffmpeg', n, re.I)]
        if forbidden:
            raise ValueError(f'Forbidden wheel binaries: {forbidden}')
        # Check the imported extension is the exact file from the candidate wheel.
        import cv2
        installed = Path(cv2.__file__).parent
        extensions = 0
        for name in archive.namelist():
            if name.startswith('cv2/') and name.endswith('.pyd'):
                extensions += 1
                actual = installed/Path(name).relative_to('cv2')
                if hashlib.sha256(actual.read_bytes()).digest() != hashlib.sha256(archive.read(name)).digest():
                    raise ValueError('Installed extension does not match candidate wheel')
        if extensions == 0:
            raise ValueError('No cv2 extension in candidate wheel')
    info = cv2.getBuildInformation()
    (root/'opencv-build-info.txt').write_text(info, encoding='utf-8')
    verify_build_info(info)
    if recipe['variant'] == 'core' and not re.search(r'^\s*DNN MLAS:\s*NO\b', info, re.M):
        raise ValueError('Core build must report the non-MLAS DNN fallback')
    if cv2.ipp.useIPP():
        raise ValueError('IPP runtime is enabled')
    name, version = recipe['source']['name'], recipe['source']['version']
    if importlib.metadata.version(name) != version:
        raise ValueError('Unexpected installed package version')
    import numpy as np
    image = np.full((120, 240, 3), 255, dtype=np.uint8)
    cv2.rectangle(image, (20, 20), (180, 90), (0, 0, 0), 2)
    binary = cv2.threshold(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), 190, 255, cv2.THRESH_BINARY_INV)[1]
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    assert contours
    ok, encoded = cv2.imencode('.png', image)
    assert ok and cv2.imdecode(encoded, cv2.IMREAD_COLOR).shape == image.shape
    report = {'package':name, 'version':version, 'opencv':cv2.__version__,
              'compile_flags_verified':True, 'ipp_runtime_enabled':False, 'image_smoke':True,
              'full_application_release_approved':False}
    (root/'verification.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
