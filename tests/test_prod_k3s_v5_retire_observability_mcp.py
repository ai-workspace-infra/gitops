from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]


class ProdK3sV5RetireObservabilityMCPTests(unittest.TestCase):
    def test_prod_observability_kustomization_includes_retire_manifest(self):
        kustom_path = ROOT / 'services/platform-observability/prod/kustomization.yaml'
        self.assertTrue(kustom_path.exists())
        kustom = yaml.safe_load(kustom_path.read_text())
        resources = kustom.get('resources', [])
        self.assertIn('retire-observability-mcp.yaml', resources)

    def test_retire_observability_mcp_manifest_declarations(self):
        retire_path = ROOT / 'services/platform-observability/prod/retire-observability-mcp.yaml'
        self.assertTrue(retire_path.exists())
        docs = list(yaml.safe_load_all(retire_path.read_text()))
        self.assertGreaterEqual(len(docs), 1)

        deploy_map = {doc['metadata']['name']: doc for doc in docs if doc.get('kind') == 'Deployment'}

        # Target pod reported by user: platform-observability-mcp-victoriametrics
        self.assertIn('platform-observability-mcp-victoriametrics', deploy_map)
        vm_deploy = deploy_map['platform-observability-mcp-victoriametrics']
        self.assertEqual(vm_deploy['spec']['replicas'], 0)
        self.assertEqual(vm_deploy['metadata']['namespace'], 'platform-observability')

        # Other observability-mcp deployments
        for name in [
            'platform-observability-mcp-grafana',
            'platform-observability-mcp-victorialogs',
            'platform-observability-mcp-victoriatraces',
        ]:
            self.assertIn(name, deploy_map)
            self.assertEqual(deploy_map[name]['spec']['replicas'], 0)
            self.assertEqual(deploy_map[name]['metadata']['namespace'], 'platform-observability')

    def test_prod_values_mcp_disabled(self):
        values_path = ROOT / 'services/platform-observability/prod/values.yaml'
        self.assertTrue(values_path.exists())
        values = yaml.safe_load(values_path.read_text())
        self.assertIn('mcp', values)
        self.assertFalse(values['mcp']['enabled'])
        self.assertEqual(values['mcp']['victoriametrics']['replicaCount'], 0)


if __name__ == '__main__':
    unittest.main()
