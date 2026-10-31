from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
NAME = 'github-actions-platform-ops-toolkit-prod-k3s-v6-identity-writer'


def document(path):
    return yaml.safe_load((ROOT / path).read_text())


class WriterContract(unittest.TestCase):
    def test_exact_create_read_paths_and_protected_deploy_binding(self):
        policy = document(f'security/vault/policies/{NAME}.yaml')['spec']
        paths = {item['path']: set(item['capabilities']) for item in policy['paths']}
        self.assertEqual(paths, {f'kv/data/prod/prod-k3s-v6/{role}': {'create', 'read'} for role in ('root', 'operator', 'auditor')})
        role = document(f'security/vault/roles/{NAME}.yaml')['spec']
        self.assertEqual(role['token_policies'], [NAME])
        self.assertTrue(role['token_no_default_policy'])
        self.assertEqual(role['bound_audiences'], ['vault'])
        self.assertEqual(role['token_explicit_max_ttl'], '30m')
        claims = role['bound_claims']
        self.assertEqual(claims['repository'], 'ai-workspace-infra/Platform-Orchestrator')
        self.assertEqual(claims['environment'], 'prod')
        self.assertEqual(claims['ref_protected'], 'true')
        self.assertEqual(claims['ref'], ['refs/heads/main'])
        self.assertEqual(claims['workflow_ref'], 'ai-workspace-infra/Platform-Orchestrator/.github/workflows/selfhost-stage-deploy.yml@refs/heads/main')


if __name__ == '__main__':
    unittest.main()
