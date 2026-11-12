"""Contract for the additive kv/<env>/platform/domains TLS path migration.

Old kv/CICD/domains paths stay in place. Reader policies gain matching
read (and mirrored metadata) on the new env-scoped paths. The TLS
rotation policy keeps the same write capabilities on both sit and prod
new paths. No Vault access.
"""
from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
POLICIES = ROOT / 'security/vault/policies'
OLD_PREFIXES = ('kv/data/CICD/domains/', 'kv/metadata/CICD/domains/')

# Destinations that exist in this migration. There is no
# kv/{dev,uat,shared}/platform/domains layout.
PLATFORM_ENVS = ('sit', 'prod')

# Denied-probe entry lives only on a workload-identity allowedPath
# (singular, not a list) and is not a real domain; do not migrate it.
DENIED_PROBE = 'v6-authorization-denied-probe'


def policy_envs_and_mode(name):
    """Return (envs, capability_mode) for a policy that reads CICD/domains."""
    if name == 'github-actions-platform-ops-toolkit-tls-rotation':
        return ('sit', 'prod'), 'same'
    if name.startswith('sit-') or name.endswith('-sit') or '-sit-' in name:
        return ('sit',), 'read'
    if name.startswith('prod-') or name.endswith('-prod') or '-prod-' in name:
        return ('prod',), 'read'
    # toolkit-<env> and toolkit-<env>-* suffixes, including uat-xconnect-*.
    for env in ('sit', 'prod', 'dev', 'uat'):
        token = f'github-actions-platform-ops-toolkit-{env}'
        if name == token or name.startswith(token + '-'):
            if env in ('dev', 'uat'):
                return ('sit',), 'read'
            return (env,), 'read'
    if 'shared' in name:
        # Shared policies have no dedicated platform/domains env; grant both.
        return ('sit', 'prod'), 'read'
    raise AssertionError(f'unmapped policy that reads CICD/domains: {name}')


def new_path(old_path, env):
    for prefix, kind in (('kv/data/CICD/domains/', 'data'), ('kv/metadata/CICD/domains/', 'metadata')):
        if old_path.startswith(prefix):
            rest = old_path[len(prefix):]
            return f'kv/{kind}/{env}/platform/domains/{rest}'
    raise AssertionError(f'not a CICD/domains path: {old_path}')


def data_capabilities(mode, old_caps):
    return list(old_caps) if mode == 'same' else ['read']


def metadata_capabilities(old_caps):
    return list(old_caps)


class PlatformDomainTlsPolicyMigration(unittest.TestCase):
    def policies(self):
        docs = []
        for path in sorted(POLICIES.glob('*.yaml')):
            doc = yaml.safe_load(path.read_text())
            if doc and doc.get('kind') == 'VaultACLPolicy':
                docs.append((path, doc))
        return docs

    def test_every_cicd_domains_reader_gains_new_paths_and_keeps_old(self):
        seen = []
        for path, doc in self.policies():
            name = doc['metadata']['name']
            entries = {(item['path'], tuple(item['capabilities'])) for item in doc['spec']['paths']}
            paths = {item['path'] for item in doc['spec']['paths']}
            old = [item for item in doc['spec']['paths'] if item['path'].startswith(OLD_PREFIXES)]
            if not old:
                self.assertFalse(
                    any('/platform/domains/' in item['path'] for item in doc['spec']['paths']),
                    f'{path} has new platform/domains paths but no CICD/domains source',
                )
                continue
            seen.append(name)
            envs, mode = policy_envs_and_mode(name)
            for env in envs:
                self.assertIn(env, PLATFORM_ENVS)
            for item in old:
                self.assertNotIn(DENIED_PROBE, item['path'])
                for env in envs:
                    expected = new_path(item['path'], env)
                    self.assertIn(expected, paths, f'{name} missing {expected}')
                    old_caps = item['capabilities']
                    if item['path'].startswith('kv/metadata/'):
                        want = metadata_capabilities(old_caps)
                    else:
                        want = data_capabilities(mode, old_caps)
                    self.assertIn((expected, tuple(want)), entries, f'{name} {expected} caps {want}')
        self.assertGreaterEqual(len(seen), 12)
        self.assertIn('github-actions-platform-ops-toolkit-tls-rotation', seen)
        self.assertIn('github-actions-platform-ops-toolkit-dev', seen)
        self.assertIn('github-actions-platform-ops-toolkit-uat', seen)

    def test_tls_rotation_writes_both_new_env_wildcards(self):
        doc = yaml.safe_load((POLICIES / 'github-actions-platform-ops-toolkit-tls-rotation.yaml').read_text())
        entries = {item['path']: item['capabilities'] for item in doc['spec']['paths']}
        old = ['create', 'read', 'update', 'list']
        meta = ['list', 'read']
        self.assertEqual(entries['kv/data/CICD/domains/*'], old)
        self.assertEqual(entries['kv/metadata/CICD/domains/*'], meta)
        for env in PLATFORM_ENVS:
            self.assertEqual(entries[f'kv/data/{env}/platform/domains/*'], old)
            self.assertEqual(entries[f'kv/metadata/{env}/platform/domains/*'], meta)

    def test_dev_and_uat_toolkit_map_to_sit_only(self):
        for name in (
            'github-actions-platform-ops-toolkit-dev',
            'github-actions-platform-ops-toolkit-uat',
            'github-actions-platform-ops-toolkit-uat-xconnect-cloud-lab',
            'github-actions-platform-ops-toolkit-uat-xconnect-existing-one',
        ):
            envs, mode = policy_envs_and_mode(name)
            self.assertEqual((envs, mode), (('sit',), 'read'))
            doc = yaml.safe_load((POLICIES / f'{name}.yaml').read_text())
            paths = [item['path'] for item in doc['spec']['paths']]
            self.assertTrue(any(p.startswith('kv/data/sit/platform/domains/') for p in paths))
            self.assertFalse(any(p.startswith('kv/data/prod/platform/domains/') for p in paths))
            self.assertFalse(any(p.startswith('kv/data/dev/platform/domains/') for p in paths))
            self.assertFalse(any(p.startswith('kv/data/uat/platform/domains/') for p in paths))

    def test_denied_probe_is_not_treated_as_a_domain_and_allowed_path_is_singular(self):
        identity = yaml.safe_load(
            (ROOT / 'operations/workload-identities/prod-k3s-v6/vault-tls-reader.yaml').read_text()
        )['spec']['identity']
        self.assertIsInstance(identity['allowedPath'], str)
        self.assertEqual(identity['allowedPath'], 'kv/data/CICD/domains/svc.plus')
        self.assertEqual(identity['deniedPath'], f'kv/data/CICD/domains/{DENIED_PROBE}')
        for _, doc in self.policies():
            for item in doc['spec']['paths']:
                self.assertNotIn(DENIED_PROBE, item['path'])


if __name__ == '__main__':
    unittest.main()
