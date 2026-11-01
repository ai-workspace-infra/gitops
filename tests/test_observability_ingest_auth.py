"""Guard the public metrics write route and its scoped Vault contract."""
from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'services/distributed-web-saas-fullstack/prod'


class IngestAuthContract(unittest.TestCase):
    def setUp(self):
        self.objects = list(yaml.safe_load_all((BASE / 'observability-ingest-auth.yaml').read_text()))
        self.by_kind = {(o['kind'], o['metadata']['name']): o for o in self.objects}

    def test_caddy_routes_only_metrics_write_through_authenticated_service(self):
        release = yaml.safe_load((BASE / 'helmrelease.yaml').read_text())
        patches = release['spec']['postRenderers'][0]['kustomize']['patches']
        config = yaml.safe_load(patches[0]['patch'])['data']['Caddyfile']
        site = config.split('https://observability.svc.plus:8443 {', 1)[1]
        self.assertIn('@metrics_write path /ingest/metrics/api/v1/write', site)
        self.assertIn('uri strip_prefix /ingest/metrics', site)
        self.assertIn('reverse_proxy observability-ingest-auth.web-saas-k3s-v5.svc.cluster.local:8427', site)
        self.assertIn('reverse_proxy http://platform-observability-observability-stack.platform-observability.svc.cluster.local:3000', site)
        deployment_patch = yaml.safe_load(patches[1]['patch'])
        self.assertIn('checksum/observability-ingest', deployment_patch['spec']['template']['metadata']['annotations'])

    def test_auth_proxy_and_vault_are_scoped(self):
        external = self.by_kind[('ExternalSecret', 'observability-ingest-auth')]
        auth = external['spec']['target']['template']['data']['auth.yaml']
        self.assertIn('src_paths: ["/api/v1/write"]', auth)
        self.assertNotIn('unauthorized_user', auth)
        self.assertEqual({(x['remoteRef']['key'], x['remoteRef']['property']) for x in external['spec']['data']},
                         {('CICD/observability', 'user'), ('CICD/observability', 'password')})
        policy = yaml.safe_load((ROOT / 'security/vault/policies/observability-ingest-reader.yaml').read_text())
        kv_paths = [x for x in policy['spec']['paths'] if x['path'].startswith('kv/')]
        self.assertEqual(kv_paths, [{'path': 'kv/data/CICD/observability', 'capabilities': ['read']}])
        role = yaml.safe_load((ROOT / 'security/vault/workload-identities/observability-ingest-reader.yaml').read_text())
        self.assertEqual(role['spec']['token_policies'], ['observability-ingest-reader'])
        self.assertTrue(role['spec']['token_no_default_policy'])
        network = self.by_kind[('NetworkPolicy', 'observability-ingest-auth')]
        self.assertEqual(network['spec']['ingress'][0]['from'][0]['podSelector']['matchLabels']['app.kubernetes.io/component'], 'caddy')


if __name__ == '__main__':
    unittest.main()
