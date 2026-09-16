import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile


class ModelPackVersionTests(unittest.TestCase):
    def test_default_and_candidate_version(self):
        builder = Path(__file__).resolve().parents[1] / 'build_model_pack.py'
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            runtime = root / 'runtime'
            runtime.mkdir()
            (runtime / 'shiye-formula.exe').write_bytes(b'fixture-not-executable')
            cache = root / 'cache'
            for name in ('PP-FormulaNet_plus-M', 'PP-DocLayout_plus-L'):
                model = cache / 'official_models' / name
                model.mkdir(parents=True)
                (model / 'inference.json').write_text('{}', encoding='utf-8')
            for version in ('0.3.0', '0.3.1'):
                with self.subTest(version=version):
                    output = root / f'{version}.shiye-model'
                    manifest = root / f'{version}.json'
                    command = [sys.executable, str(builder), '--runtime', str(runtime),
                               '--cache', str(cache), '--output', str(output), '--manifest', str(manifest)]
                    if version != '0.3.0':
                        command += ['--version', version]
                    subprocess.run(command, check=True, capture_output=True)
                    pack = json.loads(manifest.read_text(encoding='utf-8'))['packs'][0]
                    self.assertEqual(pack['id'], 'formula-cpu-' + version)
                    self.assertEqual(pack['sha256'], hashlib.sha256(output.read_bytes()).hexdigest())
                    self.assertEqual(pack['bytes'], output.stat().st_size)
                    with zipfile.ZipFile(output) as archive:
                        self.assertIn('runtime/shiye-formula.exe', archive.namelist())
                        self.assertEqual(pack['unpackedBytes'], sum(i.file_size for i in archive.infolist()))
