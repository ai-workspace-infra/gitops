"""Protect the web-saas feature paths from unrelated shared MCP dependencies."""
import os
from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CLUSTER = ROOT / 'environments/clusters/dev-k3s-v5'
LANES = Path(os.environ.get('FEATURE_LANES_ROOT', ROOT / 'services/distributed-web-saas-fullstack/dev/feature-lanes'))


def load(path):
    return yaml.safe_load(path.read_text())


class FeatureSitPathIsolation(unittest.TestCase):
    def test_independent_ingress_and_mcp_paths(self):
        ingress = load(CLUSTER / 'platform-ingress-kustomization.yaml')['spec']
        mcp = load(CLUSTER / 'platform-mcp-kustomization.yaml')['spec']
        self.assertEqual(ingress['path'], './services/platform-ingress/dev')
        self.assertEqual(mcp['path'], './services/platform-mcp/dev-k3s-v5')
        self.assertNotEqual(ingress['path'], mcp['path'])
        self.assertEqual(ingress['sourceRef'], {'kind': 'GitRepository', 'name': 'platform-config-dev'})
        self.assertFalse(ingress.get('dependsOn'), 'ingress cannot depend on shared MCP')

    def test_feature_lane_resources_stay_within_lane(self):
        for path in sorted(LANES.glob('*/kustomization.yaml')):
            with self.subTest(lane=path.parent.name):
                self.check_lane(path)

    def check_lane(self, path):
        lane = path.parent.name
        k = load(path)
        self.assertEqual(k.get('namespace'), 'feature-' + lane + '-sit')
        for value in k.get('resources', []):
            resource = Path(value)
            self.assertFalse(resource.is_absolute() or '..' in resource.parts)
            self.assertNotIn('mcp', value.lower())
            self.assertTrue((path.parent / resource).is_file())
            for doc in yaml.safe_load_all((path.parent / resource).read_text()):
                if not isinstance(doc, dict):
                    continue
                self.assertEqual(doc.get('metadata', {}).get('namespace'), k['namespace'])
                spec = doc.get('spec') or {}
                for dep in spec.get('dependsOn') or []:
                    self.assertNotIn('mcp', str(dep).lower())
                self.assertNotIn('mcp', str(spec.get('sourceRef', {})).lower())

    def test_rejects_cross_path_resource_and_mcp_dependency(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / 'sit-test-1483'
            p.mkdir()
            k = p / 'kustomization.yaml'
            k.write_text('namespace: feature-sit-test-1483-sit\nresources: [../platform-mcp.yaml]\n')
            with self.assertRaises(AssertionError):
                self.check_lane(k)
            k.write_text('namespace: feature-sit-test-1483-sit\nresources: [release.yaml]\n')
            (p / 'release.yaml').write_text('kind: HelmRelease\nmetadata:\n  namespace: feature-sit-test-1483-sit\nspec:\n  dependsOn:\n    - name: platform-mcp\n')
            with self.assertRaises(AssertionError):
                self.check_lane(k)


if __name__ == '__main__':
    unittest.main()
