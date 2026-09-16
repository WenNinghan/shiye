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
    def test_no_ffmpeg_patch_both_locked_patterns(self):
        for digits in (3, 4):
            with self.subTest(digits=digits), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                setup = root/'setup.py'
                entry = r'[r"bin/opencv_videoio_ffmpeg\d{' + str(digits) + r'}%s\.dll" % ("_64" if is64 else "")]'
                setup.write_text('files = (\n    '+entry+'\n    if os.name == "nt"\n    else []\n)\nkeep = 123\n', encoding='utf-8')
                record = build.patch_ffmpeg_packaging(setup, root)
                self.assertIn('keep = 123', setup.read_text())
                self.assertNotIn('opencv_videoio_ffmpeg', setup.read_text())
                self.assertTrue((root/record['patch']).is_file())
                self.assertNotEqual(record['before_sha256'], record['after_sha256'])

    def test_patch_rejects_unknown_or_already_patched_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            setup = root/'setup.py'
            setup.write_text('files = []\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                build.patch_ffmpeg_packaging(setup, root)
            self.assertEqual(setup.read_text(), 'files = []\n')

    def test_core_uses_existing_sgemm_fallback_only(self):
        flag = '-DCMAKE_ASM_COMPILER:FILEPATH=NOTFOUND'
        self.assertIn(flag, build.build_flags('core'))
        self.assertNotIn(flag, build.build_flags('formula'))
        self.assertNotIn('-DBUILD_opencv_dnn=OFF', build.build_flags('core'))

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
