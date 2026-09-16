"""Offline tests: collecting texts is evidence, never an approval verdict."""
import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sources = load('prepare_release_sources')
collector = load('collect_release_notices')


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / 'sources'
        self.output.mkdir()
        self.notices = self.root / 'notices'

    def prepare_zip(self, entries, corrupt=False):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as archive:
            for path, text in entries.items():
                archive.writestr(path, text)
        data = stream.getvalue()
        entry = {'packagetype': 'sdist', 'filename': 'example-1.zip',
                 'url': 'https://files.pythonhosted.org/example-1.zip',
                 'size': len(data), 'digests': {'sha256': '0'*64 if corrupt else hashlib.sha256(data).hexdigest()}}
        with patch.object(sources, 'fetch_json', return_value={'urls': [entry]}), \
             patch.object(sources.urllib.request, 'urlopen', return_value=io.BytesIO(data)):
            return sources.prepare(('example', '1'), self.output, self.notices)

    def test_license_directory_and_eula_not_just_basename(self):
        result = self.prepare_zip({'pkg/LICENSES/Apache-2.0.txt': 'text',
                                   'pkg/EULA.rtf': 'eula', 'pkg/run.py': 'never run'})
        self.assertEqual(result['status'], 'mirrored')
        self.assertEqual(len(result['license_files']), 2)
        self.assertFalse((self.notices/'example-1/pkg/run.py').exists())

    def test_digest_mismatch_does_not_publish_archive(self):
        result = self.prepare_zip({'LICENSE': 'text'}, corrupt=True)
        self.assertEqual(result['status'], 'ERROR')
        self.assertFalse((self.output/'example-1.zip').exists())

    def test_parent_traversal_rejected(self):
        result = self.prepare_zip({'../LICENSE': 'unsafe'})
        self.assertEqual(result['status'], 'ERROR')
        self.assertFalse((self.root/'LICENSE').exists())

    def test_windows_drive_relative_rejected(self):
        result = self.prepare_zip({'C:LICENSE': 'unsafe'})
        self.assertEqual(result['status'], 'ERROR')

    def test_no_sdist_stays_explicit_gap(self):
        with patch.object(sources, 'fetch_json', return_value={'urls': [], 'info': {'project_urls': None}}):
            result = sources.prepare(('example', '1'), self.output, self.notices)
        self.assertEqual(result['status'], 'NO-SDIST')
        self.assertNotIn('sha256', result)

    def test_unknown_pyinstaller_schema_rejected(self):
        toc = self.root/'Analysis-00.toc'
        toc.write_text('([],)', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Unsupported Analysis schema'):
            collector.inventory(toc, self.notices)


if __name__ == '__main__':
    unittest.main()
