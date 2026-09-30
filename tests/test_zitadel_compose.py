"""Validate non-sensitive single-host application intent, without cloud writes."""
from pathlib import Path
import re
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]


class ZitadelComposeContract(unittest.TestCase):
    def test_dedicated_doco_target_and_pinned_images(self):
        config = yaml.safe_load((ROOT / '.doco-cd.zitadel.yaml').read_text())
        self.assertEqual(config['name'], 'shared-zitadel')
        self.assertEqual(config['working_dir'], 'compose/zitadel')
        self.assertEqual(config['env_files'], ['.env.shared'])
        lines = (ROOT / 'compose/zitadel/.env.shared').read_text().splitlines()
        images = [line for line in lines if line and not line.startswith('#')]
        self.assertEqual(len(images), 3)
        for line in images:
            self.assertRegex(line, r'^[A-Z_]+_IMAGE=ghcr[.]io/[^@]+@sha256:[0-9a-f]{64}$')

    def test_host_secret_contract_and_health(self):
        services = yaml.safe_load((ROOT / 'compose/zitadel/docker-compose.yml').read_text())['services']
        self.assertEqual(set(services), {'zitadel', 'login'})
        self.assertEqual(services['zitadel']['command'][0], 'start-from-init')
        self.assertIn('--masterkeyFile', services['zitadel']['command'])
        self.assertEqual(services['login']['depends_on']['zitadel']['condition'], 'service_healthy')
        self.assertEqual(services['login']['env_file'],
                         [{'path': '/etc/xcontrol/zitadel/login.env'}])
        # Doco-CD's compose-go rejects any env_file format other than dotenv.
        for service in services.values():
            for entry in service.get('env_file', []):
                self.assertNotIn('format', entry if isinstance(entry, dict) else {})
        # The ready probe must read the same config file (TLS disabled) as
        # start-from-init; without it ZITADEL's default TLS.Enabled=true makes
        # the probe use https against a plain-HTTP server, forever unhealthy.
        command = services['zitadel']['command']
        config_file = command[command.index('--config') + 1]
        self.assertEqual(services['zitadel']['healthcheck']['test'],
                         ['CMD', '/app/zitadel', 'ready', '--config', config_file])
        self.assertIn(f'/etc/xcontrol/zitadel/config.yaml:{config_file}:ro', services['zitadel']['volumes'])
        # A restart during first-instance setup loses the Login client PAT.
        self.assertGreaterEqual(int(services['zitadel']['healthcheck']['start_period'].rstrip('s')), 300)
        for service in services.values():
            self.assertIn('healthcheck', service)
            self.assertTrue(all(port.startswith('127.0.0.1:') for port in service['ports']))
            self.assertTrue(all(mount.startswith(('/etc/xcontrol/zitadel/', '/opt/zitadel:')) for mount in service['volumes']))


if __name__ == '__main__':
    unittest.main()
