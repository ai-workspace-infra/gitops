from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]


class DevK3sV5MCPGatewayTests(unittest.TestCase):
    def test_dev_cluster_kustomization_wiring(self):
        kustom_path = ROOT / 'environments/clusters/dev-k3s-v5/kustomization.yaml'
        self.assertTrue(kustom_path.exists())
        kustom = yaml.safe_load(kustom_path.read_text())
        resources = kustom.get('resources', [])
        self.assertIn('namespaces.yaml', resources)
        self.assertIn('source.yaml', resources)
        self.assertIn('platform-ingress-kustomization.yaml', resources)
        self.assertIn('platform-mcp-kustomization.yaml', resources)

    def test_ingress_controller_namespaces_include_platform_mcp(self):
        values_path = ROOT / 'services/platform-ingress/dev/values.yaml'
        self.assertTrue(values_path.exists())
        values = yaml.safe_load(values_path.read_text())
        watched_namespaces = values['providers']['kubernetesIngress']['namespaces']
        self.assertIn('platform-mcp', watched_namespaces)
        self.assertEqual(values['providers']['kubernetesIngress']['ingressClass'], 'dev-web-saas')

    def test_platform_mcp_kustomization_resources(self):
        mcp_kustom_path = ROOT / 'services/platform-mcp/dev-k3s-v5/kustomization.yaml'
        self.assertTrue(mcp_kustom_path.exists())
        mcp_kustom = yaml.safe_load(mcp_kustom_path.read_text())
        resources = mcp_kustom.get('resources', [])
        self.assertIn('namespace.yaml', resources)
        self.assertIn('configmap-infrastructure-mcp.yaml', resources)
        self.assertIn('deployment-infrastructure-mcp.yaml', resources)
        self.assertIn('service-infrastructure-mcp.yaml', resources)
        self.assertIn('ingress-mcp-server.yaml', resources)
        self.assertIn('deployment-observability-mcp.yaml', resources)
        self.assertIn('service-observability-mcp.yaml', resources)
        self.assertIn('ingress-mcp-observability.yaml', resources)

    def test_infrastructure_mcp_ingress_contract(self):
        ingress_path = ROOT / 'services/platform-mcp/dev-k3s-v5/ingress-mcp-server.yaml'
        self.assertTrue(ingress_path.exists())
        ingress = yaml.safe_load(ingress_path.read_text())
        annotations = ingress['metadata']['annotations']
        self.assertEqual(annotations.get('kubernetes.io/ingress.class'), 'dev-web-saas')
        self.assertEqual(annotations.get('traefik.ingress.kubernetes.io/router.tls.certresolver'), 'dev-http01')

        rules = ingress['spec']['rules']
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]['host'], 'mcp-server.svc.plus')
        self.assertEqual(rules[0]['http']['paths'][0]['backend']['service']['name'], 'infrastructure-mcp-server')
        self.assertEqual(rules[0]['http']['paths'][0]['backend']['service']['port']['number'], 8080)
        self.assertEqual(ingress['spec']['tls'][0]['hosts'], ['mcp-server.svc.plus'])

    def test_observability_mcp_ingress_contract(self):
        ingress_path = ROOT / 'services/platform-mcp/dev-k3s-v5/ingress-mcp-observability.yaml'
        self.assertTrue(ingress_path.exists())
        ingress = yaml.safe_load(ingress_path.read_text())
        annotations = ingress['metadata']['annotations']
        self.assertEqual(annotations.get('kubernetes.io/ingress.class'), 'dev-web-saas')
        self.assertEqual(annotations.get('traefik.ingress.kubernetes.io/router.tls.certresolver'), 'dev-http01')

        rules = ingress['spec']['rules']
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]['host'], 'mcp.svc.plus')
        paths = rules[0]['http']['paths']
        path_map = {p['path']: p['backend']['service'] for p in paths}
        self.assertIn('/v1/grafana', path_map)
        self.assertEqual(path_map['/v1/grafana']['name'], 'mcp-grafana')
        self.assertEqual(path_map['/v1/grafana']['port']['number'], 8000)
        self.assertEqual(ingress['spec']['tls'][0]['hosts'], ['mcp.svc.plus'])

    def test_observability_mcp_readonly_guardrails(self):
        deploy_path = ROOT / 'services/platform-mcp/dev-k3s-v5/deployment-observability-mcp.yaml'
        self.assertTrue(deploy_path.exists())
        deploy = yaml.safe_load(deploy_path.read_text())
        container = deploy['spec']['template']['spec']['containers'][0]
        self.assertEqual(container['name'], 'mcp-grafana')
        command = container['command']
        self.assertIn('-t', command)
        self.assertIn('sse', command)
        self.assertIn('--base-path', command)
        self.assertIn('/v1/grafana', command)
        self.assertIn('--disable-write', command)
        self.assertIn('--disable-admin', command)
        env_map = {e['name']: e['value'] for e in container['env']}
        self.assertEqual(env_map['GRAFANA_URL'], 'https://observability.svc.plus/grafana/')


if __name__ == '__main__':
    unittest.main()
