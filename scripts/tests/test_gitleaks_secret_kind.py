"""Exercise the actual pinned scanner against synthetic YAML, without credentials."""
import base64
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

CONFIG = Path(__file__).resolve().parents[2] / '.gitleaks.toml'

class SecretKindTest(unittest.TestCase):
    def test_exact_secret_kind(self):
        for kind, expected in [('Secret', 1), ('"Secret"', 1), ('Secret # comment', 1), ('SecretStore', 0), ('ClusterSecretStore', 0), ('ExternalSecret', 0)]:
            for reverse in (False, True):
                with self.subTest(kind=kind, reverse=reverse), tempfile.TemporaryDirectory() as tmp:
                    payload = base64.b64encode(b'synthetic-fixture-only').decode()
                    parts = [f'kind: {kind}\n', f'data:\n  password: {payload}\n']
                    if reverse:
                        parts.reverse()
                    Path(tmp, 'fixture.yaml').write_text('apiVersion: v1\n' + ''.join(parts))
                    result = subprocess.run([os.environ.get('GITLEAKS_BIN', 'gitleaks'), 'detect', '--no-git', '--source', tmp, '--config', str(CONFIG), '--redact', '--report-format', 'json', '--report-path', str(Path(tmp, 'report.json')), '--exit-code', '1'], capture_output=True)
                    self.assertIn(result.returncode, (0, 1), result.stderr.decode())
                    findings = json.loads(Path(tmp, 'report.json').read_text())
                    matched = any(item['RuleID'] == 'kubernetes-secret-yaml' for item in findings)
                    self.assertEqual(bool(expected), matched, result.stderr.decode())

if __name__ == '__main__':
    unittest.main()
