"""Contract tests for full-product-matrix dual-mirror GitOps declaration and Vault IaC auth."""
from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]


class ClientMirrorsIacGitOpsContract(unittest.TestCase):
    def test_client_mirrors_declaration_is_valid_and_secret_free(self):
        manifest_path = ROOT / "resources/svc.plus/prod/client-mirrors/mirrors.yaml"
        raw = manifest_path.read_text(encoding="utf-8")
        doc = yaml.safe_load(raw)

        self.assertEqual(doc["apiVersion"], "gitops.svc.plus/v1alpha1")
        self.assertEqual(doc["kind"], "ClientMirrorStack")
        self.assertEqual(doc["metadata"]["project"], "svc.plus")
        self.assertEqual(doc["metadata"]["environment"], "prod")

        spec = doc["spec"]
        self.assertEqual(spec["global"]["zone_name"], "svc.plus")
        self.assertEqual(spec["global"]["managed_by"], "terraform-client-mirrors")
        self.assertEqual(spec["global"]["saas_role"], "playbooks/roles/saas/client_mirrors")
        self.assertEqual(spec["admin_vault_sources"]["cloudflare"], "kv/prod/serverless/cloudflare")
        self.assertEqual(spec["admin_vault_sources"]["alicloud"], "kv/prod/platform/alicloud")
        self.assertEqual(spec["admin_vault_sources"]["iac_state"], "kv/CICD/prod/iac_state")
        slugs = [p["slug"] for p in spec["products"]]
        self.assertIn("xconnect", slugs)
        self.assertIn("xworkmate", slugs)

        r2 = spec["cloudflare_r2"]
        self.assertEqual(r2["custom_domain"], "dl.svc.plus")
        self.assertEqual(r2["location"], "apac")
        self.assertEqual(r2["vault_kv_path"], "prod/platform/storage/cloudflare-r2")
        self.assertIn("https://console.svc.plus", r2["cors_allowed_origins"])

        ali = spec["aliyun_oss_cdn"]
        self.assertEqual(ali["oss_region"], "cn-hongkong")
        self.assertEqual(ali["oss_acl"], "public-read")
        self.assertEqual(ali["cdn_domain"], "cn-dl.svc.plus")
        self.assertEqual(ali["cdn_type"], "download")
        self.assertEqual(ali["cdn_scope"], "overseas")
        self.assertEqual(ali["vault_kv_path"], "prod/platform/storage/aliyun-oss")

        lowered = raw.lower()
        for forbidden in ("api_token:", "access_key_id:", "access_key_secret:", "secret_access_key:"):
            self.assertNotIn(forbidden, lowered)

    def test_client_mirrors_vault_policy_and_role_contracts(self):
        cases = (
            ("github-actions-iac-client-mirrors-prod", "ai-workspace-infra/iac_modules", True),
            ("github-actions-playbooks-client-mirrors-prod", "ai-workspace-infra/playbooks", False),
        )
        for name, repo, needs_iac_state in cases:
            policy = yaml.safe_load((ROOT / f"security/vault/policies/{name}.yaml").read_text(encoding="utf-8"))
            role = yaml.safe_load((ROOT / f"security/vault/roles/{name}.yaml").read_text(encoding="utf-8"))

            self.assertEqual(policy["apiVersion"], "security.gitops/v1alpha1")
            self.assertEqual(policy["kind"], "VaultACLPolicy")
            self.assertEqual(policy["metadata"]["name"], name)

            paths = {entry["path"]: set(entry["capabilities"]) for entry in policy["spec"]["paths"]}
            self.assertEqual(paths["kv/data/prod/serverless/cloudflare"], {"read"})
            self.assertEqual(paths["kv/data/prod/platform/alicloud"], {"read"})
            if needs_iac_state:
                self.assertEqual(paths["kv/data/CICD/prod/iac_state"], {"read"})
            self.assertEqual(paths["kv/data/prod/platform/storage/cloudflare-r2"], {"create", "update", "read"})
            self.assertEqual(paths["kv/data/prod/platform/storage/aliyun-oss"], {"create", "update", "read"})
            for path in paths:
                self.assertRegex(path, r"^kv/(data|metadata)/(CICD/)?prod/")

            self.assertEqual(role["kind"], "VaultJWTAuthRole")
            self.assertEqual(role["metadata"]["name"], name)
            self.assertEqual(role["spec"]["bound_claims"]["repository"], repo)
            self.assertEqual(role["spec"]["bound_claims"]["environment"], "prod")
            self.assertEqual(role["spec"]["bound_claims"]["ref"], ["refs/heads/main"])
            self.assertEqual(role["spec"]["token_policies"], [name])
            self.assertTrue(role["spec"]["token_no_default_policy"])


if __name__ == "__main__":
    unittest.main()
