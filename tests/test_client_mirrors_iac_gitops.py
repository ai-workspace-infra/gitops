"""Contract tests for full-product-matrix dual-mirror GitOps declaration and Vault IaC auth."""
import json
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
            self.assertEqual(paths["kv/data/prod/platform/storage/cloudflare-r2-repo"], {"create", "update", "read"})
            self.assertEqual(paths["kv/data/prod/platform/storage/aliyun-oss-repo"], {"create", "update", "read"})
            for path in paths:
                self.assertRegex(path, r"^kv/(data|metadata)/(CICD/)?prod/")

            self.assertEqual(role["kind"], "VaultJWTAuthRole")
            self.assertEqual(role["metadata"]["name"], name)
            self.assertEqual(role["spec"]["bound_claims"]["repository"], repo)
            self.assertEqual(role["spec"]["bound_claims"]["environment"], "prod")
            self.assertEqual(role["spec"]["bound_claims"]["ref"], ["refs/heads/main"])
            self.assertEqual(role["spec"]["token_policies"], [name])
            self.assertTrue(role["spec"]["token_no_default_policy"])

    def test_client_repos_declaration_is_valid_and_secret_free(self):
        manifest_path = ROOT / "resources/svc.plus/prod/client-mirrors/repos.yaml"
        raw = manifest_path.read_text(encoding="utf-8")
        doc = yaml.safe_load(raw)

        self.assertEqual(doc["apiVersion"], "gitops.svc.plus/v1alpha1")
        self.assertEqual(doc["kind"], "ClientMirrorStack")
        self.assertEqual(doc["metadata"]["name"], "svc-plus-client-repos")
        self.assertEqual(doc["metadata"]["project"], "svc.plus")
        self.assertEqual(doc["metadata"]["environment"], "prod")

        spec = doc["spec"]
        self.assertEqual(spec["global"]["zone_name"], "svc.plus")
        self.assertEqual(spec["global"]["probe_path"], "repo/_health/probe.json")
        self.assertEqual(spec["global"]["managed_by"], "terraform-client-mirrors")
        self.assertEqual(spec["global"]["saas_role"], "playbooks/roles/saas/client_mirrors")
        self.assertEqual(spec["global"]["state"]["namespace"], "repos")

        expected_prefixes = ["apt/", "rpm/", "homebrew/", "scoop/", "winget/"]
        products_by_slug = {p["slug"]: p["prefixes"] for p in spec["products"]}
        self.assertEqual(products_by_slug["xconnect"], expected_prefixes)
        self.assertEqual(products_by_slug["xworkmate"], expected_prefixes)

        r2 = spec["cloudflare_r2"]
        self.assertEqual(r2["id"], "global_repo_r2")
        self.assertEqual(r2["bucket_name"], "svc-plus-repo-global")
        self.assertEqual(r2["custom_domain"], "repo.svc.plus")
        self.assertEqual(r2["vault_kv_path"], "prod/platform/storage/cloudflare-r2-repo")

        ali = spec["aliyun_oss_cdn"]
        self.assertEqual(ali["id"], "cn_repo_oss_cdn")
        self.assertEqual(ali["bucket_name"], "svc-plus-repo-cn-hk")
        self.assertEqual(ali["cdn_domain"], "cn-repo.svc.plus")
        self.assertEqual(ali["cdn_type"], "web")
        self.assertEqual(ali["cdn_scope"], "overseas")
        self.assertEqual(ali["cdn_tls_vault_path"], "kv/CICD/domains/svc.plus")
        self.assertEqual(ali["vault_kv_path"], "prod/platform/storage/aliyun-oss-repo")
        self.assertIn("apt/*", ali["oss_policy_prefixes"])
        self.assertIn("repo/*", ali["oss_policy_prefixes"])
        self.assertIn("repo-index.json", ali["oss_policy_prefixes"])

        lowered = raw.lower()
        for forbidden in ("api_token:", "access_key_id:", "access_key_secret:", "secret_access_key:"):
            self.assertNotIn(forbidden, lowered)

    def test_distribution_and_xworkmate_app_vault_policies_and_roles(self):
        dist_pol = yaml.safe_load((ROOT / "security/vault/policies/github-actions-distribution-prod.yaml").read_text(encoding="utf-8"))
        dist_role = yaml.safe_load((ROOT / "security/vault/roles/github-actions-distribution-prod.yaml").read_text(encoding="utf-8"))
        dist_paths = {entry["path"]: set(entry["capabilities"]) for entry in dist_pol["spec"]["paths"]}
        for suffix in (
            "storage/cloudflare-r2-repo",
            "storage/aliyun-oss-repo",
            "storage/cloudflare-r2",
            "storage/aliyun-oss",
            "signing/svc-plus-repo-gpg",
            "distribution/github-pat",
        ):
            self.assertEqual(dist_paths[f"kv/data/prod/platform/{suffix}"], {"read"})
            self.assertEqual(dist_paths[f"kv/metadata/prod/platform/{suffix}"], {"list", "read"})
        for path in dist_paths:
            self.assertRegex(path, r"^kv/(data|metadata)/prod/")
        self.assertEqual(dist_role["spec"]["bound_claims"]["repository"], "ai-workspace-lab/distribution")
        self.assertEqual(dist_role["spec"]["bound_claims"]["environment"], "prod")
        self.assertEqual(dist_role["spec"]["bound_claims"]["ref"], ["refs/heads/main"])
        self.assertEqual(
            dist_role["spec"]["bound_claims"]["workflow_ref"],
            "ai-workspace-lab/distribution/.github/workflows/sync-distribution.yml@*",
        )
        self.assertEqual(dist_role["spec"]["token_policies"], ["github-actions-distribution-prod"])
        self.assertTrue(dist_role["spec"]["token_no_default_policy"])

        xw_pol = yaml.safe_load((ROOT / "security/vault/policies/github-actions-xworkmate-app.yaml").read_text(encoding="utf-8"))
        xw_role = yaml.safe_load((ROOT / "security/vault/roles/github-actions-xworkmate-app.yaml").read_text(encoding="utf-8"))
        xw_paths = {entry["path"]: set(entry["capabilities"]) for entry in xw_pol["spec"]["paths"]}
        self.assertEqual(xw_paths["kv/data/github-actions/xworkmate-app"], {"read"})
        self.assertEqual(xw_paths["kv/data/prod/platform/storage/cloudflare-r2"], {"read"})
        self.assertEqual(xw_paths["kv/data/prod/platform/storage/aliyun-oss"], {"read"})
        self.assertEqual(xw_paths["kv/data/prod/platform/distribution/dispatch-token"], {"read"})
        for caps in xw_paths.values():
            self.assertTrue(caps.issubset({"read", "list"}))
        self.assertEqual(xw_role["spec"]["bound_claims"]["repository"], "ai-workspace-lab/xworkmate-app")
        self.assertEqual(
            xw_role["spec"]["bound_claims"]["workflow_ref"],
            "ai-workspace-lab/xworkmate-app/.github/workflows/build-and-release.yml@*",
        )
        self.assertEqual(
            xw_role["spec"]["bound_claims"]["ref"],
            ["refs/heads/main", "refs/heads/release/*", "refs/tags/v*"],
        )
        self.assertEqual(xw_role["spec"]["token_policies"], ["github-actions-xworkmate-app"])
        self.assertTrue(xw_role["spec"]["token_no_default_policy"])

    def test_download_channels_repos_and_observability_probes(self):
        for rel in (
            "services/prod-k3s-v6/web-saas-prod/download-channels-configmap.yaml",
            "services/sit-k3s-v6/web-saas-sit/download-channels-configmap.yaml",
        ):
            cm = yaml.safe_load((ROOT / rel).read_text(encoding="utf-8"))
            payload = json.loads(cm["data"]["download-channels.json"])
            self.assertEqual(payload["repos"]["cn"]["id"], "cn-repo-oss")
            self.assertEqual(payload["repos"]["cn"]["baseUrl"], "https://cn-repo.svc.plus")
            self.assertTrue(payload["repos"]["cn"]["enabled"])
            self.assertEqual(payload["repos"]["global"]["id"], "global-repo-r2")
            self.assertEqual(payload["repos"]["global"]["baseUrl"], "https://repo.svc.plus")
            self.assertTrue(payload["repos"]["global"]["enabled"])

        docs = list(yaml.safe_load_all((ROOT / "services/prod-k3s-v6/observability-prod/agent-release.yaml").read_text(encoding="utf-8")))
        scrape_configs = docs[1]["spec"]["values"]["vmagent"]["scrapeConfigs"]
        repo_job = next(job for job in scrape_configs if job["job_name"] == "package-repo-mirror-probes")
        targets = [t for group in repo_job["static_configs"] for t in group["targets"]]
        self.assertEqual(
            targets,
            [
                "https://repo.svc.plus/repo/_health/probe.json",
                "https://cn-repo.svc.plus/repo/_health/probe.json",
            ],
        )


if __name__ == "__main__":
    unittest.main()
