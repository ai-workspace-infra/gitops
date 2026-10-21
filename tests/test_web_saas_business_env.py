"""Declaration-only regression for the pinned controller's env-file loader."""
from pathlib import Path
import unittest
import yaml

ROOT=Path(__file__).resolve().parents[1]


class Loader(yaml.SafeLoader):
    pass


Loader.add_constructor('!override',lambda loader,node:loader.construct_sequence(node))


class WebSaaSBusinessEnvTests(unittest.TestCase):
    def test_v4_primary_uses_selfhost_content_and_keeps_recovery_isolated(self):
        profile=yaml.safe_load((ROOT/'.doco-cd.prod-v4-primary.yml').read_text())
        content_file='docker-compose.generation-content.yml'
        self.assertIn(content_file,profile['compose_files'])
        self.assertNotIn(content_file,yaml.safe_load((ROOT/'.doco-cd.prod-v4.yml').read_text())['compose_files'])
        self.assertNotIn(content_file,yaml.safe_load((ROOT/'.doco-cd.prod-v4-stripe-sandbox.yml').read_text())['compose_files'])

        env=dict(line.split('=',1) for line in (ROOT/'compose/web-saas/.env.prod-v4').read_text().splitlines() if '=' in line)
        self.assertEqual(env['CONTENT_IMAGE'], 'ghcr.io/ai-workspace-services/docs:daily-build-2026.10.17-r2@sha256:42079743e3b6cd8297142cff84af85668342aa638aed30fef7090beeecff21ed')
        self.assertRegex(env['CONTENT_IMAGE'], r'^ghcr\.io/[^@]+@sha256:[0-9a-f]{64}$')

        overlay=yaml.safe_load((ROOT/'compose/web-saas/docker-compose.generation-content.yml').read_text())
        content=overlay['services']['content']
        self.assertEqual(content['image'], '${CONTENT_IMAGE:?fixed digest required}')
        self.assertEqual(content['env_file'], ['/etc/xcontrol/web-saas-recovery/internal-service.env'])
        self.assertEqual(content['networks'], ['recovery','content_egress'])
        self.assertEqual(overlay['services']['console']['environment']['DOCS_SERVICE_URL'], 'http://content:8084')
        self.assertEqual(overlay['services']['console']['environment']['RUNTIME_DOCS_SERVICE_URL'], 'http://content:8084')
        self.assertEqual(overlay['services']['console']['depends_on']['content']['condition'], 'service_healthy')
        self.assertTrue(yaml.safe_load((ROOT/'compose/web-saas/docker-compose.recovery-storage.yml').read_text())['networks']['recovery']['internal'])
        self.assertNotIn('internal', overlay['networks']['content_egress'])

    def test_sandbox_payment_profile_limits_egress_to_accounts(self):
        profile=yaml.safe_load((ROOT/'.doco-cd.prod-v4-stripe-sandbox.yml').read_text())
        self.assertEqual(profile['compose_files'],[
            'docker-compose.recovery-storage.yml','docker-compose.generation-app.yml',
            'docker-compose.sandbox-payment-egress.yml'])
        overlay=yaml.safe_load((ROOT/'compose/web-saas/docker-compose.sandbox-payment-egress.yml').read_text())
        self.assertEqual(overlay['services'],{
            'accounts':{'networks':['recovery','sandbox_payment_egress']}})
        self.assertFalse(overlay['networks']['sandbox_payment_egress']['internal'])
        storage=yaml.safe_load((ROOT/'compose/web-saas/docker-compose.recovery-storage.yml').read_text())
        self.assertTrue(storage['networks']['recovery']['internal'])
        for filename in ('.doco-cd.prod-v4.yml','.doco-cd.prod-v4-primary.yml'):
            existing=yaml.safe_load((ROOT/filename).read_text())
            self.assertNotIn('docker-compose.sandbox-payment-egress.yml',existing['compose_files'])

    def test_pinned_controller_never_receives_raw_env_format(self):
        for name in ('generation-app','generation-primary','recovery-app','stripe-sandbox'):
            data=yaml.load((ROOT/f'compose/web-saas/docker-compose.{name}.yml').read_text(),Loader=Loader)
            for service in data['services'].values():
                for value in service.get('env_file',[]):
                    self.assertIsInstance(value,str, name)
                    self.assertNotIn('generation-app.env',value)
                    self.assertNotIn('generation-auth.env',value)
        for name in ('generation-app','recovery-app'):
            data=yaml.load((ROOT/f'compose/web-saas/docker-compose.{name}.yml').read_text(),Loader=Loader)
            for service in ('accounts','billing'):
                self.assertTrue(data['services'][service]['env_file'][-1].endswith('/business-database.env'))

    def test_contract_contains_only_existing_identity_and_secret_references(self):
        c=yaml.safe_load((ROOT/'compose/web-saas/runtime/prod.yaml').read_text())['business_database']
        self.assertEqual(c['role'],'account_user')
        self.assertEqual(c['credential'],dict(vault_path='kv/prod/databases',key='account_pg_password'))
        self.assertNotIn('password',c)
        self.assertNotIn('dsn',c)


if __name__=='__main__':unittest.main()
