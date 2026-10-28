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

    def test_platform_ingress_caddy_helmrelease_contract(self):
        hr_path = ROOT / 'services/platform-ingress/dev/helmrelease.yaml'
        self.assertTrue(hr_path.exists())
        hr = yaml.safe_load(hr_path.read_text())
        self.assertEqual(hr['metadata']['name'], 'dev-ingress')
        self.assertEqual(hr['metadata']['namespace'], 'platform-ingress')
        chart_spec = hr['spec']['chart']['spec']
        self.assertEqual(chart_spec['chart'], 'caddy-ingress-controller')
        self.assertEqual(chart_spec['sourceRef']['kind'], 'HelmRepository')
        self.assertEqual(chart_spec['sourceRef']['name'], 'caddyserver')

        repo_path = ROOT / 'services/platform-ingress/dev/helmrepository.yaml'
        self.assertTrue(repo_path.exists())
        repo = yaml.safe_load(repo_path.read_text())
        self.assertEqual(repo['spec']['url'], 'https://caddyserver.github.io/ingress/')

        values_path = ROOT / 'services/platform-ingress/dev/values.yaml'
        self.assertTrue(values_path.exists())
        values = yaml.safe_load(values_path.read_text())
        self.assertEqual(values['ingressController']['className'], 'caddy')
        self.assertFalse(values['ingressController']['classNameRequired'])

    def test_traefik_strictly_forbidden_in_dev_ingress_and_mcp(self):
        # Prohibit Traefik Ingress service declarations per organizational policy
        self.assertFalse((ROOT / 'services/platform-ingress/dev/oci-repository.yaml').exists())
        for path in (ROOT / 'services/platform-ingress/dev').glob('*.yaml'):
            content = path.read_text()
            self.assertNotIn('traefik', content.lower(), f"Forbidden Traefik reference found in {path.name}")
        for path in (ROOT / 'services/platform-mcp/dev-k3s-v5').glob('*.yaml'):
            content = path.read_text()
            self.assertNotIn('traefik', content.lower(), f"Forbidden Traefik reference found in {path.name}")

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
        self.assertNotIn('ingress-mcp-observability.yaml', resources)
        self.assertFalse((ROOT / 'services/platform-mcp/dev-k3s-v5/ingress-mcp-observability.yaml').exists())

    def test_single_domain_mcp_server_ingress_contract(self):
        ingress_path = ROOT / 'services/platform-mcp/dev-k3s-v5/ingress-mcp-server.yaml'
        self.assertTrue(ingress_path.exists())
        ingress = yaml.safe_load(ingress_path.read_text())

        # Must use Caddy IngressClass
        self.assertEqual(ingress['spec']['ingressClassName'], 'caddy')

        rules = ingress['spec']['rules']
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]['host'], 'mcp-server.svc.plus')

        paths = rules[0]['http']['paths']
        path_map = {p['path']: p['backend']['service'] for p in paths}
        # Route: /v1/grafana -> mcp-grafana:8000
        self.assertIn('/v1/grafana', path_map)
        self.assertEqual(path_map['/v1/grafana']['name'], 'mcp-grafana')
        self.assertEqual(path_map['/v1/grafana']['port']['number'], 8000)
        # Route: / -> infrastructure-mcp-server:8080
        self.assertIn('/', path_map)
        self.assertEqual(path_map['/']['name'], 'infrastructure-mcp-server')
        self.assertEqual(path_map['/']['port']['number'], 8080)

        self.assertEqual(ingress['spec']['tls'][0]['hosts'], ['mcp-server.svc.plus'])

    def test_infrastructure_mcp_configmap_backends_use_single_domain(self):
        cm_path = ROOT / 'services/platform-mcp/dev-k3s-v5/configmap-infrastructure-mcp.yaml'
        self.assertTrue(cm_path.exists())
        cm = yaml.safe_load(cm_path.read_text())
        import json
        config_data = json.loads(cm['data']['config.json'])
        for backend in config_data['backends']:
            self.assertTrue(
                backend['url'].startswith('https://mcp-server.svc.plus/'),
                f"Backend {backend['name']} URL {backend['url']} does not use mcp-server.svc.plus",
            )

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
        self.assertIn('--allowed-hosts', command)
        allowed_hosts_idx = command.index('--allowed-hosts')
        self.assertIn('mcp-server.svc.plus', command[allowed_hosts_idx + 1])
        env_map = {e['name']: e['value'] for e in container['env']}
        self.assertEqual(env_map['GRAFANA_URL'], 'https://observability.svc.plus/grafana/')


if __name__ == '__main__':
    unittest.main()
