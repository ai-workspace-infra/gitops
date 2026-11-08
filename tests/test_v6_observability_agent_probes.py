"""Keep both clusters' release probes and remote writer in the agent HelmRelease."""
from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]


class V6ObservabilityAgentProbes(unittest.TestCase):
    def test_blackbox_and_vmagent_are_agent_release_components_in_both_clusters(self):
        for cluster, path, namespace, expected_environment in (
            ('sit', 'services/sit-k3s-v6/observability-sit/agent-release.yaml', 'observability-sit', 'sit'),
            ('prod', 'services/prod-k3s-v6/observability-prod/agent-release.yaml', 'observability-prod', 'prod'),
        ):
            docs = list(yaml.safe_load_all((ROOT / path).read_text()))
            source, release = docs
            self.assertRegex(source['spec']['ref']['digest'], r'^sha256:[a-f0-9]{64}$')
            self.assertEqual(release['spec']['targetNamespace'], namespace)
            values = release['spec']['values']
            self.assertTrue(values['blackboxExporter']['enabled'])
            self.assertTrue(values['vmagent']['enabled'])
            self.assertEqual(values['vmagent']['externalLabels']['environment'], expected_environment)
            scrape = next(job for job in values['vmagent']['scrapeConfigs'] if job['job_name'] == 'progressive-release-probes')
            self.assertEqual(sum(len(group['targets']) for group in scrape['static_configs']), 10)
            self.assertEqual(scrape['relabel_configs'][-1]['replacement'], f'observability-agent-blackbox.{namespace}.svc:9115')
            self.assertEqual(values['vmagent']['remoteWrite']['url'], 'https://observability.svc.plus/ingest/metrics/api/v1/write')
            self.assertEqual(values['vmagent']['remoteWrite']['usernameKey'], 'username')
            self.assertEqual(values['vmagent']['remoteWrite']['passwordKey'], 'password')

    def test_probe_jobs_are_removed_from_the_server_release(self):
        for path in ('services/sit-k3s-v6/observability-sit/helmrelease.yaml', 'services/prod-k3s-v6/observability-prod/helmrelease.yaml'):
            release = yaml.safe_load((ROOT / path).read_text())
            values = release['spec']['values']
            self.assertFalse(values['blackboxExporter']['enabled'])
            jobs = values['telemetry'].get('extraScrapeConfigs', [])
            self.assertNotIn('progressive-release-probes', {job['job_name'] for job in jobs})

    def test_shared_query_routes_and_flagger_use_authenticated_vmauth(self):
        for path, service_namespace in (
            ('services/sit-k3s-v6/ingress-sit/shared-observability-routes.yaml', 'observability-sit'),
            ('services/prod-k3s-v6/ingress-prod/observability-ingest-route.yaml', 'observability-prod'),
        ):
            docs = [doc for doc in yaml.safe_load_all((ROOT / path).read_text()) if doc]
            route = next(doc for doc in docs if doc.get('kind') == 'IngressRoute' and doc['metadata']['name'].endswith('observability-query'))
            backend = route['spec']['routes'][0]['services'][0]
            self.assertEqual(backend['name'], 'observability-ingest-auth')
            self.assertEqual(backend['namespace'], service_namespace)
            self.assertEqual(backend['port'], 8427)
        template = next(yaml.safe_load_all((ROOT / 'services/prod-k3s-v6/web-saas-prod/canary-accounts.yaml').read_text()))
        provider = template['spec']['provider']
        self.assertEqual(provider['address'], 'https://observability.svc.plus')
        self.assertFalse(provider['insecureSkipVerify'])
        self.assertEqual(provider['secretRef']['name'], 'observability-query-auth')

    def test_credentials_are_external_and_vault_access_is_read_only(self):
        docs = [doc for doc in yaml.safe_load_all((ROOT / 'services/sit-k3s-v6/observability-sit/observability-ingest-auth.yaml').read_text()) if doc]
        external = next(doc for doc in docs if doc.get('kind') == 'ExternalSecret')
        self.assertEqual(set(external['spec']['target']['template']['data']), {'username', 'password', 'auth.yaml'})
        self.assertEqual({(item['remoteRef']['key'], item['remoteRef']['property']) for item in external['spec']['data']}, {('CICD/observability', 'user'), ('CICD/observability', 'password')})
        policy = yaml.safe_load((ROOT / 'security/vault/policies/observability-ingest-reader.yaml').read_text())
        secret_policy = next(item for item in policy['spec']['paths'] if item['path'].startswith('kv/'))
        self.assertEqual(secret_policy['capabilities'], ['read'])
        for path in ('services/sit-k3s-v6/ingress-sit/shared-observability-vault-tls.yaml', 'services/prod-k3s-v6/observability-prod/observability-remote-write-secret.yaml', 'services/prod-k3s-v6/web-saas-prod/observability-query-auth.yaml'):
            text = (ROOT / path).read_text()
            self.assertNotIn('token: ', text)
            self.assertNotIn('sit-ingest-password', text)


if __name__ == '__main__':
    unittest.main()
