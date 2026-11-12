"""Contract for the SIT K3s V6 Contabo candidate Flux root."""
from pathlib import Path
import subprocess
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = 'environments/clusters/sit-k3s-v6/overlays/contabo-vps'
# Reviewed main SHA that already contains the Contabo overlay and identity
# declaration (gitops#890 / #896). The pin commit itself is a child of this SHA.
PINNED_COMMIT = '8fae9c2db8da3ef0994558ad24278912df411738'
FIRST_PHASE_ACTIVE = {'sit-k3s', 'external-secrets', 'cluster-identities-sit'}
FIRST_PHASE_SUSPENDED = {
    'postgresql-sit',
    'observability-sit',
    'vpa-sit',
    'platform-mcp-sit',
    'ingress-sit',
    'web-saas-sit',
    'external-dns-sit',
}


def render():
    result = subprocess.run(
        ['kubectl', 'kustomize', '--load-restrictor', 'LoadRestrictionsNone', OVERLAY],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return list(yaml.safe_load_all(result.stdout))


class ContaboOverlay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs = [doc for doc in render() if doc]

    def test_git_repositories_are_pinned_to_the_reviewed_commit(self):
        repos = [doc for doc in self.docs if doc.get('kind') == 'GitRepository']
        self.assertEqual(len(repos), 9)
        for doc in repos:
            ref = doc['spec']['ref']
            self.assertEqual(ref, {'commit': PINNED_COMMIT}, doc['metadata']['name'])

    def test_old_cluster_root_sources_stay_on_main(self):
        for relative in (
            'environments/clusters/sit-k3s-v6/source.yaml',
            'environments/clusters/sit-k3s-v6/unit-sources.yaml',
        ):
            for doc in yaml.safe_load_all((ROOT / relative).read_text()):
                if doc and doc.get('kind') == 'GitRepository':
                    self.assertEqual(doc['spec']['ref'], {'branch': 'main'}, doc['metadata']['name'])

    def test_first_phase_only_identity_and_eso_are_active(self):
        units = {
            doc['metadata']['name']: doc
            for doc in self.docs
            if doc.get('kind') == 'Kustomization' and doc.get('apiVersion', '').startswith('kustomize.toolkit.fluxcd.io/')
        }
        self.assertEqual(set(units), FIRST_PHASE_ACTIVE | FIRST_PHASE_SUSPENDED)
        for name in FIRST_PHASE_ACTIVE:
            self.assertFalse(units[name]['spec']['suspend'], name)
        for name in FIRST_PHASE_SUSPENDED:
            self.assertTrue(units[name]['spec']['suspend'], name)
        self.assertEqual(
            units['sit-k3s']['spec']['path'],
            './environments/clusters/sit-k3s-v6/overlays/contabo-vps',
        )


if __name__ == '__main__':
    unittest.main()
