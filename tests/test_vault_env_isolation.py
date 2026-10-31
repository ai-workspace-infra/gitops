"""Isolation tests for scripts/validate-vault-env-isolation.py (no Vault)."""
import pathlib, shutil, subprocess, sys, tempfile, unittest
import yaml

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / 'scripts/validate-vault-env-isolation.py'
POL = 'security/vault/policies/github-actions-platform-ops-toolkit-uat-compute-cleanup.yaml'
EXC = 'security/vault-exceptions/cross-env-paths.yaml'


class T(unittest.TestCase):
    def setUp(self):
        self.d = pathlib.Path(tempfile.mkdtemp())
        for rel in (POL, EXC):
            (self.d / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(REPO / rel, self.d / rel)

    def tearDown(self):
        shutil.rmtree(self.d)

    def run_v(self, date='2026-11-01'):
        return subprocess.run([sys.executable, SCRIPT, self.d, date], capture_output=True, text=True)

    def edit(self, rel, fn):
        p = self.d / rel; doc = yaml.safe_load(p.read_text()); fn(doc); p.write_text(yaml.safe_dump(doc))

    def test_current_declarations_pass(self):
        self.assertEqual(self.run_v().returncode, 0)

    def test_unregistered_cross_env_path_fails(self):
        self.edit(POL, lambda d: d['spec']['paths'].append({'path': 'kv/data/prod/serverless/gcp', 'capabilities': ['read']}))
        r = self.run_v(); self.assertNotEqual(r.returncode, 0); self.assertIn('outside uat scope', r.stderr)

    def test_widened_capability_fails(self):
        def f(d):
            for p in d['spec']['paths']:
                if 'github-app' in p['path']: p['capabilities'] = ['read', 'list']
        self.edit(POL, f); self.assertNotEqual(self.run_v().returncode, 0)

    def test_exception_cannot_grant_write(self):
        self.edit(EXC, lambda d: d['spec']['exceptions'][0].update(capabilities=['read', 'update']))
        self.assertNotEqual(self.run_v().returncode, 0)

    def test_expired_exception_fails(self):
        self.assertNotEqual(self.run_v('2027-01-01').returncode, 0)

    def test_stale_exception_fails_after_path_removed(self):
        self.edit(POL, lambda d: d['spec'].update(paths=[p for p in d['spec']['paths'] if 'github-app' not in p['path']]))
        r = self.run_v(); self.assertNotEqual(r.returncode, 0); self.assertIn('stale exception', r.stderr)


if __name__ == '__main__':
    unittest.main()
