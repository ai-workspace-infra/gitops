from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
NAME = 'github-actions-platform-ops-toolkit-prod-k3s-v6-bootstrap-reader'


class BootstrapReader(unittest.TestCase):
    def test_only_ssh_and_os_identity_paths_and_protected_workflow(self):
        policy = yaml.safe_load((ROOT / f'security/vault/policies/{NAME}.yaml').read_text())['spec']['paths']
        paths = {item['path']: set(item['capabilities']) for item in policy}
        expected = {'kv/data/prod/platform/prod-k3s-v6/ssh'} | {f'kv/data/prod/security/{role}' for role in ('root', 'operator', 'auditor')}
        self.assertEqual(paths, {path: {'read'} for path in expected})
        role = yaml.safe_load((ROOT / f'security/vault/roles/{NAME}.yaml').read_text())['spec']
        self.assertEqual(role['token_policies'], [NAME])
        self.assertTrue(role['token_no_default_policy'])
        self.assertEqual(role['bound_claims']['environment'], 'prod')
        self.assertEqual(role['bound_claims']['ref'], ['refs/heads/main'])
        self.assertEqual(role['bound_claims']['ref_protected'], 'true')
        self.assertEqual(role['bound_claims']['workflow_ref'], 'ai-workspace-infra/Platform-Orchestrator/.github/workflows/selfhost-stage-deploy.yml@refs/heads/main')


if __name__ == '__main__':
    unittest.main()
