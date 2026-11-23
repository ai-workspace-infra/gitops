"""Contract tests for XConnect download channels ConfigMap, Vault OIDC, and mirror probes."""
import json
from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]


class XConnectDownloadChannelsContract(unittest.TestCase):
    def test_prod_and_sit_download_channels_configmaps_and_mounts(self):
        cases = (
            ("prod", "services/prod-k3s-v6/web-saas-prod", "web-saas-prod"),
            ("sit", "services/sit-k3s-v6/web-saas-sit", "web-saas-sit"),
        )
        for _env, rel_dir, namespace in cases:
            base = ROOT / rel_dir
            kustom = yaml.safe_load((base / "kustomization.yaml").read_text())
            self.assertIn("download-channels-configmap.yaml", kustom["resources"])

            cm = yaml.safe_load((base / "download-channels-configmap.yaml").read_text())
            self.assertEqual(cm["kind"], "ConfigMap")
            self.assertEqual(cm["metadata"]["name"], "web-saas-download-channels")
            self.assertEqual(cm["metadata"]["namespace"], namespace)
            payload = json.loads(cm["data"]["download-channels.json"])
            self.assertEqual(payload["schemaVersion"], 1)
            self.assertEqual(payload["mirrors"]["cn"]["baseUrl"], "https://cn-dl.svc.plus")
            self.assertEqual(payload["mirrors"]["cn"]["authMode"], "public-cdn-capped")
            self.assertEqual(payload["mirrors"]["global"]["baseUrl"], "https://dl.svc.plus")
            xconnect = payload["products"]["xconnect"]
            self.assertEqual(xconnect["matrixPath"], "/releases/xconnect/release-matrix.json")
            self.assertEqual(set(xconnect["stores"]), {"ios", "android", "windows", "macos"})
            for stores in xconnect["stores"].values():
                for store in stores:
                    self.assertEqual(store["status"], "coming_soon")
                    self.assertEqual(store["url"], "")

            hr = yaml.safe_load((base / "helmrelease.yaml").read_text())
            console_patch = next(
                p for p in hr["spec"]["postRenderers"][0]["kustomize"]["patches"]
                if p["target"]["name"] == "web-saas-console"
            )
            patch_doc = yaml.safe_load(console_patch["patch"])
            env_map = {
                entry["name"]: entry["value"]
                for entry in patch_doc["spec"]["template"]["spec"]["containers"][0]["env"]
            }
            self.assertEqual(env_map["DOWNLOAD_CHANNELS_CONFIG_PATH"], "/etc/console/download-channels.json")
            self.assertEqual(env_map["ALLOW_REMOTE_DL_FETCH"], "true")

            single = hr["spec"]["values"]["console"]["singleContainer"]
            self.assertTrue(
                any(
                    v["name"] == "download-channels"
                    and v.get("configMap", {}).get("name") == "web-saas-download-channels"
                    for v in single["volumes"]
                )
            )
            self.assertTrue(
                any(
                    m["name"] == "download-channels"
                    and m["mountPath"] == "/etc/console/download-channels.json"
                    and m["subPath"] == "download-channels.json"
                    and m["readOnly"] is True
                    for m in single["volumeMounts"]
                )
            )

    def test_xconnect_app_vault_policy_and_role_are_least_privilege(self):
        policy = yaml.safe_load((ROOT / "security/vault/policies/github-actions-xconnect-app.yaml").read_text())
        role = yaml.safe_load((ROOT / "security/vault/roles/github-actions-xconnect-app.yaml").read_text())

        self.assertEqual(policy["kind"], "VaultACLPolicy")
        self.assertEqual(policy["metadata"]["name"], "github-actions-xconnect-app")
        paths = {entry["path"]: entry["capabilities"] for entry in policy["spec"]["paths"]}
        self.assertEqual(paths["kv/data/prod/platform/storage/aliyun-oss"], ["read"])
        self.assertEqual(paths["kv/data/prod/platform/storage/cloudflare-r2"], ["read"])
        for caps in paths.values():
            self.assertTrue(set(caps).issubset({"read", "list"}))

        self.assertEqual(role["kind"], "VaultJWTAuthRole")
        self.assertEqual(role["metadata"]["name"], "github-actions-xconnect-app")
        self.assertEqual(role["spec"]["bound_claims"]["repository"], "ai-workspace-xstream/xconnect-app")
        self.assertEqual(role["spec"]["token_policies"], ["github-actions-xconnect-app"])
        self.assertNotIn("refs/pull/*/merge", role["spec"]["bound_claims"]["ref"])

    def test_prod_agent_release_adds_xconnect_mirror_probes_without_breaking_progressive_probes(self):
        docs = list(yaml.safe_load_all((ROOT / "services/prod-k3s-v6/observability-prod/agent-release.yaml").read_text()))
        release = docs[1]
        scrape_configs = release["spec"]["values"]["vmagent"]["scrapeConfigs"]
        progressive = next(job for job in scrape_configs if job["job_name"] == "progressive-release-probes")
        self.assertEqual(sum(len(group["targets"]) for group in progressive["static_configs"]), 10)

        mirror_job = next(job for job in scrape_configs if job["job_name"] == "xconnect-download-mirror-probes")
        targets = [t for group in mirror_job["static_configs"] for t in group["targets"]]
        self.assertEqual(
            targets,
            [
                "https://cn-dl.svc.plus/releases/xconnect/release-matrix.json",
                "https://dl.svc.plus/releases/xconnect/release-matrix.json",
                "https://console.svc.plus/download?product=xconnect",
            ],
        )


if __name__ == "__main__":
    unittest.main()
