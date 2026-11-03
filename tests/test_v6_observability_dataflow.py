"""Guard the V6 observability ingest and scraping contracts."""
from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
OBS_PROD = ROOT / 'services/prod-k3s-v6/observability-prod'
INGRESS_PROD = ROOT / 'services/prod-k3s-v6/ingress-prod'
PG_PROD = ROOT / 'services/prod-k3s-v6/postgresql-prod'


class V6ObservabilityDataflowContract(unittest.TestCase):
    def setUp(self):
        self.ingest_objects = list(yaml.safe_load_all((OBS_PROD / 'observability-ingest-auth.yaml').read_text()))
        self.by_kind = {(o['kind'], o['metadata']['name']): o for o in self.ingest_objects}

    def test_caddy_routes_metrics_and_logs_ingest_to_vmauth(self):
        release = yaml.safe_load((INGRESS_PROD / 'helmrelease.yaml').read_text())
        patches = release['spec']['postRenderers'][0]['kustomize']['patches']
        config = yaml.safe_load(patches[0]['patch'])['data']['Caddyfile']
        site = config.split('https://observability.svc.plus:8443 {', 1)[1]
        self.assertIn('@metrics_write path /ingest/metrics/api/v1/write', site)
        self.assertIn('uri strip_prefix /ingest/metrics', site)
        self.assertIn('@logs_write path /ingest/logs/*', site)
        self.assertIn('uri strip_prefix /ingest/logs', site)
        self.assertIn('reverse_proxy http://observability-ingest-auth.observability-prod.svc.cluster.local:8427', site)
        self.assertIn('reverse_proxy http://observability-observability-stack.observability-prod.svc.cluster.local:3000', site)

    def test_vmauth_maps_metrics_and_logs_destinations(self):
        external = self.by_kind[('ExternalSecret', 'observability-ingest-auth')]
        auth = external['spec']['target']['template']['data']['auth.yaml']
        self.assertIn('/api/v1/write', auth)
        self.assertIn(':8428', auth)
        self.assertIn('/insert/jsonline', auth)
        self.assertIn(':9428', auth)
        self.assertEqual({(x['remoteRef']['key'], x['remoteRef']['property']) for x in external['spec']['data']},
                         {('CICD/observability', 'user'), ('CICD/observability', 'password')})

    def test_observability_stack_scrapes_all_workstreams(self):
        release = yaml.safe_load((OBS_PROD / 'helmrelease.yaml').read_text())
        scrapes = release['spec']['values']['telemetry']['extraScrapeConfigs']
        job_names = {s['job_name'] for s in scrapes}
        self.assertIn('node-exporter', job_names)
        self.assertIn('process-exporter', job_names)
        self.assertIn('kube-state-metrics', job_names)
        self.assertIn('postgres-exporter', job_names)
        self.assertIn('cadvisor', job_names)

    def test_postgresql_metrics_enabled_with_auditor_account(self):
        release = yaml.safe_load((PG_PROD / 'helmrelease.yaml').read_text())
        metrics = release['spec']['values']['postgresql']['metrics']
        self.assertTrue(metrics['enabled'])
        env_map = {e['name']: e.get('value') or e.get('valueFrom', {}).get('secretKeyRef', {}).get('name') for e in metrics['env']}
        self.assertEqual(env_map.get('DATA_SOURCE_USER'), 'auditor')
        self.assertEqual(env_map.get('DATA_SOURCE_PASS'), 'postgresql-auditor')


if __name__ == '__main__':
    unittest.main()
