from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]


class ServiceSecrets(unittest.TestCase):
    def test_each_secret_has_one_exact_reader_and_no_cross_path_policy(self):
        cases = [
            ('postgresql-prod', 'postgresql-admin', 'prod/database/postgresql/admin', 'password'),
            ('postgresql-prod', 'postgresql-operator', 'prod/database/postgresql/operator', 'password'),
            ('postgresql-prod', 'postgresql-auditor', 'prod/database/postgresql/auditor', 'password'),
            ('web-saas-prod', 'web-saas-secrets', 'prod/accounts/runtime', 'INTERNAL_SERVICE_TOKEN'),
        ]
        roles = set()
        for namespace, name, path, field in cases:
            docs = list(yaml.safe_load_all((ROOT/f'services/prod-k3s-v6/{namespace}/vault-secrets.yaml').read_text()))
            external = next(d for d in docs if d['kind'] == 'ExternalSecret' and d['metadata']['name'] == name)
            self.assertEqual(external['spec']['data'], [{'secretKey': field, 'remoteRef': {'key': path, 'property': field}}])
            principal = external['spec']['secretStoreRef']['name']
            store = next(d for d in docs if d['kind'] == 'SecretStore' and d['metadata']['name'] == principal)
            jwt = store['spec']['provider']['vault']['auth']['jwt']
            operation = yaml.safe_load((ROOT/f'operations/workload-identities/prod-k3s-v6/{principal}.yaml').read_text())['spec']['identity']
            self.assertEqual(jwt['role'], operation['role'])
            self.assertEqual(jwt['kubernetesServiceAccountToken']['serviceAccountRef']['name'], operation['serviceAccount'])
            self.assertEqual(jwt['kubernetesServiceAccountToken']['audiences'], [operation['audience']])
            self.assertEqual(operation['allowedPath'], 'kv/data/' + path)
            self.assertNotEqual(operation['deniedPath'], operation['allowedPath'])
            roles.add(operation['role'])
        self.assertEqual(len(roles), 4)
        admin = 'github-actions-platform-ops-toolkit-prod-k3s-v6-service-secret-admin'
        policy = yaml.safe_load((ROOT/f'security/vault/policies/{admin}.yaml').read_text())['spec']['paths']
        paths = {entry['path'] for entry in policy}
        self.assertFalse(any('*' in path or path.startswith('kv/') for path in paths))
        for role in roles:
            self.assertIn('sys/policies/acl/' + role, paths)
            self.assertIn('auth/jwt-prod-k3s-v6/role/' + role, paths)


if __name__ == '__main__':
    unittest.main()
