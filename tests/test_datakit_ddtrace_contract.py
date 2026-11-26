"""Contract tests for DataKit DDTrace, throttled host_processes, Plan A probes, and web-saas DDTrace envs."""
from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]


class TestDataKitDDTraceContract(unittest.TestCase):
    def test_datakit_releases_replicas_and_enable_ddtrace_and_throttled_host_processes(self):
        expected_replicas = [
            ("services/prod-k3s-v6/observability-prod/datakit-helmrelease.yaml", 1),
            ("services/sit-k3s-v6/observability-sit/datakit-helmrelease.yaml", 0),
            ("services/prod-k3s-v6-ulhost/observability-prod/datakit-helmrelease.yaml", 1),
        ]
        for rel, replicas in expected_replicas:
            doc = yaml.safe_load((ROOT / rel).read_text())
            values = doc["spec"]["values"]
            self.assertEqual(values["workload"]["kind"], "Deployment")
            self.assertEqual(values["workload"]["replicas"], replicas, rel)
            inputs = {x.strip() for x in values["datakit"]["default_enabled_inputs"].split(",")}
            self.assertTrue({"dk", "prom", "host_processes", "ddtrace"}.issubset(inputs), rel)
            dkconfig = {item["name"]: item for item in values["dkconfig"]}
            self.assertIn("host-processes.conf", dkconfig)
            self.assertIn('metric_interval = "60s"', dkconfig["host-processes.conf"]["value"])
            self.assertIn('object_interval = "5m"', dkconfig["host-processes.conf"]["value"])
            self.assertIn("ddtrace.conf", dkconfig)

    def test_prod_and_sit_datakit_include_plan_a_progressive_release_probes_and_flagger(self):
        for rel, expected_svc_ns in (
            ("services/prod-k3s-v6/observability-prod/datakit-helmrelease.yaml", "observability-prod"),
            ("services/prod-k3s-v6-ulhost/observability-prod/datakit-helmrelease.yaml", "observability-prod"),
            ("services/sit-k3s-v6/observability-sit/datakit-helmrelease.yaml", "observability-sit"),
        ):
            doc = yaml.safe_load((ROOT / rel).read_text())
            dkconfig = {item["name"]: item for item in doc["spec"]["values"]["dkconfig"]}
            self.assertIn("progressive-release-probes.conf", dkconfig)
            probes_val = dkconfig["progressive-release-probes.conf"]["value"]
            self.assertEqual(probes_val.count("[[inputs.prom]]"), 10)
            self.assertIn(f"observability-agent-blackbox.{expected_svc_ns}.svc:9115/probe", probes_val)
            self.assertIn("flagger-metrics.conf", dkconfig)
            self.assertIn("traefik-canary.conf", dkconfig)

    def test_platform_prod_datakit_values_preserves_zero_replicas_and_ddtrace(self):
        values = yaml.safe_load((ROOT / "services/platform-observability/prod-datakit/values.yaml").read_text())
        self.assertEqual(values["workload"]["replicas"], 0)
        inputs = {x.strip() for x in values["datakit"]["default_enabled_inputs"].split(",")}
        self.assertTrue({"dk", "prom", "host_processes", "ddtrace"}.issubset(inputs))
        dkconfig = {item["name"]: item for item in values["dkconfig"]}
        self.assertIn("host-processes.conf", dkconfig)
        self.assertIn("ddtrace.conf", dkconfig)

    def test_web_saas_deployments_inject_ddtrace_env_with_string_port(self):
        cases = [
            ("services/prod-k3s-v6/web-saas-prod/helmrelease.yaml", "datakit-service.observability-prod.svc", "prod"),
            ("services/sit-k3s-v6/web-saas-sit/helmrelease.yaml", "datakit-service.observability-sit.svc", "sit"),
        ]
        for rel, expected_host, expected_env in cases:
            doc = yaml.safe_load((ROOT / rel).read_text())
            values = doc["spec"]["values"]
            for comp in ("accounts", "billing", "content"):
                env = values[comp]["workload"]["env"]
                self.assertIn(env["DD_TRACE_ENABLED"], ("true", "false"))
                self.assertIsInstance(env["DD_TRACE_ENABLED"], str)
                self.assertEqual(env["DD_AGENT_HOST"], expected_host)
                self.assertEqual(env["DD_TRACE_AGENT_PORT"], "9529")
                self.assertIsInstance(env["DD_TRACE_AGENT_PORT"], str)
                self.assertEqual(env["DD_SERVICE"], f"web-saas-{comp}")
                self.assertEqual(env["DD_ENV"], expected_env)
            console_patch = next(
                p["patch"]
                for p in doc["spec"]["postRenderers"][0]["kustomize"]["patches"]
                if p["target"]["name"] == "web-saas-console"
            )
            patch_doc = yaml.safe_load(console_patch)
            c_env = {e["name"]: e["value"] for e in patch_doc["spec"]["template"]["spec"]["containers"][0]["env"]}
            self.assertIn(c_env["DD_TRACE_ENABLED"], ("true", "false"))
            self.assertIsInstance(c_env["DD_TRACE_ENABLED"], str)
            self.assertEqual(c_env["DD_AGENT_HOST"], expected_host)
            self.assertEqual(c_env["DD_TRACE_AGENT_PORT"], "9529")
            self.assertIsInstance(c_env["DD_TRACE_AGENT_PORT"], str)
            self.assertEqual(c_env["DD_SERVICE"], "web-saas-console")
            self.assertEqual(c_env["DD_ENV"], expected_env)

    def test_prod_datakit_binds_hk_commercial_cn6_vault_record(self):
        policy = yaml.safe_load((ROOT / "security/vault/policies/prod-k3s-v6-datakit-dataway-reader.yaml").read_text())
        self.assertIn("kv/data/observability/datakit/hk-commercial", {p["path"] for p in policy["spec"]["paths"]})
        for rel in (
            "services/prod-k3s-v6/observability-prod/datakit-vault-secret.yaml",
            "services/prod-k3s-v6-ulhost/observability-prod/datakit-vault-secret.yaml",
        ):
            docs = list(yaml.safe_load_all((ROOT / rel).read_text()))
            ext = next(d for d in docs if d["kind"] == "ExternalSecret")
            for item in ext["spec"]["data"]:
                self.assertEqual(item["remoteRef"]["key"], "observability/datakit/hk-commercial", rel)


if __name__ == "__main__":
    unittest.main()
