"""Declaration-only regression for the pinned controller's env-file loader."""
from pathlib import Path
import unittest
import yaml

ROOT=Path(__file__).resolve().parents[1]


class Loader(yaml.SafeLoader):
    pass


Loader.add_constructor('!override',lambda loader,node:loader.construct_sequence(node))


class WebSaaSBusinessEnvTests(unittest.TestCase):
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
