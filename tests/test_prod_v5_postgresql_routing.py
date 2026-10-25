from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
TARGET = 'postgresql-k3s-v5.svc.plus'
CNAME_TARGETS = {
    'console.svc.plus': 'console-k3s-v5.svc.plus',
    'accounts.svc.plus': 'accounts-k3s-v5.svc.plus',
    'billing.svc.plus': 'billing-k3s-v5.svc.plus',
    'vault.svc.plus': 'vault-k3s-v5.svc.plus',
    'observability.svc.plus': 'observability-k3s-v5.svc.plus',
    'postgresql.svc.plus': TARGET,
}


class ProdV5PostgresqlRoutingTests(unittest.TestCase):
    def test_prod_selfhost_canonical_cname_targets_v5(self):
        config = yaml.safe_load((ROOT / 'topology/prod/selfhost/runtime-topology.yaml').read_text())
        dns = config['spec']['runtime']['routing']['dns']
        self.assertEqual(dns['canonical_records'], CNAME_TARGETS)
        for name, target in CNAME_TARGETS.items():
            self.assertEqual(config['spec']['domains'][name]['selfhost'], target)
        self.assertEqual(dns['canonical_records']['postgresql.svc.plus'], TARGET)
        self.assertEqual(config['spec']['domains']['postgresql.svc.plus']['selfhost'], TARGET)
        self.assertEqual(config['spec']['public_endpoints']['postgresql']['host'], TARGET)

    def test_prod_hybrid_endpoint_does_not_fall_back_to_generic_generation(self):
        config = yaml.safe_load((ROOT / 'topology/prod/hybrid/runtime-topology.yaml').read_text())
        self.assertEqual(config['spec']['public_endpoints']['postgresql']['host'], TARGET)
        self.assertEqual(config['spec']['public_endpoints']['accounts']['host'], 'accounts-k3s-v5.svc.plus')
        self.assertEqual(config['spec']['public_endpoints']['billing']['host'], 'billing-k3s-v5.svc.plus')

    def test_retired_prod_candidate_has_no_business_domain_or_deploy_binding(self):
        config = yaml.safe_load((ROOT / 'resources/svc.plus/prod/akamai/web-saas-prod-v5.yaml').read_text())
        host_record = config['hosts'][0]
        host = host_record['host_vars']
        self.assertNotIn('service_domains', host)
        self.assertNotIn('web_saas_doco_cd_target', host)
        self.assertNotIn('web_saas', host_record['groups'])
        self.assertNotIn('generation_candidate', host_record['groups'])
        dev = yaml.safe_load((ROOT / 'topology/dev/k3s-v5/existing-host.yaml').read_text())
        self.assertEqual(dev['metadata']['environment'], 'dev')
        self.assertEqual(dev['spec']['inventory_host'], 'dev-k3s-v5.svc.plus')
        self.assertEqual(dev['spec']['service_domains'], ['dev-k3s-v5.svc.plus'])
        cluster = yaml.safe_load((ROOT / 'environments/clusters/dev-k3s-v5/namespaces.yaml').read_text())
        self.assertEqual(cluster['metadata']['name'], 'feature-xconnect-referral')

    def test_active_prod_topologies_have_no_generic_selfhost_generation_target(self):
        root = ROOT / 'topology/prod'
        forbidden = ('console-selfhost-prod.svc.plus', 'accounts-selfhost-prod.svc.plus',
                     'billing-selfhost-prod.svc.plus', 'postgresql-selfhost-prod.svc.plus',
                     'console-selfhost-prod-v5.svc.plus', 'accounts-selfhost-prod-v5.svc.plus',
                     'billing-selfhost-prod-v5.svc.plus', 'postgresql-selfhost-prod-v5.svc.plus')
        for path in root.rglob('*.yaml'):
            content = path.read_text()
            for value in forbidden:
                self.assertNotIn(value, content, f'{path.relative_to(ROOT)} retains {value}')


if __name__ == '__main__':
    unittest.main()
