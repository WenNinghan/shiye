import importlib.util
from pathlib import Path
import tempfile
import unittest


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parents[1]/(name+'.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build = load('build_opencv_no_ipp')
verify = load('verify_opencv_no_ipp')


class OpenCVBuildTests(unittest.TestCase):
    def test_exact_sources(self):
        for variant in build.PACKAGES:
            entry = build.source_record(variant)
            self.assertEqual(len(entry['sha256']), 64)
            self.assertGreater(entry['bytes'], 1_000_000)

    def test_cache_requires_all_flags_off(self):
        good = '\n'.join(f'{flag}:BOOL=OFF' for flag in ('WITH_IPP','WITH_IPP_IW','WITH_FFMPEG'))
        verify.verify_cache(good)
        for bad in (good.replace('WITH_IPP:BOOL=OFF','WITH_IPP:BOOL=ON'), '', good.replace('WITH_FFMPEG:BOOL=OFF','')):
            with self.assertRaises(ValueError):
                verify.verify_cache(bad)

    def test_build_info_rejects_ipp_or_ffmpeg(self):
        good = 'General configuration for OpenCV 5.0.0\n  FFMPEG: NO\n'
        verify.verify_build_info(good)
        for bad in ('', good+'  Intel IPP: 2026.0.0\n', good.replace('NO','YES')):
            with self.assertRaises(ValueError):
                verify.verify_build_info(bad)

    def test_source_digest_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.tar.gz'
            path.write_bytes(b'not source')
            with self.assertRaises(ValueError):
                build.check_source(path, {'bytes':10, 'sha256':'0'*64})


if __name__ == '__main__':
    unittest.main()
