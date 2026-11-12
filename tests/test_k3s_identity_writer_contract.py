from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
NAME = 'github-actions-platform-ops-toolkit-prod-k3s-v6-identity-writer'
SIT_NAME = 'github-actions-platform-ops-toolkit-sit-k3s-v6-identity-writer'


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
        self.assertEqual(claims['workflow_ref'], 'ai-workspace-infra/Platform-Orchestrator/.github/workflows/selfhost-stage-deploy-container.yml@refs/heads/main')


    def test_sit_writer_matches_declaration(self):
        policy = document(f'security/vault/policies/{SIT_NAME}.yaml')['spec']
        paths = {item['path']: set(item['capabilities']) for item in policy['paths']}
        self.assertEqual(paths, {f'kv/data/sit/sit-k3s-v6/{role}': {'create', 'read'} for role in ('root', 'operator', 'auditor')})
        role = document(f'security/vault/roles/{SIT_NAME}.yaml')['spec']
        self.assertEqual(role['token_policies'], [SIT_NAME])
        self.assertEqual(role['bound_claims']['environment'], 'sit')
        host = document('resources/svc.plus/sit/Contabo-VPS/sit-k3s-v6.yaml')['hosts'][0]['host_vars']
        self.assertEqual(host['k3s_identity_vault_writer_role'], SIT_NAME)
        self.assertEqual(host['k3s_identity_environment'], 'sit')
        self.assertEqual(sorted(host['k3s_identity_checks']), ['auditor', 'operator', 'root'])
        self.assertTrue(all(k.startswith(('k3s_identity_', 'k3s_platform_')) for k in host))


if __name__ == '__main__':
    unittest.main()
