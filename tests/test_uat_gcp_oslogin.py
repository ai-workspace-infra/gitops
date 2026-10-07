"""UAT GCP Spot VMs must use OS Login.

The UAT GCP project enforces the requireOsLogin organization policy: GCP
rejects enable-oslogin=FALSE (HTTP 412) and ignores metadata SSH keys. These
are the manifests the Toolkit routes for the UAT Hybrid GCP lanes.
"""

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
UAT_GCP_SPOT_MANIFESTS = (
    "resources/onwalk.net/uat/gcp/web-saas.yaml",
    "resources/svc.plus/uat/gcp/ai-workspace.yaml",
    "resources/svc.plus/uat/gcp/agent-proxy-us.yaml",
)


class UatGcpOsLoginTest(unittest.TestCase):
    def test_us_proxy_is_a_reachable_public_regional_entry(self):
        path = ROOT / "resources/svc.plus/uat/gcp/agent-proxy-us.yaml"
        spec = yaml.safe_load(path.read_text(encoding="utf-8"))["spec"]
        ssh_tags = set(spec.get("spot_network_tags", []))
        self.assertTrue(spec.get("spot_ssh_source_ranges"))
        policy_path = ROOT / "resources/onwalk.net/uat/gcp/open-platform.yaml"
        policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))["global"]
        allowlisted = {(item["name"], item["zone"]) for item in policy["external_ip_allowed_instances"]}
        for vm in spec["resources"]["spot_vms"]:
            self.assertIs(vm.get("public_ip"), True)
            self.assertIs(vm.get("enable_oslogin"), True)
            # Deploy jobs pick the bootstrap playbook from the inventory group
            # and use the first service domain as the node's hostname.
            self.assertIn("agent_proxy", vm.get("inventory_groups", []))
            self.assertTrue(vm["host_vars"]["service_domains"])
            self.assertTrue(ssh_tags & set(vm.get("network_tags", [])))
            self.assertIn(443, vm.get("public_tcp_ports", []))
            self.assertNotIn(22, vm.get("public_tcp_ports", []))
            # The project only admits external IPs for allowlisted instances.
            self.assertIn((vm["name"], vm["zone"]), allowlisted)

    def test_persistent_web_saas_keeps_retained_disks_and_state(self):
        document = yaml.safe_load((ROOT / "resources/onwalk.net/uat/gcp/web-saas.yaml").read_text())
        spec = document["spec"]
        self.assertEqual(spec["resource"]["lifecycle"], "persistent")
        self.assertEqual(spec["state"]["key"], "terraform/uat/open-platform-uat/gcp-cloud/xworktech/web-saas/terraform.tfstate")
        resources = spec["resources"]
        self.assertNotIn("spot_vms", resources)
        vm, = resources["service_vms"]
        self.assertEqual(vm["name"], "web-saas-uat")
        self.assertEqual(vm["provisioning_model"], "STANDARD")
        self.assertIs(vm["deletion_protection"], True)
        self.assertNotIn("data_disk", vm)
        disks = {disk["name"]: disk for disk in resources["persistent_data_disks"]}
        self.assertEqual(set(disks), {"web-saas-uat-upgrade-data", "web-saas-uat-data"})
        self.assertEqual(disks["web-saas-uat-upgrade-data"]["size_gb"], 50)
        self.assertEqual(disks["web-saas-uat-data"]["size_gb"], 100)
        self.assertEqual(disks["web-saas-uat-data"]["device_name"], "web-saas-data")

    def test_every_routed_uat_gcp_spot_vm_enables_os_login(self):
        for relative in UAT_GCP_SPOT_MANIFESTS:
            document = yaml.safe_load((ROOT / relative).read_text(encoding="utf-8"))
            self.assertEqual(document["kind"], "GCPWorkloadNamespace", relative)
            self.assertEqual(document["metadata"]["environment"], "uat", relative)
            resources = document["spec"]["resources"]
            spot_vms = resources.get("spot_vms", []) + resources.get("service_vms", [])
            self.assertTrue(spot_vms, relative)
            for vm in spot_vms:
                with self.subTest(manifest=relative, vm=vm["name"]):
                    self.assertIs(vm.get("enable_oslogin"), True)


if __name__ == "__main__":
    unittest.main()
